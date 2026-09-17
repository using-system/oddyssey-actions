#!/usr/bin/env bash
# Check the setup and the inputs before any CLI runs, and write the command's arguments.
#
# Reads:  PROMPT, FAIL_ON - the prompt and fail-on inputs
#         ODDYSSEY_CLI, ODDYSSEY_MODEL - what a setup action exported (copilot, opencode or claude)
#         ARGUMENTS_FILE - where the command's arguments go for the launch step
# Writes: ARGUMENTS_FILE - the prompt, then the verdict instruction
#         GITHUB_OUTPUT - cli=copilot|opencode
set -euo pipefail
case "$FAIL_ON" in none|warning|error) ;; *)
  echo "::error::fail-on must be none, warning or error, got '${FAIL_ON}'."; exit 1 ;;
esac
# The prompt is the command's positional argument: one starting
# with a dash would be read as a flag of the CLI.
case "$PROMPT" in -*)
  echo "::error::prompt must not start with a dash."; exit 1 ;;
esac
if [ -z "${ODDYSSEY_CLI:-}" ] || [ -z "${ODDYSSEY_MODEL:-}" ]; then
  echo "::error::ODDYSSEY_CLI and ODDYSSEY_MODEL are not set - run a setup action (setup-copilot, setup-opencode) earlier in the job."
  exit 1
fi
case "$ODDYSSEY_CLI" in copilot|opencode|claude) ;; *)
  echo "::error::ODDYSSEY_CLI is '${ODDYSSEY_CLI}' - this action runs copilot, opencode or claude."; exit 1 ;;
esac
# The contract verdict.py parses. The status and the todo are the
# package's own: get-status opens its rendering with a verdict line and
# a todo line, computed by its rules from every report, ruling and ledger
# row, and the run prints them unchanged. The model's part is the
# one-sentence summary.
INSTRUCTION='Print the rendering unchanged, its verdict and todo lines included, then end your answer with exactly one fenced json code block and nothing after it: {"summary": "<one sentence on the verdict>"}.'
# The command's arguments, handed to the launch step through a file: the
# prompt is the caller's text and never goes through GITHUB_OUTPUT or
# GITHUB_ENV.
printf '%s\n\n%s\n' "$PROMPT" "$INSTRUCTION" > "$ARGUMENTS_FILE"
echo "cli=${ODDYSSEY_CLI}" >> "$GITHUB_OUTPUT"
echo "odd-status through ${ODDYSSEY_CLI} on ${ODDYSSEY_MODEL}${PROMPT:+ - $(printf '%s' "$PROMPT" | tr '\n\r' '  ')}"
