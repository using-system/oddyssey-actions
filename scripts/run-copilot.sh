#!/usr/bin/env bash
# Run a packaged command through the Copilot CLI, scoped - the one Copilot
# launch line, run by every action that runs a prompt, behind its shim.
#
# Reads:  COMMAND - the packaged command to run (odd-status, ...): lowercase, digits, dashes
#         ARGUMENTS_FILE, EVENTS - the arguments the action's check step wrote, where the run's events go
#         ODDYSSEY_MODEL - the model a setup action exported
#         GITHUB_TOKEN - the token input, this step's alone
# Writes: EVENTS - the CLI's JSON event stream, for the action's verdict step
set -euo pipefail
# The command is the action's constant, never a caller's input; the
# pattern keeps a slash, a space or a dash-led flag out of the prompt.
# The characters are listed, not ranged: a range in a case pattern
# follows the locale, and a-z admits an uppercase letter in some.
case "${COMMAND:-}" in
  ''|*[!abcdefghijklmnopqrstuvwxyz0123456789-]*|-*)
    echo "::error::COMMAND must be a packaged command's name (lowercase, digits, dashes), got '${COMMAND:-}'."
    exit 1 ;;
esac
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "::error::the token input is empty - the Copilot run authenticates with it (the workflow's token by default, under copilot-requests: write)."
  exit 1
fi
# The CLI reads COPILOT_GITHUB_TOKEN, then GH_TOKEN, then
# GITHUB_TOKEN (its `help environment`): either of the first two
# in this step's environment would silently replace the token
# input. The token input is the one path.
for other in COPILOT_GITHUB_TOKEN GH_TOKEN; do
  if [ -n "${!other:-}" ]; then
    echo "::error::${other} is set in the step's environment and the Copilot CLI would prefer it over the token input - pass that token as the action's token input instead, and unset ${other}."
    exit 1
  fi
done
arguments="$(cat "$ARGUMENTS_FILE")"
# The Copilot CLI does not expand a slash command: the text reaches
# the model as written and the model routes it to the packaged
# skill. Scoped: tools auto-approved (non-interactive mode requires
# it), file access to the skills only, no instructions from the
# checkout, the built-in GitHub MCP server off, the token stripped
# from the shells the run opens, the installed version and nothing
# newer.
copilot -p "/${COMMAND} ${arguments}" --model "$ODDYSSEY_MODEL" \
  --allow-all-tools --add-dir "$HOME/.agents/skills" \
  --no-ask-user --no-custom-instructions --disable-builtin-mcps \
  --secret-env-vars GITHUB_TOKEN --no-auto-update \
  --output-format json < /dev/null > "$EVENTS"
