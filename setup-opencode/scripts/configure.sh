#!/usr/bin/env bash
# Configure opencode: the endpoint as a provider, the model, the package's MCP server, the key in a file.
#
# Reads:  MODEL, BASE_URL - the model and openai-base-url inputs
#         API_KEY - the openai-api-key input, a secret: written to KEY_FILE only, never echoed
#         KEY_FILE - the file opencode's provider reads the key from
#         PYYAML_VERSION - the pyyaml pin opencode_config.py runs with
# Writes: KEY_FILE - the key, readable by the runner's user only
#         ~/.config/opencode/opencode.json - replaced (opencode_config.py)
#         GITHUB_ENV - ODDYSSEY_CLI=opencode, ODDYSSEY_MODEL=openai-compatible/<model>
set -euo pipefail
case "$API_KEY" in
  '') echo "::error::openai-api-key is empty."; exit 1 ;;
  *[[:space:]]*) echo "::error::openai-api-key carries whitespace."; exit 1 ;;
esac
# The key lives in a file only opencode's provider reads
# ({file:...}); it is never written to $GITHUB_ENV and never echoed.
(umask 077 && printf '%s' "$API_KEY" > "$KEY_FILE")
# opencode's global config: the endpoint as an OpenAI-compatible
# provider with the model declared, and the package's MCP server
# read from the installed package's own manifest. A global config
# already on the runner is replaced.
uv run --no-project --with "pyyaml==${PYYAML_VERSION}" python "$(dirname "$0")/opencode_config.py" "$MODEL" "$BASE_URL" "$KEY_FILE"
{
  echo "ODDYSSEY_CLI=opencode"
  echo "ODDYSSEY_MODEL=openai-compatible/${MODEL}"
} >> "$GITHUB_ENV"
