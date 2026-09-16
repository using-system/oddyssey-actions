#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  CLAUDE_VERSION, VERSION, SKILLS, MODEL, KIND - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
echo "Claude Code ${CLAUDE_VERSION}, oddyssey ${VERSION} (${SKILLS} skills), model ${MODEL}, credential ${KIND}"
{
  echo "### setup-claude"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| Claude Code | ${CLAUDE_VERSION} |"
  echo "| oddyssey | ${VERSION} (${SKILLS} skills) |"
  echo "| model | ${MODEL} |"
  echo "| credential | ${KIND} |"
} >> "$GITHUB_STEP_SUMMARY"
