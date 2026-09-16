#!/usr/bin/env bash
# Check the inputs before anything is fetched.
#
# Reads:  MODEL, BASE_URL, REQUESTED - the model, openai-base-url and oddyssey-version inputs
# Writes: nothing - exits 1 with ::error:: on the first input that is not a plain value
set -euo pipefail
# Each input reaches a config file, $GITHUB_OUTPUT or $GITHUB_ENV:
# only plain, single-line values may pass (a case pattern sees the
# whole value; a grep sees it line by line). The key is checked in
# the step that writes it, the only one that holds it.
case "$MODEL" in
  ''|*[!A-Za-z0-9._/:-]*)
    echo "::error::model must be a plain model id ([A-Za-z0-9._/:-]+), got '${MODEL}'."
    exit 1 ;;
esac
case "$BASE_URL" in
  ''|*[[:space:]]*)
    echo "::error::openai-base-url must be a single https:// URL, got '${BASE_URL}'."
    exit 1 ;;
esac
# single-line by the case above, so the line-wise grep is exact
if ! printf '%s' "$BASE_URL" | grep -Eq '^https://[A-Za-z0-9._~:/?#@!$&+,;=%-]+$'; then
  echo "::error::openai-base-url must be an https:// URL made of URL characters, got '${BASE_URL}'."
  exit 1
fi
case "$REQUESTED" in
  ''|*[!A-Za-z0-9._-]*)
    echo "::error::oddyssey-version must be a tag, a full commit SHA or latest, got '${REQUESTED}'."
    exit 1 ;;
esac
