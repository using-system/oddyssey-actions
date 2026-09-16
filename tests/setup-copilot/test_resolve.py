"""The oddyssey release resolution of setup-copilot."""

import pytest
from resolve_cases import (
    REJECTS,
    RESOLVES,
    check_no_tags_readable,
    check_rejects,
    check_resolves,
)

ACTION = "setup-copilot"


@pytest.mark.parametrize(("requested", "expected"), RESOLVES)
def test_resolves(script, fake_cli, requested, expected):
    check_resolves(script, fake_cli, ACTION, requested, expected)


@pytest.mark.parametrize(("requested", "error"), REJECTS)
def test_rejects(script, fake_cli, requested, error):
    check_rejects(script, fake_cli, ACTION, requested, error)


def test_fails_when_no_tag_can_be_read(script, fake_cli):
    check_no_tags_readable(script, fake_cli, ACTION)
