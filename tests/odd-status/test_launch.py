"""The launch steps of odd-status: the shared cases, on the command odd-status."""

import pytest
from launch_cases import (
    INVALID_COMMANDS,
    check_claude_fails_when_the_environment_would_replace_the_credential,
    check_claude_fails_without_the_setup_credential,
    check_claude_launches_scoped_with_the_credential_from_the_file,
    check_claude_reads_an_api_key_into_its_own_variable,
    check_copilot_fails_on_an_empty_token,
    check_copilot_fails_when_the_cli_would_prefer_another_token,
    check_copilot_launches_scoped_with_the_token_stripped,
    check_invalid_command_fails_before_the_cli,
    check_opencode_launches_the_packaged_command_without_a_token,
    check_unset_command_fails_before_the_cli,
)

ACTION = "odd-status"
COMMAND = "odd-status"


@pytest.mark.parametrize("cli", ["copilot", "opencode", "claude"])
@pytest.mark.parametrize("command", INVALID_COMMANDS)
def test_invalid_command_fails_before_the_cli(script, fake_cli, tmp_path, cli, command):
    check_invalid_command_fails_before_the_cli(
        script, fake_cli, tmp_path, ACTION, cli, command
    )


@pytest.mark.parametrize("cli", ["copilot", "opencode", "claude"])
def test_unset_command_fails_before_the_cli(script, fake_cli, tmp_path, cli):
    check_unset_command_fails_before_the_cli(script, fake_cli, tmp_path, ACTION, cli)


def test_copilot_launches_scoped_with_the_token_stripped(script, fake_cli, tmp_path):
    check_copilot_launches_scoped_with_the_token_stripped(
        script, fake_cli, tmp_path, ACTION, COMMAND
    )


def test_copilot_fails_on_an_empty_token(script, fake_cli, tmp_path):
    check_copilot_fails_on_an_empty_token(script, fake_cli, tmp_path, ACTION, COMMAND)


@pytest.mark.parametrize("other", ["COPILOT_GITHUB_TOKEN", "GH_TOKEN"])
def test_copilot_fails_when_the_cli_would_prefer_another_token(
    script, fake_cli, tmp_path, other
):
    check_copilot_fails_when_the_cli_would_prefer_another_token(
        script, fake_cli, tmp_path, ACTION, COMMAND, other
    )


def test_opencode_launches_the_packaged_command_without_a_token(
    script, fake_cli, tmp_path
):
    check_opencode_launches_the_packaged_command_without_a_token(
        script, fake_cli, tmp_path, ACTION, COMMAND
    )


def test_claude_launches_scoped_with_the_credential_from_the_file(
    script, fake_cli, tmp_path
):
    check_claude_launches_scoped_with_the_credential_from_the_file(
        script, fake_cli, tmp_path, ACTION, COMMAND
    )


def test_claude_reads_an_api_key_into_its_own_variable(script, fake_cli, tmp_path):
    check_claude_reads_an_api_key_into_its_own_variable(
        script, fake_cli, tmp_path, ACTION, COMMAND
    )


def test_claude_fails_without_the_setup_credential(script, fake_cli, tmp_path):
    check_claude_fails_without_the_setup_credential(
        script, fake_cli, tmp_path, ACTION, COMMAND
    )


@pytest.mark.parametrize("other", ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"])
def test_claude_fails_when_the_environment_would_replace_the_credential(
    script, fake_cli, tmp_path, other
):
    check_claude_fails_when_the_environment_would_replace_the_credential(
        script, fake_cli, tmp_path, ACTION, COMMAND, other
    )
