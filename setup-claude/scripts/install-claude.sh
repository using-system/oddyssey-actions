#!/usr/bin/env bash
# Install Claude Code from the release channel's own assets, verified against the release's manifest.
#
# Reads:  CLAUDE_CODE_VERSION - the Claude Code release pinned by action.yml
#         PREFIX - where the CLI lands (<prefix>/bin on the later steps' PATH)
# Writes: GITHUB_PATH - <prefix>/bin
#         GITHUB_OUTPUT - version=<the CLI version installed>
set -euo pipefail
case "$(uname -s)" in
  Linux) os=linux ;;
  Darwin) os=darwin ;;
  *) echo "::error::unsupported runner OS $(uname -s)"; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) arch=x64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) echo "::error::unsupported runner architecture $(uname -m)"; exit 1 ;;
esac
platform="${os}-${arch}"
# The release channel the official installer reads: <base>/<version>/
# manifest.json carries a sha256 per platform, the binary sits next to
# it. No installer script runs; nothing is fetched from npm.
base="https://downloads.claude.ai/claude-code-releases/${CLAUDE_CODE_VERSION}"
work="$(mktemp -d)"
curl -fsSL --retry 3 -o "${work}/manifest.json" "${base}/manifest.json"
expected="$(python3 -c '
import json, sys
platforms = json.load(open(sys.argv[1])).get("platforms") or {}
print((platforms.get(sys.argv[2]) or {}).get("checksum") or "")
' "${work}/manifest.json" "$platform")"
if ! printf '%s' "$expected" | grep -Eq '^[0-9a-f]{64}$'; then
  echo "::error::the manifest of Claude Code ${CLAUDE_CODE_VERSION} carries no checksum for ${platform}."
  exit 1
fi
curl -fsSL --retry 3 -o "${work}/claude" "${base}/${platform}/claude"
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "${work}/claude" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "${work}/claude" | awk '{print $1}')"
fi
if [ "$actual" != "$expected" ]; then
  echo "::error::claude (${platform}) does not match the manifest of Claude Code ${CLAUDE_CODE_VERSION} (got ${actual})."
  exit 1
fi
mkdir -p "${PREFIX}/bin"
mv "${work}/claude" "${PREFIX}/bin/claude"
chmod +x "${PREFIX}/bin/claude"
rm -rf "$work"
echo "${PREFIX}/bin" >> "$GITHUB_PATH"
# "2.1.267 (Claude Code)": the version must be the pin. The updater is
# off for this call and for every run (DISABLE_AUTOUPDATER on the
# launch line): the version installed is the version that runs.
answer="$(DISABLE_AUTOUPDATER=1 "${PREFIX}/bin/claude" --version)"
version="$(printf '%s\n' "$answer" | (sed -nE 's/^([0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?) \(Claude Code\)$/\1/p' || true))"
if [ "$version" != "$CLAUDE_CODE_VERSION" ]; then
  echo "::error::the installed Claude Code answered '${answer}', not version ${CLAUDE_CODE_VERSION}."
  exit 1
fi
echo "Claude Code ${version} (${platform}, checksum verified)"
echo "version=${version}" >> "$GITHUB_OUTPUT"
