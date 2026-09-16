#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  OPENCODE_VERSION, VERSION, SKILLS, MODEL, BASE_URL - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
echo "opencode ${OPENCODE_VERSION}, oddyssey ${VERSION} (${SKILLS} skills), model ${MODEL} at ${BASE_URL}"
{
  echo "### setup-opencode"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| opencode | ${OPENCODE_VERSION} |"
  echo "| oddyssey | ${VERSION} (${SKILLS} skills) |"
  echo "| model | ${MODEL} |"
  echo "| endpoint | ${BASE_URL} |"
} >> "$GITHUB_STEP_SUMMARY"
