#!/usr/bin/env bash
# Run the packaged odd-status through the Copilot CLI: the repository's one copilot
# launch line, scripts/run-copilot.sh at its root, which states what it reads
# and writes; COMMAND is the step's env.
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/../../scripts/run-copilot.sh"
