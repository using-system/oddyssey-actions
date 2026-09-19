#!/usr/bin/env bash
# Run the packaged odd-status through opencode: the repository's one opencode
# launch line, scripts/run-opencode.sh at its root, which states what it reads
# and writes; COMMAND is the step's env.
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/../../scripts/run-opencode.sh"
