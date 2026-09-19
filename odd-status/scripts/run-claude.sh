#!/usr/bin/env bash
# Run the packaged odd-status through Claude Code: the repository's one claude
# launch line, scripts/run-claude.sh at its root, which states what it reads
# and writes; COMMAND is the step's env.
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/../../scripts/run-claude.sh"
