#!/usr/bin/env bash
# Resolve the oddyssey release to install, against the repository's release tags
# and the minimum this release of the actions supports - the one resolve step,
# run by every setup action.
#
# Reads:  REQUESTED - the oddyssey-version input: a tag, a full commit SHA, or latest
#         ODDYSSEY_MINIMUM_VERSION, the one-line file at the repository root - the minimum
# Writes: GITHUB_OUTPUT - version=<vX.Y.Z or the SHA>
#                         note=<empty, or "requested: <tag>, below the minimum">
set -euo pipefail
minimum="$(tr -d '[:space:]' < "$(dirname "${BASH_SOURCE[0]}")/../ODDYSSEY_MINIMUM_VERSION")"
if ! printf '%s' "$minimum" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "::error::ODDYSSEY_MINIMUM_VERSION must hold one plain vX.Y.Z, got '${minimum}'."
  exit 1
fi
# Resolved first: a wrong input costs nothing else. The value
# reaches $GITHUB_OUTPUT: a case pattern sees it whole, so a second
# line cannot pass. The characters are listed, not ranged: a range in
# a case pattern follows the locale, and A-Za-z admits an accented
# letter in some.
case "$REQUESTED" in
  ''|*[!ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-]*)
    echo "::error::oddyssey-version must be a tag, a full commit SHA or latest, got '${REQUESTED}'."
    exit 1 ;;
esac
note=""
if printf '%s' "$REQUESTED" | grep -Eq '^[0-9a-f]{40}$'; then
  # A full commit SHA is taken as is - the one immutable form, and one
  # no version order applies to: the minimum is not checked.
  version="$REQUESTED"
  echo "oddyssey ${version} (requested: ${REQUESTED}, a commit SHA taken as is)"
else
  # A tag is checked against the remote's release tags (plain vX.Y.Z),
  # read with no API call and no token.
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
  # Below the minimum, the minimum is installed and the run says so: an
  # older package lacks what this release of the actions reads from it.
  if [ "$version" != "$minimum" ] \
    && [ "$(printf '%s\n%s\n' "$version" "$minimum" | sort -V | head -1)" = "$version" ]; then
    if ! printf '%s\n' "$tags" | grep -qxF "$minimum"; then
      echo "::error::the minimum oddyssey version ${minimum} is not a release tag of using-system/oddyssey."
      exit 1
    fi
    note="requested: ${REQUESTED}, below the minimum"
    version="$minimum"
    echo "::notice::oddyssey ${version} (${note})"
  else
    echo "oddyssey ${version} (requested: ${REQUESTED})"
  fi
fi
{
  echo "version=${version}"
  echo "note=${note}"
} >> "$GITHUB_OUTPUT"
