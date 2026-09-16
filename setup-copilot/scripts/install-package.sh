#!/usr/bin/env bash
# Install the oddyssey package for the copilot target, in user scope, and export the CLI and the model.
#
# Reads:  APM_CLI_VERSION, APM_CLI_PINNED_ON - oddyssey's apm-cli pin and its date
#         VERSION - the oddyssey ref resolved
#         MODEL - the model input, exported to the later steps
# Writes: GITHUB_ENV - COPILOT_MODEL, ODDYSSEY_CLI=copilot, ODDYSSEY_MODEL
#         GITHUB_OUTPUT - skills=<count deployed>
set -euo pipefail
# The model goes to $GITHUB_ENV, which every later step of the
# caller's job reads: only a plain model name may pass.
case "$MODEL" in
  ''|*[!A-Za-z0-9._-]*)
    echo "::error::model must be a plain model name ([A-Za-z0-9._-]+), got '${MODEL}'."
    exit 1 ;;
esac
# User scope: the package lands under the runner's home - prompts,
# agents, hooks and the MCP server under ~/.copilot/, the skills
# under ~/.agents/skills/ - and the checkout stays clean. The
# repository is public: apm clones it with no credential.
# apm-cli declares Python >=3.10 but imports a 3.11 name: the
# constraint keeps uvx off an older interpreter a runner may
# carry first on its PATH (macOS ships 3.9 at /usr/bin/python3).
uvx --python '>=3.11' --exclude-newer "$APM_CLI_PINNED_ON" --from "apm-cli==${APM_CLI_VERSION}" \
  apm install --global --target copilot "using-system/oddyssey#${VERSION}"
skills="$( (find "$HOME/.agents/skills" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null || true) | wc -l | tr -d ' ')"
if [ "$skills" -eq 0 ]; then
  echo "::error::apm ${APM_CLI_VERSION} deployed no skill for oddyssey ${VERSION} - the package is not usable without them."
  exit 1
fi
{
  echo "COPILOT_MODEL=${MODEL}"
  echo "ODDYSSEY_CLI=copilot"
  echo "ODDYSSEY_MODEL=${MODEL}"
} >> "$GITHUB_ENV"
echo "skills=${skills}" >> "$GITHUB_OUTPUT"
