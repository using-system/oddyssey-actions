"""opencode's global config: the endpoint as a provider, the model, the
package's MCP server from its manifest, the key in a file for the user
only - through the real uv, since the step runs Python through it."""

import json
import stat

import pytest

MANIFEST = """\
name: oddyssey
dependencies:
  mcp:
    - name: oddyssey
      transport: stdio
      command: uvx
      args: ["oddyssey-mcp"]
    - name: remote
      transport: http
      url: https://example.invalid
"""


@pytest.fixture
def env(tmp_path, home):
    manifest = home / ".apm/apm_modules/using-system/oddyssey/apm.yml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(MANIFEST)
    (tmp_path / "opencode").mkdir()
    return {
        "MODEL": "openai/gpt-5.6-luna",
        "BASE_URL": "https://openrouter.ai/api/v1",
        "API_KEY": "sk-or-v1-placeholder",
        "KEY_FILE": str(tmp_path / "opencode" / "api-key"),
        "PYYAML_VERSION": "6.0.3",
    }


def test_writes_the_key_for_the_user_only_and_the_config(script, env, home, tmp_path):
    result = script("setup-opencode", "configure.sh").run(env)
    assert result.returncode == 0, result.log
    key = tmp_path / "opencode" / "api-key"
    assert key.read_text() == "sk-or-v1-placeholder"
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert "sk-or-v1-placeholder" not in result.log
    config = json.loads((home / ".config/opencode/opencode.json").read_text())
    assert config["autoupdate"] is False
    provider = config["provider"]["openai-compatible"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"] == {
        "baseURL": "https://openrouter.ai/api/v1",
        "apiKey": "{file:" + str(key) + "}",
    }
    assert provider["models"] == {
        "openai/gpt-5.6-luna": {"name": "openai/gpt-5.6-luna"}
    }
    # the stdio server from the manifest, the http one left out
    assert config["mcp"] == {
        "oddyssey": {
            "type": "local",
            "command": ["uvx", "oddyssey-mcp"],
            "enabled": True,
        }
    }
    assert result.env == {
        "ODDYSSEY_CLI": "opencode",
        "ODDYSSEY_MODEL": "openai-compatible/openai/gpt-5.6-luna",
    }
    assert "MCP servers ['oddyssey']" in result.stdout


@pytest.mark.parametrize(
    ("key", "error"),
    [("", "openai-api-key is empty"), ("sk or", "openai-api-key carries whitespace")],
)
def test_a_bad_key_fails_before_anything_is_written(
    script, env, home, tmp_path, key, error
):
    result = script("setup-opencode", "configure.sh").run({**env, "API_KEY": key})
    assert result.returncode == 1
    assert f"::error::{error}" in result.stdout
    assert not (tmp_path / "opencode" / "api-key").exists()
    assert not (home / ".config/opencode/opencode.json").exists()
    assert result.env == {}
