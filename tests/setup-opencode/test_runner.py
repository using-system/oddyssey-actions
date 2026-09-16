"""On the runner, after `uses: ./setup-opencode`: what it says it
installed is what the runner carries."""

import os
import pathlib
import stat
import subprocess

import pytest
from runner_cases import SKILLS, check_checkout_clean, check_resolved_version

pytestmark = pytest.mark.runner
HOME = pathlib.Path.home()
CONFIG = HOME / ".config/opencode"


def test_opencode_answers_the_version_installed():
    answer = subprocess.run(
        ["opencode", "--version"], text=True, capture_output=True, check=True
    ).stdout
    assert answer.strip() == os.environ["OPENCODE_VERSION"]


def test_the_oddyssey_version_resolved_is_the_one_requested():
    check_resolved_version()


def test_the_later_steps_receive_the_cli_and_the_model():
    assert os.environ["ODDYSSEY_CLI"] == "opencode"
    assert os.environ["ODDYSSEY_MODEL"] == os.environ["MODEL"]


def test_the_skills_and_the_command_are_deployed():
    for skill in SKILLS:
        assert (CONFIG / "skills" / skill / "SKILL.md").is_file(), skill
    assert (CONFIG / "commands/odd-status.md").is_file()


def test_the_config_declares_the_provider_and_the_mcp_server():
    config = (CONFIG / "opencode.json").read_text()
    assert '"openai-compatible"' in config
    assert '"oddyssey"' in config


def test_the_key_file_is_the_users_only():
    key = pathlib.Path(os.environ["RUNNER_TEMP"]) / "opencode/api-key"
    assert stat.S_IMODE(key.stat().st_mode) == 0o600


def test_the_model_is_the_one_declared():
    models = subprocess.run(
        ["opencode", "models", "openai-compatible"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert os.environ["MODEL"] in models.splitlines()


def test_the_checkout_stays_clean():
    check_checkout_clean()
