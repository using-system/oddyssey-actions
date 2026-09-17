#!/usr/bin/env bash
# State what the runner carries, in the log and the run's summary.
#
# Reads:  OPENCODE_VERSION, VERSION, SKILLS, NOTE, MODEL, BASE_URL - what the earlier steps installed
# Writes: GITHUB_STEP_SUMMARY - one table
set -euo pipefail
# The note is the resolve step's: empty, or why the version installed is
# not the one requested.
oddyssey="${VERSION} (${SKILLS} skills${NOTE:+; $NOTE})"
echo "opencode ${OPENCODE_VERSION}, oddyssey ${oddyssey}, model ${MODEL} at ${BASE_URL}"
{
  echo "### setup-opencode"
  echo ""
  echo "| | |"
  echo "| --- | --- |"
  echo "| opencode | ${OPENCODE_VERSION} |"
  echo "| oddyssey | ${oddyssey} |"
  echo "| model | ${MODEL} |"
  echo "| endpoint | ${BASE_URL} |"
} >> "$GITHUB_STEP_SUMMARY"
