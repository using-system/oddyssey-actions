"""On the runner, after `uses: ./setup-copilot`: what it says it installed
is what the runner carries."""

import os
import pathlib
import subprocess

import pytest
from runner_cases import SKILLS, check_checkout_clean, check_resolved_version

pytestmark = pytest.mark.runner
HOME = pathlib.Path.home()


def test_the_copilot_cli_answers_the_version_installed():
    answer = subprocess.run(
        ["copilot", "--version"], text=True, capture_output=True, check=True
    ).stdout
    assert os.environ["COPILOT_VERSION"] in answer.splitlines()[0]


def test_the_oddyssey_version_resolved_is_the_one_requested():
    check_resolved_version()


def test_the_later_steps_receive_the_cli_and_the_model():
    model = os.environ["MODEL"]
    assert os.environ["COPILOT_MODEL"] == model
    assert os.environ["ODDYSSEY_CLI"] == "copilot"
    assert os.environ["ODDYSSEY_MODEL"] == model


def test_the_skills_are_deployed_and_listed_by_the_cli():
    # read once into memory: the CLI dies of EPIPE when a reader closes early
    listed = subprocess.run(
        ["copilot", "skill", "list"], text=True, capture_output=True, check=True
    ).stdout
    for skill in SKILLS:
        assert (HOME / ".agents/skills" / skill / "SKILL.md").is_file(), skill
        assert any(skill in line.split() for line in listed.splitlines()), skill


def test_the_prompt_and_the_mcp_registration_are_deployed():
    assert (HOME / ".copilot/prompts/odd-status.prompt.md").is_file()
    assert (HOME / ".copilot/mcp-config.json").is_file()


def test_the_checkout_stays_clean():
    check_checkout_clean()
