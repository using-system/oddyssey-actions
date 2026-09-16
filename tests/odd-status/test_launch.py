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


@pytest.fixture
def credential(tmp_path):
    file = tmp_path / "credential"
    file.write_text("sk-ant-oat01-placeholder")
    return {
        "CLAUDE_CREDENTIAL_FILE": str(file),
        "CLAUDE_CREDENTIAL_KIND": "oauth-token",
    }


def test_claude_launches_scoped_with_the_credential_from_the_file(
    script, fake_cli, arguments, credential, tmp_path
):
    argv = fake_cli(
        "claude",
        stdout='{"type":"result","subtype":"success","is_error":false,"result":"ok"}\n',
        script='printf \'%s\' "${CLAUDE_CODE_OAUTH_TOKEN:-unset}" > "$0.token"; printf \'%s\' "${ANTHROPIC_API_KEY:-unset}" > "$0.key"; printf \'%s\' "${DISABLE_AUTOUPDATER:-unset}" > "$0.update"',
    )
    result = script("odd-status", "run-claude.sh").run({**arguments, **credential})
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:2] == [
        "-p",
        "/odd-status the checkout service\n\nThen end your answer with one json block.",
    ]
    assert args[args.index("--model") + 1] == "gpt-5.6-luna"
    assert args[args.index("--permission-mode") + 1] == "bypassPermissions"
    assert args[args.index("--setting-sources") + 1] == "user"
    assert args[args.index("--output-format") + 1] == "json"
    assert "--no-session-persistence" in args
    assert "--dangerously-skip-permissions" not in args
    # the credential reached the CLI's variable, and only the one of its kind
    bin_dir = tmp_path / "bin"
    assert (bin_dir / "claude.token").read_text() == "sk-ant-oat01-placeholder"
    assert (bin_dir / "claude.key").read_text() == "unset"
    assert (bin_dir / "claude.update").read_text() == "1"
    assert "sk-ant-oat01-placeholder" not in result.log
    assert (tmp_path / "events.jsonl").read_text().startswith('{"type":"result"')


def test_claude_reads_an_api_key_into_its_own_variable(
    script, fake_cli, arguments, credential, tmp_path
):
    fake_cli(
        "claude",
        script='printf \'%s\' "${ANTHROPIC_API_KEY:-unset}" > "$0.key"; printf \'%s\' "${CLAUDE_CODE_OAUTH_TOKEN:-unset}" > "$0.token"',
    )
    result = script("odd-status", "run-claude.sh").run(
        {**arguments, **credential, "CLAUDE_CREDENTIAL_KIND": "api-key"}
    )
    assert result.returncode == 0, result.log
    assert (tmp_path / "bin" / "claude.key").read_text() == "sk-ant-oat01-placeholder"
    assert (tmp_path / "bin" / "claude.token").read_text() == "unset"


def test_claude_fails_without_the_setup_credential(
    script, fake_cli, arguments, tmp_path
):
    argv = fake_cli("claude")
    result = script("odd-status", "run-claude.sh").run(
        {
            **arguments,
            "CLAUDE_CREDENTIAL_FILE": str(tmp_path / "missing"),
            "CLAUDE_CREDENTIAL_KIND": "api-key",
        }
    )
    assert result.returncode == 1
    assert (
        "::error::no credential file - run setup-claude earlier in the job"
        in result.stdout
    )
    assert not argv.called


@pytest.mark.parametrize("other", ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"])
def test_claude_fails_when_the_environment_would_replace_the_credential(
    script, fake_cli, arguments, credential, other
):
    argv = fake_cli("claude")
    result = script("odd-status", "run-claude.sh").run(
        {**arguments, **credential, other: "sk-other"}
    )
    assert result.returncode == 1
    assert f"::error::{other} is set in the step's environment" in result.stdout
    assert not argv.called
