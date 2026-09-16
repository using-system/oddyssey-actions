"""On the runner, after `uses: ./odd-status` through a setup: the outputs
the CI step passes as env have the shape a workflow gates on."""

import json
import os

import pytest

pytestmark = pytest.mark.runner


def test_the_status_is_one_of_the_three():
    assert os.environ["STATUS"] in ("ok", "warning", "error")


def test_the_report_is_the_answer():
    assert os.environ["REPORT"].strip()


def test_the_todo_is_a_json_list():
    assert isinstance(json.loads(os.environ["TODO"]), list)


def test_the_verdict_line():
    print(
        f"odd-status on {os.environ['ODDYSSEY_CLI']}: {os.environ['STATUS']} - {os.environ['SUMMARY']}"
    )
