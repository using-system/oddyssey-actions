"""On the runner, after `uses: ./odd-status` through a setup: the four
outputs the CI step passes as env have the shape a workflow gates on,
and the status is the package's own, recomputed by its script."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "odd-status" / "scripts"))
import verdict

pytestmark = pytest.mark.runner


def test_the_status_is_one_of_the_three():
    assert os.environ["STATUS"] in ("ok", "warning", "error")


def test_the_summary_is_one_line():
    assert os.environ["SUMMARY"].strip() and "\n" not in os.environ["SUMMARY"]


def test_the_todo_is_a_json_list():
    assert isinstance(json.loads(os.environ["TODO"]), list)


def test_the_report_is_the_answer():
    assert os.environ["REPORT"].strip()


def test_the_verdict_line():
    print(
        f"odd-status on {os.environ['ODDYSSEY_CLI']}: {os.environ['STATUS']} - {os.environ['SUMMARY']}"
    )


def test_the_status_is_the_package_s_own_verdict():
    # the CI cell runs the whole loop (no prompt, no scope): a fresh
    # rendering by the script the setup deployed opens with the same verdict
    script = (
        Path.home() / verdict.SKILLS[os.environ["ODDYSSEY_CLI"]] / verdict.STATUS_SCRIPT
    )
    assert script.is_file(), script
    rendering = subprocess.run(
        [sys.executable, str(script), "--render"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert verdict.rendered_verdict(rendering)["status"] == os.environ["STATUS"]
