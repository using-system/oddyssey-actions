"""The two launch steps: the token reaches Copilot's and nothing else."""

import pytest


@pytest.fixture
def arguments(tmp_path):
    path = tmp_path / "arguments.txt"
    path.write_text(
        "the checkout service\n\nThen end your answer with one json block.\n"
    )
    return {
        "ARGUMENTS_FILE": str(path),
        "EVENTS": str(tmp_path / "events.jsonl"),
        "ODDYSSEY_MODEL": "gpt-5.6-luna",
    }


def test_copilot_launches_scoped_with_the_token_stripped(
    script, fake_cli, arguments, tmp_path
):
    argv = fake_cli(
        "copilot", stdout='{"type":"assistant.message","data":{"content":"ok"}}\n'
    )
    result = script("odd-status", "run-copilot.sh").run(
        {**arguments, "GITHUB_TOKEN": "ghs_x"}
    )
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:2] == [
        "-p",
        "/odd-status the checkout service\n\nThen end your answer with one json block.",
    ]
    assert "--model" in args and args[args.index("--model") + 1] == "gpt-5.6-luna"
    for flag in (
        "--allow-all-tools",
        "--no-ask-user",
        "--no-custom-instructions",
        "--disable-builtin-mcps",
        "--no-auto-update",
    ):
        assert flag in args
    assert args[args.index("--add-dir") + 1].endswith("/.agents/skills")
    assert args[args.index("--secret-env-vars") + 1] == "GITHUB_TOKEN"
    assert "--allow-all-paths" not in args
    assert (
        (tmp_path / "events.jsonl")
        .read_text()
        .startswith('{"type":"assistant.message"')
    )


def test_copilot_fails_on_an_empty_token(script, fake_cli, arguments):
    argv = fake_cli("copilot")
    result = script("odd-status", "run-copilot.sh").run(
        {**arguments, "GITHUB_TOKEN": ""}
    )
    assert result.returncode == 1
    assert "::error::the token input is empty" in result.stdout
    assert not argv.called


@pytest.mark.parametrize("other", ["COPILOT_GITHUB_TOKEN", "GH_TOKEN"])
def test_copilot_fails_when_the_cli_would_prefer_another_token(
    script, fake_cli, arguments, other
):
    argv = fake_cli("copilot")
    result = script("odd-status", "run-copilot.sh").run(
        {**arguments, "GITHUB_TOKEN": "ghs_x", other: "ghp_y"}
    )
    assert result.returncode == 1
    assert f"::error::{other} is set in the step's environment" in result.stdout
    assert "token input" in result.stdout
    assert not argv.called


def test_opencode_launches_the_packaged_command_without_a_token(
    script, fake_cli, arguments, tmp_path
):
    argv = fake_cli("opencode", stdout='{"type":"text"}\n')
    result = script("odd-status", "run-opencode.sh").run(arguments)
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:3] == ["run", "--model", "gpt-5.6-luna"]
    assert "--auto" in args and "--format" in args
    assert args[args.index("--command") + 1] == "odd-status"
    assert (
        args[-1] == "the checkout service\n\nThen end your answer with one json block."
    )
    assert (tmp_path / "events.jsonl").read_text() == '{"type":"text"}\n'
