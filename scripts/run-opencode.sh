#!/usr/bin/env bash
# Run a packaged command through opencode - the one opencode launch line,
# run by every action that runs a prompt, behind its shim.
#
# Reads:  COMMAND - the packaged command to run (odd-status, ...): lowercase, digits, dashes
#         ARGUMENTS_FILE, EVENTS - the arguments the action's check step wrote, where the run's events go
#         ODDYSSEY_MODEL - the model a setup action exported
# Writes: EVENTS - opencode's JSON event stream, for the action's verdict step
set -euo pipefail
# The command is the action's constant, never a caller's input; the
# pattern keeps a slash, a space or a dash-led flag out of the launch line.
# The characters are listed, not ranged: a range in a case pattern
# follows the locale, and a-z admits an uppercase letter in some.
case "${COMMAND:-}" in
  ''|*[!abcdefghijklmnopqrstuvwxyz0123456789-]*|-*)
    echo "::error::COMMAND must be a packaged command's name (lowercase, digits, dashes), got '${COMMAND:-}'."
    exit 1 ;;
esac
arguments="$(cat "$ARGUMENTS_FILE")"
# opencode expands the packaged command itself; --auto is what
# non-interactive mode requires. No token: the provider's key is
# the setup's, in the file opencode's config points at.
opencode run --model "$ODDYSSEY_MODEL" --format json --auto --title "$COMMAND" \
  --command "$COMMAND" "$arguments" < /dev/null > "$EVENTS"
