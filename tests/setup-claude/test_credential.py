"""The credential: one of the two inputs, in a file for the launch step,
never in GITHUB_ENV, never printed."""

import stat

import pytest


def env(tmp_path, **override):
    return {
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_CODE_OAUTH_TOKEN": "",
        "CREDENTIAL_FILE": str(tmp_path / "claude-code" / "credential"),
        **override,
    }


@pytest.mark.parametrize(
    ("override", "kind"),
    [
        ({"ANTHROPIC_API_KEY": "sk-ant-api03-placeholder"}, "api-key"),
        ({"CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-placeholder"}, "oauth-token"),
    ],
)
def test_keeps_the_one_credential_given_in_a_file_for_the_user_only(
    script, tmp_path, override, kind
):
    result = script("setup-claude", "credential.sh").run(env(tmp_path, **override))
    assert result.returncode == 0, result.log
    file = tmp_path / "claude-code" / "credential"
    assert file.read_text() == next(iter(override.values()))
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    assert result.env == {
        "CLAUDE_CREDENTIAL_FILE": str(file),
        "CLAUDE_CREDENTIAL_KIND": kind,
    }
    assert result.outputs == {"kind": kind}
    assert "placeholder" not in result.log
    assert f"credential: {kind}" in result.stdout


def test_fails_when_neither_is_given(script, tmp_path):
    result = script("setup-claude", "credential.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert (
        "::error::neither anthropic-api-key nor claude-oauth-token is set"
        in result.stdout
    )
    assert not (tmp_path / "claude-code" / "credential").exists()
    assert result.env == {}


def test_fails_when_both_are_given(script, tmp_path):
    result = script("setup-claude", "credential.sh").run(
        env(tmp_path, ANTHROPIC_API_KEY="a", CLAUDE_CODE_OAUTH_TOKEN="b")
    )
    assert result.returncode == 1
    assert (
        "::error::anthropic-api-key and claude-oauth-token are both set"
        in result.stdout
    )
    assert not (tmp_path / "claude-code" / "credential").exists()


def test_fails_on_whitespace(script, tmp_path):
    result = script("setup-claude", "credential.sh").run(
        env(tmp_path, ANTHROPIC_API_KEY="sk ant")
    )
    assert result.returncode == 1
    assert "::error::the credential carries whitespace" in result.stdout
    assert not (tmp_path / "claude-code" / "credential").exists()
