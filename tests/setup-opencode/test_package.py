"""The oddyssey package for the opencode target, through apm at
oddyssey's pin, the MCP server left to the configure step."""

ENV = {
    "APM_CLI_VERSION": "0.30.0",
    "APM_CLI_PINNED_ON": "2026-09-16",
    "VERSION": "v1.12.0",
}
DEPLOY = 'for s in a b; do mkdir -p "$HOME/.config/opencode/skills/$s" && touch "$HOME/.config/opencode/skills/$s/SKILL.md"; done'


def test_installs_at_the_pin_apm_only(script, fake_cli):
    uvx = fake_cli("uvx", script=DEPLOY)
    result = script("setup-opencode", "install-package.sh").run(ENV)
    assert result.returncode == 0, result.log
    args = uvx.list()
    assert args[:4] == ["--python", ">=3.11", "--exclude-newer", "2026-09-16"]
    assert args[args.index("--from") + 1] == "apm-cli==0.30.0"
    assert args[-8:] == [
        "apm",
        "install",
        "--global",
        "--target",
        "opencode",
        "--only",
        "apm",
        "using-system/oddyssey#v1.12.0",
    ]
    assert result.outputs == {"skills": "2"}
    assert result.env == {}


def test_fails_when_apm_deployed_no_skill(script, fake_cli):
    fake_cli("uvx")
    result = script("setup-opencode", "install-package.sh").run(ENV)
    assert result.returncode == 1
    assert "::error::apm 0.30.0 deployed no skill for oddyssey v1.12.0" in result.stdout
    assert result.outputs == {}
