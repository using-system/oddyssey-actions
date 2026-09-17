"""The oddyssey package for the copilot target, through apm at
oddyssey's pin, and what the later steps receive."""

import pytest

ENV = {
    "APM_CLI_VERSION": "0.30.0",
    "APM_CLI_PINNED_ON": "2026-09-16",
    "VERSION": "v1.12.2",
    "MODEL": "gpt-5.6-luna",
}
DEPLOY = 'for s in a b c; do mkdir -p "$HOME/.agents/skills/$s" && touch "$HOME/.agents/skills/$s/SKILL.md"; done'


def test_installs_at_the_pin_and_exports_the_cli_and_the_model(script, fake_cli):
    uvx = fake_cli("uvx", script=DEPLOY)
    result = script("setup-copilot", "install-package.sh").run(ENV)
    assert result.returncode == 0, result.log
    args = uvx.list()
    assert args[:3] == ["--python", ">=3.11", "--exclude-newer"]
    assert args[3] == "2026-09-16"
    assert args[args.index("--from") + 1] == "apm-cli==0.30.0"
    assert args[-6:] == [
        "apm",
        "install",
        "--global",
        "--target",
        "copilot",
        "using-system/oddyssey#v1.12.2",
    ]
    assert result.outputs == {"skills": "3"}
    assert result.env == {
        "COPILOT_MODEL": "gpt-5.6-luna",
        "ODDYSSEY_CLI": "copilot",
        "ODDYSSEY_MODEL": "gpt-5.6-luna",
    }


@pytest.mark.parametrize("model", ["", "gpt 5", "gpt\n5", "a;b"])
def test_a_bad_model_fails_before_anything_installs(script, fake_cli, model):
    uvx = fake_cli("uvx", script=DEPLOY)
    result = script("setup-copilot", "install-package.sh").run({**ENV, "MODEL": model})
    assert result.returncode == 1
    assert "::error::model must be a plain model name" in result.stdout
    assert not uvx.called
    assert result.env == {}


def test_fails_when_apm_deployed_no_skill(script, fake_cli):
    fake_cli("uvx")
    result = script("setup-copilot", "install-package.sh").run(ENV)
    assert result.returncode == 1
    assert "::error::apm 0.30.0 deployed no skill for oddyssey v1.12.2" in result.stdout
    assert result.env == {}
    assert result.outputs == {}
