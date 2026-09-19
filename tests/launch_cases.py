"""The launch steps, one per CLI (scripts/run-<cli>.sh at the repository
root, behind each prompt-running action's run-<cli>.sh): the packaged
command reaches the CLI scoped, the token reaches Copilot's step and
nothing else, the credential reaches Claude Code's from the setup's file.
An action's test_launch.py replays these with its name and its command."""

ARGUMENTS = "the checkout service\n\nThen end your answer with one json block."
INVALID_COMMANDS = [
    "",
    "Odd-Status",
    "odd status",
    "odd/status",
    "odd_status",
    "1odd-status",
    "-p",
    "odd\nstatus",
]


def arguments(tmp_path, command):
    path = tmp_path / "arguments.txt"
    path.write_text(ARGUMENTS + "\n")
    return {
        "COMMAND": command,
        "ARGUMENTS_FILE": str(path),
        "EVENTS": str(tmp_path / "events.jsonl"),
        "ODDYSSEY_MODEL": "gpt-5.6-luna",
    }


def credential(tmp_path):
    file = tmp_path / "credential"
    file.write_text("sk-ant-oat01-placeholder")
    return {
        "CLAUDE_CREDENTIAL_FILE": str(file),
        "CLAUDE_CREDENTIAL_KIND": "oauth-token",
    }


def check_invalid_command_fails_before_the_cli(
    script, fake_cli, tmp_path, action, cli, command
):
    argv = fake_cli(cli)
    env = arguments(tmp_path, command)
    if cli == "copilot":
        env["GITHUB_TOKEN"] = "ghs_x"
    if cli == "claude":
        env.update(credential(tmp_path))
    result = script(action, f"run-{cli}.sh").run(env)
    assert result.returncode == 1
    assert "::error::COMMAND must be a packaged command's name" in result.stdout
    assert not argv.called


def check_unset_command_fails_before_the_cli(script, fake_cli, tmp_path, action, cli):
    argv = fake_cli(cli)
    env = arguments(tmp_path, "odd-status")
    del env["COMMAND"]
    if cli == "copilot":
        env["GITHUB_TOKEN"] = "ghs_x"
    if cli == "claude":
        env.update(credential(tmp_path))
    result = script(action, f"run-{cli}.sh").run(env)
    assert result.returncode == 1
    assert "::error::COMMAND must be a packaged command's name" in result.stdout
    assert not argv.called


def check_copilot_launches_scoped_with_the_token_stripped(
    script, fake_cli, tmp_path, action, command
):
    argv = fake_cli(
        "copilot", stdout='{"type":"assistant.message","data":{"content":"ok"}}\n'
    )
    result = script(action, "run-copilot.sh").run(
        {**arguments(tmp_path, command), "GITHUB_TOKEN": "ghs_x"}
    )
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:2] == ["-p", f"/{command} {ARGUMENTS}"]
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


def check_copilot_fails_on_an_empty_token(script, fake_cli, tmp_path, action, command):
    argv = fake_cli("copilot")
    result = script(action, "run-copilot.sh").run(
        {**arguments(tmp_path, command), "GITHUB_TOKEN": ""}
    )
    assert result.returncode == 1
    assert "::error::the token input is empty" in result.stdout
    assert not argv.called


def check_copilot_fails_when_the_cli_would_prefer_another_token(
    script, fake_cli, tmp_path, action, command, other
):
    argv = fake_cli("copilot")
    result = script(action, "run-copilot.sh").run(
        {**arguments(tmp_path, command), "GITHUB_TOKEN": "ghs_x", other: "ghp_y"}
    )
    assert result.returncode == 1
    assert f"::error::{other} is set in the step's environment" in result.stdout
    assert "token input" in result.stdout
    assert not argv.called


def check_opencode_launches_the_packaged_command_without_a_token(
    script, fake_cli, tmp_path, action, command
):
    argv = fake_cli("opencode", stdout='{"type":"text"}\n')
    result = script(action, "run-opencode.sh").run(arguments(tmp_path, command))
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:3] == ["run", "--model", "gpt-5.6-luna"]
    assert "--auto" in args and "--format" in args
    assert args[args.index("--title") + 1] == command
    assert args[args.index("--command") + 1] == command
    assert args[-1] == ARGUMENTS
    assert (tmp_path / "events.jsonl").read_text() == '{"type":"text"}\n'


def check_claude_launches_scoped_with_the_credential_from_the_file(
    script, fake_cli, tmp_path, action, command
):
    argv = fake_cli(
        "claude",
        stdout='{"type":"result","subtype":"success","is_error":false,"result":"ok"}\n',
        script='printf \'%s\' "${CLAUDE_CODE_OAUTH_TOKEN:-unset}" > "$0.token"; printf \'%s\' "${ANTHROPIC_API_KEY:-unset}" > "$0.key"; printf \'%s\' "${DISABLE_AUTOUPDATER:-unset}" > "$0.update"',
    )
    result = script(action, "run-claude.sh").run(
        {**arguments(tmp_path, command), **credential(tmp_path)}
    )
    assert result.returncode == 0, result.log
    args = argv.list()
    assert args[:2] == ["-p", f"/{command} {ARGUMENTS}"]
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


def check_claude_reads_an_api_key_into_its_own_variable(
    script, fake_cli, tmp_path, action, command
):
    fake_cli(
        "claude",
        script='printf \'%s\' "${ANTHROPIC_API_KEY:-unset}" > "$0.key"; printf \'%s\' "${CLAUDE_CODE_OAUTH_TOKEN:-unset}" > "$0.token"',
    )
    result = script(action, "run-claude.sh").run(
        {
            **arguments(tmp_path, command),
            **credential(tmp_path),
            "CLAUDE_CREDENTIAL_KIND": "api-key",
        }
    )
    assert result.returncode == 0, result.log
    assert (tmp_path / "bin" / "claude.key").read_text() == "sk-ant-oat01-placeholder"
    assert (tmp_path / "bin" / "claude.token").read_text() == "unset"


def check_claude_fails_without_the_setup_credential(
    script, fake_cli, tmp_path, action, command
):
    argv = fake_cli("claude")
    result = script(action, "run-claude.sh").run(
        {
            **arguments(tmp_path, command),
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


def check_claude_fails_when_the_environment_would_replace_the_credential(
    script, fake_cli, tmp_path, action, command, other
):
    argv = fake_cli("claude")
    result = script(action, "run-claude.sh").run(
        {**arguments(tmp_path, command), **credential(tmp_path), other: "sk-other"}
    )
    assert result.returncode == 1
    assert f"::error::{other} is set in the step's environment" in result.stdout
    assert not argv.called
