# Terminal Tutor

[![tests](https://github.com/khalil-lab/terminal-tutor/actions/workflows/tests.yml/badge.svg)](https://github.com/khalil-lab/terminal-tutor/actions/workflows/tests.yml)

Explain Linux terminal output, compiler errors, and build logs in plain language,
line by line, using a local LLM.

No API keys, no cloud service, and no data leaving your machine.

## Why

Long build logs and cryptic compiler errors slow down debugging, especially when
you are new to a toolchain or working in an unfamiliar codebase. Terminal Tutor
wraps your command, keeps the exact output, and asks a local Ollama model to
explain what happened and why.

Typical uses:

- Understanding `gcc`, `cmake`, `make`, or linker errors
- Reading kernel, Yocto, or embedded toolchain failures
- Learning what a long `dmesg`, `journalctl`, or test log is telling you

## Demo

```console
$ tutor gcc hello.c
hello.c:1:10: fatal error: stdio.h: No such file or directory
    1 | #include <stdio.h>
      |          ^~~~~~~~~
compilation terminated.

$ tutor explain
The command tried to compile hello.c with GCC, but the compiler could not find
the standard header stdio.h. This usually means the C development headers are
not installed, or the compiler is looking in the wrong sysroot.

Next step: install the libc development package (for example
`sudo apt install libc6-dev`) and run the command again.
```

## How it works

```text
tutor <command>  ->  bash -c <command>  ->  print output
                                      \->  ~/.terminal-tutor-last.log
                                                    |
tutor explain    ->  read log  ->  Ollama (local model)  ->  explanation
```

1. `tutor <command>` runs the command through Bash, streams its combined stdout
   and stderr, and stores the command, exit code, and output in a local log.
2. `tutor explain` sends that log to a local model with a strict prompt: explain
   each meaningful line, define technical terms, distinguish facts from guesses,
   and never claim a failed command succeeded.

## Requirements

- Linux or macOS (the runner uses `bash`)
- Python 3.9+
- [Ollama](https://ollama.com/download) running locally
- A model pulled in Ollama, for example `ollama pull llama3`

## Installation

```bash
git clone https://github.com/khalil-lab/terminal-tutor.git
cd terminal-tutor
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs two equivalent commands: `tutor` and `terminal-tutor`.

Using [pipx](https://pipx.pypa.io/) keeps it isolated:

```bash
pipx install .
```

Without installing, the script also runs directly:

```bash
python3 terminal_tutor.py --help
```

## Usage

Run a command and capture its output:

```bash
tutor make
tutor pytest -q
tutor cmake --build build
```

Ask for an explanation of the most recent captured output:

```bash
tutor explain
```

Pass a full shell expression as one quoted argument when you need pipes,
redirections, or `&&`:

```bash
tutor "make 2>&1 | tail -20"
tutor "dmesg | grep -i error"
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TERMINAL_TUTOR_MODEL` | `llama3:latest` | Ollama model used for explanations |
| `TERMINAL_TUTOR_LOG` | `~/.terminal-tutor-last.log` | Location of the saved command output |

Example:

```bash
export TERMINAL_TUTOR_MODEL="qwen2.5-coder:7b"
tutor explain
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

The test suite mocks Ollama, so it runs without a model or a running server.

## Safety notes

- Commands are executed with your user privileges. Review what you ask it to run,
  exactly as you would with a normal shell.
- The last command output is written to `~/.terminal-tutor-last.log`. Do not run
  commands that print secrets if you do not want them stored locally.
- Explanations come from a local model and can be wrong. The prompt asks the
  model to separate facts from guesses, but always verify critical diagnoses.

## License

MIT. See [LICENSE](LICENSE).
