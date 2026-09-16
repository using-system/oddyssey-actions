#!/usr/bin/env bash
# Check the setup and the inputs before any CLI runs, and write the command's arguments.
#
# Reads:  PROMPT, FAIL_ON - the prompt and fail-on inputs
#         ODDYSSEY_CLI, ODDYSSEY_MODEL - what a setup action exported
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
case "$ODDYSSEY_CLI" in copilot|opencode) ;; *)
  echo "::error::ODDYSSEY_CLI is '${ODDYSSEY_CLI}' - this action runs copilot or opencode."; exit 1 ;;
esac
# The verdict the run must end with - the contract verdict.py parses.
# The judgement is the model's; the shape is not.
INSTRUCTION='Then end your answer with exactly one fenced json code block and nothing after it, of the form {"status": "ok" | "warning" | "error", "summary": "<one sentence>", "todo": [{"action": "<what to do next>", "why": "<the evidence>"}]}. Judge the status yourself from the loop'"'"'s state: error when something demands a fix before the next step (a verification that failed, a regression, a finding past its due date, a report that could not be read), warning when something is due or degraded but not blocking (a report older than its cadence, an open telemetry gap, a loop not started), ok when nothing is due. The todo lists the next actions, most urgent first, and is empty when nothing is due.'
# The command's arguments, handed to the launch step through a file: the
# prompt is the caller's text and never goes through GITHUB_OUTPUT or
# GITHUB_ENV.
printf '%s\n\n%s\n' "$PROMPT" "$INSTRUCTION" > "$ARGUMENTS_FILE"
echo "cli=${ODDYSSEY_CLI}" >> "$GITHUB_OUTPUT"
echo "odd-status through ${ODDYSSEY_CLI} on ${ODDYSSEY_MODEL}${PROMPT:+ - $(printf '%s' "$PROMPT" | tr '\n\r' '  ')}"
