#!/usr/bin/env bash
# Keep the credential in a file for the launch step, and nowhere else.
#
# Reads:  ANTHROPIC_API_KEY - the anthropic-api-key input (a secret), or empty
#         CLAUDE_CODE_OAUTH_TOKEN - the claude-oauth-token input (a secret), or empty
#         CREDENTIAL_FILE - the file the launch step reads the credential from
# Writes: CREDENTIAL_FILE - the credential, readable by the runner's user only
#         GITHUB_ENV - CLAUDE_CREDENTIAL_FILE and CLAUDE_CREDENTIAL_KIND (api-key or oauth-token), never the value
#         GITHUB_OUTPUT - kind=api-key|oauth-token
set -euo pipefail
# Exactly one of the two: the CLI reads the one variable the launch
# step sets from this file, so two would mean a silent choice.
if [ -n "${ANTHROPIC_API_KEY:-}" ] && [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "::error::anthropic-api-key and claude-oauth-token are both set - pass one of them."
  exit 1
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  kind=api-key; value="$ANTHROPIC_API_KEY"
elif [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  kind=oauth-token; value="$CLAUDE_CODE_OAUTH_TOKEN"
else
  echo "::error::neither anthropic-api-key nor claude-oauth-token is set - the Claude Code run authenticates with one of them."
  exit 1
fi
case "$value" in
  *[[:space:]]*) echo "::error::the credential carries whitespace."; exit 1 ;;
esac
# The file lives under the runner's temporary directory, for the
# runner's user only; it is never written to $GITHUB_ENV and never
# echoed. The launch step of the prompt-running action reads it into
# the CLI's variable, on that step alone.
mkdir -p "$(dirname "$CREDENTIAL_FILE")"
(umask 077 && printf '%s' "$value" > "$CREDENTIAL_FILE")
{
  echo "CLAUDE_CREDENTIAL_FILE=${CREDENTIAL_FILE}"
  echo "CLAUDE_CREDENTIAL_KIND=${kind}"
} >> "$GITHUB_ENV"
echo "kind=${kind}" >> "$GITHUB_OUTPUT"
echo "credential: ${kind}, in a file for the launch step"
