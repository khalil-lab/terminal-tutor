from types import SimpleNamespace

import terminal_tutor


def test_format_log_includes_command_status_and_output():
    log = terminal_tutor.format_log("make", 2, "make: *** No targets.\n")

    assert "Command: make" in log
    assert "Exit code: 2" in log
    assert "make: *** No targets." in log


def test_build_prompt_contains_log_and_explanation_rules():
    prompt = terminal_tutor.build_prompt("$ gcc main.c\nerror: stdio.h: not found")

    assert "$ gcc main.c" in prompt
    assert "error: stdio.h: not found" in prompt
    assert "root cause" in prompt
    assert "facts from guesses" in prompt


def test_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINAL_TUTOR_MODEL", "qwen2.5-coder:7b")
    monkeypatch.setenv("TERMINAL_TUTOR_LOG", str(tmp_path / "last.log"))

    assert terminal_tutor.get_model() == "qwen2.5-coder:7b"
    assert terminal_tutor.get_log_path() == tmp_path / "last.log"


def test_run_command_saves_output_and_returns_exit_code(
    tmp_path, monkeypatch, capsys
):
    def fake_run(command, **kwargs):
        assert command == ["bash", "-c", "false"]
        assert kwargs["text"] is True
        return SimpleNamespace(returncode=1, stdout="boom\n")

    monkeypatch.setattr(terminal_tutor.subprocess, "run", fake_run)
    log_path = tmp_path / "last.log"

    assert terminal_tutor.run_command("false", log_path=log_path) == 1
    assert capsys.readouterr().out == "boom\n"

    saved = log_path.read_text(encoding="utf-8")
    assert "Command: false" in saved
    assert "Exit code: 1" in saved
    assert "boom" in saved


def test_run_command_warns_when_log_cannot_be_written(
    tmp_path, monkeypatch, capsys
):
    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="ok\n")

    monkeypatch.setattr(terminal_tutor.subprocess, "run", fake_run)
    missing_parent = tmp_path / "missing" / "last.log"

    assert terminal_tutor.run_command("true", log_path=missing_parent) == 0
    assert "warning: could not save output" in capsys.readouterr().err


def test_explain_without_saved_log_returns_error(tmp_path, capsys):
    result = terminal_tutor.explain_last_output(
        log_path=tmp_path / "none.log"
    )

    assert result == 1
    assert "No saved command output yet" in capsys.readouterr().out


def test_explain_invokes_ollama_with_model_and_prompt(
    tmp_path, monkeypatch
):
    log_path = tmp_path / "last.log"
    log_path.write_text(
        "Command: gcc main.c\nExit code: 1\n\nOutput:\nerror: missing header\n",
        encoding="utf-8",
    )
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(terminal_tutor.subprocess, "run", fake_run)

    result = terminal_tutor.explain_last_output(
        log_path=log_path,
        model="llama3:latest",
    )

    assert result == 0
    assert calls["command"][:3] == ["ollama", "run", "llama3:latest"]
    assert "error: missing header" in calls["command"][3]


def test_explain_reports_missing_ollama(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "last.log"
    log_path.write_text("Command: ls\nExit code: 0\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(terminal_tutor.subprocess, "run", fake_run)

    result = terminal_tutor.explain_last_output(log_path=log_path)

    assert result == 127
    assert "Ollama is not installed" in capsys.readouterr().err


def test_explain_reports_ollama_failure(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "last.log"
    log_path.write_text("Command: ls\nExit code: 0\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=3, stdout="")

    monkeypatch.setattr(terminal_tutor.subprocess, "run", fake_run)

    result = terminal_tutor.explain_last_output(log_path=log_path)

    assert result == 3
    assert "Ollama failed" in capsys.readouterr().err


def test_main_prints_usage_without_arguments(capsys):
    assert terminal_tutor.main([]) == 0
    assert "Usage: tutor <command>" in capsys.readouterr().out


def test_main_prints_usage_for_help(capsys):
    assert terminal_tutor.main(["--help"]) == 0
    assert "tutor explain" in capsys.readouterr().out


def test_main_joins_multiple_arguments(monkeypatch):
    captured = {}

    def fake_run(command):
        captured["command"] = command
        return 0

    monkeypatch.setattr(terminal_tutor, "run_command", fake_run)

    assert terminal_tutor.main(["ls", "-l"]) == 0
    assert captured["command"] == "ls -l"


def test_main_keeps_single_quoted_command(monkeypatch):
    captured = {}

    def fake_run(command):
        captured["command"] = command
        return 0

    monkeypatch.setattr(terminal_tutor, "run_command", fake_run)

    assert terminal_tutor.main(["ls | head -5"]) == 0
    assert captured["command"] == "ls | head -5"


def test_main_dispatches_explain(monkeypatch):
    called = {"explain": False}

    def fake_explain():
        called["explain"] = True
        return 0

    monkeypatch.setattr(terminal_tutor, "explain_last_output", fake_explain)

    assert terminal_tutor.main(["explain"]) == 0
    assert called["explain"] is True
