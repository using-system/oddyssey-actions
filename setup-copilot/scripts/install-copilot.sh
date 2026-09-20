#!/usr/bin/env bash
# Install the Copilot CLI from the release's own assets, verified against its SHA256SUMS.
#
# Reads:  COPILOT_CLI_VERSION - the Copilot CLI release pinned by action.yml
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
asset="copilot-${os}-${arch}.tar.gz"
base="https://github.com/github/copilot-cli/releases/download/v${COPILOT_CLI_VERSION}"
work="$(mktemp -d)"
# --retry alone covers a timeout or a 408/429/5xx; a connection reset
# is not "transient" to curl. --retry-all-errors makes the three retries
# cover every failure; what lands is verified below all the same.
curl -fsSL --retry 3 --retry-all-errors -o "${work}/${asset}" "${base}/${asset}"
curl -fsSL --retry 3 --retry-all-errors -o "${work}/SHA256SUMS.txt" "${base}/SHA256SUMS.txt"
expected="$( (grep -E "  ${asset}\$" "${work}/SHA256SUMS.txt" || true) | awk '{print $1}')"
if [ -z "$expected" ]; then
  echo "::error::SHA256SUMS.txt of copilot-cli v${COPILOT_CLI_VERSION} carries no entry for ${asset}."
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "${work}/${asset}" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "${work}/${asset}" | awk '{print $1}')"
fi
if [ "$actual" != "$expected" ]; then
  echo "::error::${asset} does not match SHA256SUMS.txt of copilot-cli v${COPILOT_CLI_VERSION} (got ${actual})."
  exit 1
fi
mkdir -p "${PREFIX}/bin"
tar -xzf "${work}/${asset}" -C "${PREFIX}/bin"
chmod +x "${PREFIX}/bin/copilot"
rm -rf "$work"
echo "${PREFIX}/bin" >> "$GITHUB_PATH"
# Two lines ("GitHub Copilot CLI 1.0.85." then an update hint):
# the first one, read whole rather than through a pipe the CLI
# would see closed early. The version must be the pin.
answer="$("${PREFIX}/bin/copilot" --no-auto-update --version)"
answer="${answer%%$'\n'*}"
version="$(printf '%s\n' "$answer" | (sed -nE 's/^GitHub Copilot CLI ([0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z]+)?)\.?$/\1/p' || true))"
if [ "$version" != "$COPILOT_CLI_VERSION" ]; then
  echo "::error::the installed Copilot CLI answered '${answer}', not version ${COPILOT_CLI_VERSION}."
  exit 1
fi
echo "Copilot CLI ${version} (${asset}, checksum verified)"
echo "version=${version}" >> "$GITHUB_OUTPUT"
