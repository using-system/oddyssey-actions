#!/usr/bin/env bash
# Run the packaged odd-status through opencode.
#
# Reads:  ARGUMENTS_FILE, EVENTS - the arguments check.sh wrote, where the run's events go
#         ODDYSSEY_MODEL - the model a setup action exported
# Writes: EVENTS - opencode's JSON event stream, for verdict.py
set -euo pipefail
arguments="$(cat "$ARGUMENTS_FILE")"
# opencode expands the packaged command itself; --auto is what
# non-interactive mode requires. No token: the provider's key is
# the setup's, in the file opencode's config points at.
opencode run --model "$ODDYSSEY_MODEL" --format json --auto --title "odd-status" \
  --command odd-status "$arguments" < /dev/null > "$EVENTS"
