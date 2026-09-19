"""Write opencode's global config for setup-opencode.

    opencode_config.py <model> <base-url> <key-file>

The endpoint as an `@ai-sdk/openai-compatible` provider named
`openai-compatible` with the one model declared, the key read from
<key-file> through opencode's `{file:...}`, auto-update off so the version
installed is the version that runs, and the package's stdio MCP servers as
the installed package's own manifest (~/.apm/apm_modules/using-system/
oddyssey/apm.yml) declares them. Replaces ~/.config/opencode/opencode.json.
"""

import json
import pathlib
import sys

import yaml

model, base_url, key_file = sys.argv[1:4]
home = pathlib.Path.home()
manifest = yaml.safe_load(
    (home / ".apm/apm_modules/using-system/oddyssey/apm.yml").read_text()
)
mcp = {}
for server in (manifest.get("dependencies") or {}).get("mcp") or []:
    if server.get("transport") == "stdio" and server.get("command"):
        mcp[server["name"]] = {
            "type": "local",
            "command": [server["command"], *server.get("args", [])],
            "enabled": True,
        }
config = {
    "$schema": "https://opencode.ai/config.json",
    # the version installed is the version that runs
    "autoupdate": False,
    "provider": {
        "openai-compatible": {
            # a provider opencode bundles into its binary (its
            # BUNDLED_PROVIDERS table): loaded from the verified build,
            # never fetched from a registry at launch - keep it one of those
            "npm": "@ai-sdk/openai-compatible",
            "name": "OpenAI-compatible endpoint (setup-opencode)",
            "options": {"baseURL": base_url, "apiKey": "{file:" + key_file + "}"},
            "models": {model: {"name": model}},
        }
    },
    "mcp": mcp,
}
target = home / ".config/opencode/opencode.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(config, indent=2) + "\n")
print(
    f"opencode.json: provider openai-compatible at {base_url}, model {model}, MCP servers {sorted(mcp) or 'none'}"
)
