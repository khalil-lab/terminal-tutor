

import pathlib  # Provides convenient file and directory handling.
import subprocess  # Lets Python execute shell commands and run Ollama.
import sys  # Reads command-line arguments.
import shlex  # Safely formats the command for display.

# Store the latest command output in your home directory.
LOG_FILE = pathlib.Path.home() / ".terminal-tutor-last.log"

# Choose a model already installed in your local Ollama instance.
MODEL = "llama3:latest"


def run_command(command):
    """Run a command and save its output."""

    # Execute the command using Bash, capturing normal output and errors.
    result = subprocess.run(
        ["bash", "-c", command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Save the command and its output so explain can retrieve them later.
    LOG_FILE.write_text(
        f"Command: {command}\n"
        f"Exit code: {result.returncode}\n\n"
        f"Output:\n{result.stdout}",
        encoding="utf-8",
    )

    # Display the original output, just like a normal terminal command.
    print(result.stdout, end="")

    # Return the original command's exit status.
    return result.returncode


def explain_last_output():
    """Ask the local AI to explain the latest command output."""

    # Stop if no command has been recorded yet.
    if not LOG_FILE.exists():
        print("No saved command output. Run tutor COMMAND first.")
        return

    # Read the complete saved log.
    log = LOG_FILE.read_text(encoding="utf-8")

    # Tell the AI exactly how to explain the log.
    prompt = f"""
You are a patient Linux and embedded Linux tutor.

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

    # Ask Ollama to generate the explanation using the local model.
    result = subprocess.run(
        [
            "ollama", "run", MODEL, prompt
        ],
        text=True,
    )

    # Report an error if Ollama itself could not run.
    if result.returncode != 0:
        print("Ollama failed. Check that it is installed and running.")


def main():
    """Choose whether to run a command or explain the last output."""

    # Collect everything typed after the script name.
    arguments = sys.argv[1:]

    # If the user typed explain, explain the saved output.
    if arguments == ["explain"]:
        explain_last_output()

    # Otherwise, treat the arguments as a command to execute.
    elif arguments:
        command = shlex.join(arguments)
        run_command(command)

    # Display usage instructions if nothing was entered.
    else:
        print("Usage: tutor COMMAND")
        print("       tutor explain")


# Start the program when the file is executed directly.
if __name__ == "__main__":
    main()

