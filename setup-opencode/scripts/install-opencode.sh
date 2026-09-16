#!/usr/bin/env bash
# Install opencode from the release's own assets, verified against the checksum pinned for this runner.
#
# Reads:  OPENCODE_VERSION - the opencode release pinned by action.yml
#         SHA256_LINUX_X64, SHA256_LINUX_ARM64, SHA256_DARWIN_ARM64, SHA256_DARWIN_X64 - its assets' checksums, pinned there too
#         PREFIX - where opencode lands (<prefix>/bin on the later steps' PATH)
# Writes: GITHUB_PATH - <prefix>/bin
#         GITHUB_OUTPUT - version=<the opencode version installed>
set -euo pipefail
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64|Linux/amd64) asset="opencode-linux-x64.tar.gz"; expected="$SHA256_LINUX_X64" ;;
  Linux/aarch64|Linux/arm64) asset="opencode-linux-arm64.tar.gz"; expected="$SHA256_LINUX_ARM64" ;;
  Darwin/arm64) asset="opencode-darwin-arm64.zip"; expected="$SHA256_DARWIN_ARM64" ;;
  Darwin/x86_64) asset="opencode-darwin-x64.zip"; expected="$SHA256_DARWIN_X64" ;;
  *) echo "::error::unsupported runner $(uname -s)/$(uname -m)"; exit 1 ;;
esac
work="$(mktemp -d)"
curl -fsSL --retry 3 -o "${work}/${asset}" "https://github.com/sst/opencode/releases/download/v${OPENCODE_VERSION}/${asset}"
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "${work}/${asset}" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "${work}/${asset}" | awk '{print $1}')"
fi
if [ "$actual" != "$expected" ]; then
  echo "::error::${asset} of opencode v${OPENCODE_VERSION} does not match the checksum this action pins (got ${actual})."
  exit 1
fi
mkdir -p "${PREFIX}/bin"
case "$asset" in
  *.tar.gz) tar -xzf "${work}/${asset}" -C "${PREFIX}/bin" ;;
  *.zip) unzip -q -o "${work}/${asset}" -d "${PREFIX}/bin" ;;
esac
chmod +x "${PREFIX}/bin/opencode"
rm -rf "$work"
echo "${PREFIX}/bin" >> "$GITHUB_PATH"
version="$("${PREFIX}/bin/opencode" --version | tr -d '[:space:]')"
if [ "$version" != "$OPENCODE_VERSION" ]; then
  echo "::error::the installed opencode answered '${version}', not version ${OPENCODE_VERSION}."
  exit 1
fi
echo "opencode ${version} (${asset}, checksum verified)"
echo "version=${version}" >> "$GITHUB_OUTPUT"
