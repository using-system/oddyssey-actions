"""The oddyssey release resolution of setup-claude."""

import pytest
from resolve_cases import (
    REJECTS,
    RESOLVES,
    check_minimum_not_released,
    check_no_tags_readable,
    check_rejects,
    check_resolves,
)

ACTION = "setup-claude"


@pytest.mark.parametrize(("requested", "expected", "note"), RESOLVES)
def test_resolves(script, fake_cli, requested, expected, note):
    check_resolves(script, fake_cli, ACTION, requested, expected, note)


@pytest.mark.parametrize(("requested", "error"), REJECTS)
def test_rejects(script, fake_cli, requested, error):
    check_rejects(script, fake_cli, ACTION, requested, error)


def test_fails_when_no_tag_can_be_read(script, fake_cli):
    check_no_tags_readable(script, fake_cli, ACTION)


def test_fails_when_the_minimum_is_not_released(script, fake_cli):
    check_minimum_not_released(script, fake_cli, ACTION)
