#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  COPILOT_VERSION, VERSION, SKILLS, MODEL - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
echo "Copilot CLI ${COPILOT_VERSION}, oddyssey ${VERSION} (${SKILLS} skills), model ${MODEL}"
{
  echo "### setup-copilot"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| Copilot CLI | ${COPILOT_VERSION} |"
  echo "| oddyssey | ${VERSION} (${SKILLS} skills) |"
  echo "| model | ${MODEL} |"
} >> "$GITHUB_STEP_SUMMARY"
