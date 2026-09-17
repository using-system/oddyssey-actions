#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  COPILOT_VERSION, VERSION, SKILLS, NOTE, MODEL - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
# The note is the resolve step's: empty, or why the version installed is
# not the one requested.
oddyssey="${VERSION} (${SKILLS} skills${NOTE:+; $NOTE})"
echo "Copilot CLI ${COPILOT_VERSION}, oddyssey ${oddyssey}, model ${MODEL}"
{
  echo "### setup-copilot"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| Copilot CLI | ${COPILOT_VERSION} |"
  echo "| oddyssey | ${oddyssey} |"
  echo "| model | ${MODEL} |"
} >> "$GITHUB_STEP_SUMMARY"
