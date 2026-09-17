#!/usr/bin/env bash
# Resolve the oddyssey release to install: the repository's one resolve step,
# scripts/resolve-oddyssey.sh at its root, which states what it reads and writes.
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/../../scripts/resolve-oddyssey.sh"
