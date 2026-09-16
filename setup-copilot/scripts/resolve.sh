#!/usr/bin/env bash
# Resolve the oddyssey release to install, against the repository's release tags.
#
# Reads:  REQUESTED - the oddyssey-version input: a tag, a full commit SHA, or latest
# Writes: GITHUB_OUTPUT - version=<vX.Y.Z or the SHA>
set -euo pipefail
# Resolved first: a wrong input costs nothing else. The value
# reaches $GITHUB_OUTPUT: a case pattern sees it whole, so a second
# line cannot pass. A full commit SHA is taken as is - the one
# immutable form; a tag is checked against the remote's release
# tags (plain vX.Y.Z), read with no API call and no token.
case "$REQUESTED" in
  ''|*[!A-Za-z0-9._-]*)
    echo "::error::oddyssey-version must be a tag, a full commit SHA or latest, got '${REQUESTED}'."
    exit 1 ;;
esac
if printf '%s' "$REQUESTED" | grep -Eq '^[0-9a-f]{40}$'; then
  version="$REQUESTED"
else
  tags="$( (git ls-remote --tags --refs https://github.com/using-system/oddyssey.git 'refs/tags/v*' || true) \
    | awk -F/ '{print $NF}' | (grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true) | sort -V)"
  if [ -z "$tags" ]; then
    echo "::error::no release tag of using-system/oddyssey could be read from github.com."
    exit 1
  fi
  if [ "$REQUESTED" = "latest" ]; then
    version="$(printf '%s\n' "$tags" | tail -1)"
  else
    version="$REQUESTED"
    case "$version" in v*) ;; *) version="v${version}" ;; esac
    if ! printf '%s\n' "$tags" | grep -qxF "$version"; then
      echo "::error::oddyssey-version '${REQUESTED}' is not a release tag of using-system/oddyssey (a plain vX.Y.Z, a full commit SHA, or latest)."
      exit 1
    fi
  fi
fi
echo "oddyssey ${version} (requested: ${REQUESTED})"
echo "version=${version}" >> "$GITHUB_OUTPUT"
