"""On the runner, after `uses: ./setup-claude`: what it says it installed
is what the runner carries."""

import json
import os
import pathlib
import stat
import subprocess

import pytest
from runner_cases import SKILLS, check_checkout_clean, check_resolved_version

pytestmark = pytest.mark.runner
HOME = pathlib.Path.home()


def test_claude_code_answers_the_version_installed():
    answer = subprocess.run(
        ["claude", "--version"],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "DISABLE_AUTOUPDATER": "1"},
    ).stdout
    assert answer.strip() == f"{os.environ['CLAUDE_VERSION']} (Claude Code)"


def test_the_oddyssey_version_resolved_is_the_one_requested():
    check_resolved_version()


def test_the_later_steps_receive_the_cli_and_the_model():
    assert os.environ["ODDYSSEY_CLI"] == "claude"
    assert os.environ["ODDYSSEY_MODEL"] == os.environ["MODEL"]


def test_the_skills_the_command_and_the_mcp_server_are_deployed():
    for skill in SKILLS:
        assert (HOME / ".claude/skills" / skill / "SKILL.md").is_file(), skill
    assert (HOME / ".claude/commands/odd-status.md").is_file()
    assert "oddyssey" in json.loads((HOME / ".claude.json").read_text()).get(
        "mcpServers", {}
    )


def test_the_credential_is_in_a_file_for_the_user_only_and_nowhere_else():
    file = pathlib.Path(os.environ["CLAUDE_CREDENTIAL_FILE"])
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    assert os.environ["CLAUDE_CREDENTIAL_KIND"] in ("api-key", "oauth-token")
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ


def test_the_checkout_stays_clean():
    check_checkout_clean()
