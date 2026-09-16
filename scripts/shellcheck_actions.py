"""Run shellcheck over the bash `run:` blocks of every `*/action.yml`.

actionlint parses workflows only, so a composite action's shell steps
would otherwise go unchecked. Each block is checked as a standalone bash
script; a finding names the action, the step and the line inside the
block. Exit 1 when any block fails.

    python3 scripts/shellcheck_actions.py [--shellcheck <binary>]
"""

import argparse
import pathlib
import subprocess
import sys

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--shellcheck",
        default="shellcheck",
        help="the shellcheck binary (default: on PATH)",
    )
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    failed = 0
    checked = 0
    for action in sorted(root.glob("*/action.yml")):
        steps = yaml.safe_load(action.read_text())["runs"]["steps"]
        for step in steps:
            if "run" not in step or step.get("shell") != "bash":
                continue
            checked += 1
            name = f"{action.relative_to(root)} / {step.get('name') or step.get('id')}"
            result = subprocess.run(
                [args.shellcheck, "--shell=bash", "--severity=style", "-"],
                input=step["run"],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                failed += 1
                print(f"--- {name}")
                print(result.stdout, end="")
                print(result.stderr, end="", file=sys.stderr)
    print(f"{checked} bash step(s) checked, {failed} with findings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
