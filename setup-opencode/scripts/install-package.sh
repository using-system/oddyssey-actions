#!/usr/bin/env bash
# Install the oddyssey package for the opencode target, in user scope, apm only.
#
# Reads:  APM_CLI_VERSION, APM_CLI_PINNED_ON - oddyssey's apm-cli pin and its date
#         VERSION - the oddyssey ref resolved
# Writes: GITHUB_OUTPUT - skills=<count deployed>
set -euo pipefail
# User scope: agents, commands and skills land under
# ~/.config/opencode/ and the checkout stays clean. --only apm: apm
# cannot register an MCP server at user scope for opencode - the
# next step writes it into opencode's global config itself.
# apm-cli declares Python >=3.10 but imports a 3.11 name: the
# constraint keeps uvx off an older interpreter a runner may carry
# first on its PATH (macOS ships 3.9 at /usr/bin/python3).
uvx --python '>=3.11' --exclude-newer "$APM_CLI_PINNED_ON" --from "apm-cli==${APM_CLI_VERSION}" \
  apm install --global --target opencode --only apm "using-system/oddyssey#${VERSION}"
skills="$( (find "$HOME/.config/opencode/skills" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null || true) | wc -l | tr -d ' ')"
if [ "$skills" -eq 0 ]; then
  echo "::error::apm ${APM_CLI_VERSION} deployed no skill for oddyssey ${VERSION} - the package is not usable without them."
  exit 1
fi
echo "skills=${skills}" >> "$GITHUB_OUTPUT"
