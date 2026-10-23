"""Explain Linux terminal output and errors with a local Ollama model."""

from __future__ import annotations

import os
import pathlib
import shlex
import subprocess
import sys

DEFAULT_MODEL = "llama3:latest"
DEFAULT_LOG_FILE = pathlib.Path.home() / ".terminal-tutor-last.log"

PROMPT_TEMPLATE = """You are a patient Linux and embedded Linux tutor.

Explain the following terminal log in simple English.

Requirements:
1. Explain what the command was intended to do.
2. Explain the output in its original order.
3. Comment on every meaningful output line or group of lines.
4. Explain technical terms and error messages.
5. Identify the root cause when the evidence supports it.
6. Give practical next steps only when appropriate.
7. Clearly distinguish facts from guesses.
8. Do not claim the command succeeded if it failed.

Terminal log:
{log}
"""


def get_log_path() -> pathlib.Path:
    """Return the log path, honouring TERMINAL_TUTOR_LOG."""
    return pathlib.Path(os.environ.get("TERMINAL_TUTOR_LOG", DEFAULT_LOG_FILE))


def get_model() -> str:
    """Return the Ollama model, honouring TERMINAL_TUTOR_MODEL."""
    return os.environ.get("TERMINAL_TUTOR_MODEL", DEFAULT_MODEL)


def format_log(command: str, returncode: int, output: str) -> str:
    """Format a command result for storage and later explanation."""
    return (
        f"Command: {command}\n"
        f"Exit code: {returncode}\n\n"
        f"Output:\n{output}"
    )


def run_command(command: str, log_path: pathlib.Path | None = None) -> int:
    """Run a command in Bash, echo its output, and save it for later."""
    result = subprocess.run(
        ["bash", "-c", command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout, end="")

    path = log_path or get_log_path()
    try:
        path.write_text(
            format_log(command, result.returncode, result.stdout),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"warning: could not save output to {path}: {exc}", file=sys.stderr)

    return result.returncode


def build_prompt(log: str) -> str:
    """Build the instruction sent to the local model."""
    return PROMPT_TEMPLATE.format(log=log)


def explain_last_output(
    log_path: pathlib.Path | None = None,
    model: str | None = None,
) -> int:
    """Explain the most recent saved command output with Ollama."""
    path = log_path or get_log_path()
    if not path.exists():
        print("No saved command output yet. Run: tutor <command>")
        return 1

    prompt = build_prompt(path.read_text(encoding="utf-8"))

    try:
        result = subprocess.run(
            ["ollama", "run", model or get_model(), prompt],
            text=True,
        )
    except FileNotFoundError:
        print(
            "Ollama is not installed. See https://ollama.com/download",
            file=sys.stderr,
        )
        return 127

    if result.returncode != 0:
        print(
            "Ollama failed. Check that it is installed and running.",
            file=sys.stderr,
        )

    return result.returncode


def print_usage() -> None:
    """Print command-line usage."""
    print("Usage: tutor <command>")
    print("       tutor explain")
    print("       tutor --help")


def main(argv: list[str] | None = None) -> int:
    """Dispatch between running a command and explaining the last output."""
    arguments = sys.argv[1:] if argv is None else argv

    if arguments in (["-h"], ["--help"], ["help"]):
        print_usage()
        return 0

    if arguments == ["explain"]:
        return explain_last_output()

    if arguments:
        # A single argument is treated as a full shell command, so quoted
        # pipelines such as `tutor "ls | head"` keep working.
        command = arguments[0] if len(arguments) == 1 else shlex.join(arguments)
        return run_command(command)

    print_usage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
