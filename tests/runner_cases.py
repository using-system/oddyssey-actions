"""What every setup action leaves on a runner, read from the CI step's
environment: the requested and resolved oddyssey version, the model."""

import os
import re
import subprocess

# The nine skills oddyssey ships.
SKILLS = [
    "backend-configuration",
    "get-status",
    "k6-guides",
    "observability-cli-guides",
    "odd-memory",
    "otel-guides",
    "package-layout",
    "run-scenario",
    "setup-local-stack",
]


def check_resolved_version():
    requested, resolved = os.environ["REQUESTED"], os.environ["RESOLVED"]
    assert re.fullmatch(r"v\d+\.\d+\.\d+", resolved), resolved
    if requested != "latest":
        assert resolved == requested


def check_checkout_clean():
    assert (
        subprocess.run(
            ["git", "status", "--porcelain"], text=True, capture_output=True, check=True
        ).stdout
        == ""
    )
