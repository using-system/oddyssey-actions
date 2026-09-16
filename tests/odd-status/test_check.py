"""The step that checks the setup and the inputs before any CLI runs."""

import pytest

ENV = {
    "PROMPT": "the checkout service",
    "FAIL_ON": "error",
    "ODDYSSEY_CLI": "copilot",
    "ODDYSSEY_MODEL": "gpt-5.6-luna",
}


def env(tmp_path, **override):
    return {**ENV, "ARGUMENTS_FILE": str(tmp_path / "arguments.txt"), **override}


def test_valid_inputs_name_the_cli_and_write_the_arguments(script, tmp_path):
    result = script("odd-status", "check.sh").run(env(tmp_path))
    assert result.returncode == 0, result.log
    assert result.outputs == {"cli": "copilot"}
    arguments = (tmp_path / "arguments.txt").read_text()
    # the prompt, a blank line, then the verdict contract verdict.py parses
    assert arguments.startswith(
        "the checkout service\n\nThen end your answer with exactly one fenced json code block"
    )
    assert '{"status": "ok" | "warning" | "error"' in arguments
    assert arguments.endswith("is empty when nothing is due.\n")
    assert (
        "odd-status through copilot on gpt-5.6-luna - the checkout service"
        in result.stdout
    )


def test_an_empty_prompt_is_the_whole_loop(script, tmp_path):
    result = script("odd-status", "check.sh").run(env(tmp_path, PROMPT=""))
    assert result.returncode == 0, result.log
    assert (
        (tmp_path / "arguments.txt").read_text().startswith("\n\nThen end your answer")
    )


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"PROMPT": "-x"}, "prompt must not start with a dash"),
        ({"FAIL_ON": "always"}, "fail-on must be none, warning or error"),
        ({"ODDYSSEY_CLI": ""}, "ODDYSSEY_CLI and ODDYSSEY_MODEL are not set"),
        ({"ODDYSSEY_MODEL": ""}, "ODDYSSEY_CLI and ODDYSSEY_MODEL are not set"),
        ({"ODDYSSEY_CLI": "gemini"}, "ODDYSSEY_CLI is 'gemini'"),
    ],
)
def test_a_bad_input_or_setup_fails_and_says_which(script, tmp_path, override, error):
    result = script("odd-status", "check.sh").run(env(tmp_path, **override))
    assert result.returncode == 1
    assert f"::error::{error}" in result.stdout
    assert result.outputs == {}


@pytest.mark.parametrize("cli", ["copilot", "opencode", "claude"])
def test_each_cli_a_setup_exports_is_named(script, tmp_path, cli):
    result = script("odd-status", "check.sh").run(env(tmp_path, ODDYSSEY_CLI=cli))
    assert result.returncode == 0, result.log
    assert result.outputs == {"cli": cli}
