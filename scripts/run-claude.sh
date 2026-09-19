#!/usr/bin/env bash
# Run a packaged command through Claude Code, scoped - the one Claude Code
# launch line, run by every action that runs a prompt, behind its shim.
#
# Reads:  COMMAND - the packaged command to run (odd-status, ...): a lowercase letter, then lowercase, digits, dashes
#         ARGUMENTS_FILE, EVENTS - the arguments the action's check step wrote, where the run's result goes
#         ODDYSSEY_MODEL - the model a setup action exported
#         CLAUDE_CREDENTIAL_FILE, CLAUDE_CREDENTIAL_KIND - what setup-claude left: the file, and api-key or oauth-token
# Writes: EVENTS - the CLI's JSON result, for the action's verdict step
set -euo pipefail
# The command is the action's constant, never a caller's input; the
# pattern keeps a slash, a space or a dash-led flag out of the prompt.
# The characters are listed, not ranged: a range in a case pattern
# follows the locale, and a-z admits an uppercase letter in some.
case "${COMMAND:-}" in
  ''|[!abcdefghijklmnopqrstuvwxyz]*|*[!abcdefghijklmnopqrstuvwxyz0123456789-]*)
    echo "::error::COMMAND must be a packaged command's name (a lowercase letter first, then lowercase, digits, dashes), got '${COMMAND:-}'."
    exit 1 ;;
esac
if [ -z "${CLAUDE_CREDENTIAL_FILE:-}" ] || [ ! -f "$CLAUDE_CREDENTIAL_FILE" ]; then
  echo "::error::no credential file - run setup-claude earlier in the job, with anthropic-api-key or claude-oauth-token."
  exit 1
fi
# The CLI reads ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN; either
# one already in this step's environment would replace the setup's
# credential: the setup's input is the one path.
for other in ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN; do
  if [ -n "${!other:-}" ]; then
    echo "::error::${other} is set in the step's environment and would replace the credential setup-claude was given - pass it to setup-claude instead, and unset ${other}."
    exit 1
  fi
done
case "$CLAUDE_CREDENTIAL_KIND" in
  api-key) variable=ANTHROPIC_API_KEY ;;
  oauth-token) variable=CLAUDE_CODE_OAUTH_TOKEN ;;
  *) echo "::error::CLAUDE_CREDENTIAL_KIND is '${CLAUDE_CREDENTIAL_KIND}' - api-key or oauth-token."; exit 1 ;;
esac
arguments="$(cat "$ARGUMENTS_FILE")"
# Claude Code expands the packaged command itself, from the user scope
# the setup deployed. Scoped: permissions bypassed (non-interactive mode
# requires it), the user-scope settings only - nothing from the
# checkout's .claude/ - no session written to disk, the updater off so
# the version installed is the version that runs, and the credential in
# the CLI's variable for this process alone, read from the setup's file.
env "${variable}=$(cat "$CLAUDE_CREDENTIAL_FILE")" DISABLE_AUTOUPDATER=1 \
  claude -p "/${COMMAND} ${arguments}" --model "$ODDYSSEY_MODEL" \
  --permission-mode bypassPermissions --setting-sources user \
  --no-session-persistence --output-format json < /dev/null > "$EVENTS"
