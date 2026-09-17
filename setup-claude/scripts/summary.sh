#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  CLAUDE_VERSION, VERSION, SKILLS, NOTE, MODEL, KIND - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
# The note is the resolve step's: empty, or why the version installed is
# not the one requested.
oddyssey="${VERSION} (${SKILLS} skills${NOTE:+; $NOTE})"
echo "Claude Code ${CLAUDE_VERSION}, oddyssey ${oddyssey}, model ${MODEL}, credential ${KIND}"
{
  echo "### setup-claude"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| Claude Code | ${CLAUDE_VERSION} |"
  echo "| oddyssey | ${oddyssey} |"
  echo "| model | ${MODEL} |"
  echo "| credential | ${KIND} |"
} >> "$GITHUB_STEP_SUMMARY"
