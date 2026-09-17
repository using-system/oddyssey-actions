import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "odd-status" / "scripts" / "verdict.py"
sys.path.insert(0, str(SCRIPT.parent))
import verdict

# The rendering get-status opens with: the verdict and the todo lines are
# the package's own, the model writes the summary only.
ANSWER = (
    "# ODD loop status\n\n"
    "- verdict: warning - checkout / grafana / prod: verification due\n"
    "- todo: checkout / grafana / prod: verification due - 3 commits since 2026-09-10-1200-checkout.md"
    " (observe); last verify PASS · start the loop: /odd-instrument-otel or /odd-observe\n\n"
    "## Loop state\n\n| Lineage | Action |\n|---|---|\n| checkout / grafana / prod | verification due |\n\n"
    "- checkout / grafana / prod: last report 2026-09-10-1200-checkout.md (observe); verdict 1 of 8 rulings closed\n\n"
    "Verdict: the loop is due.\n\n"
    '```json\n{"summary": "Three commits await a verification."}\n```\n'
)
TODO = [
    {
        "action": "checkout / grafana / prod: verification due",
        "why": "3 commits since 2026-09-10-1200-checkout.md (observe); last verify PASS",
    },
    {"action": "start the loop: /odd-instrument-otel or /odd-observe", "why": ""},
]
NO_VERDICT_LINE = '# ODD loop status\n\nThe loop has not started.\n\n```json\n{"summary": "No report yet."}\n```\n'


def copilot_stream(answer: str) -> str:
    lines = [
        {"type": "assistant.message", "data": {"content": ""}},
        {"type": "tool.execution_start", "data": {"toolName": "skill"}},
        {"type": "assistant.message", "data": {"content": "an earlier turn"}},
        {"type": "assistant.message", "data": {"content": answer}},
        {"type": "result", "data": {}},
    ]
    return "\n".join(json.dumps(line) for line in lines) + "\n"


def claude_result(answer: str, error: bool = False) -> str:
    return (
        json.dumps(
            {
                "type": "result",
                "subtype": "error" if error else "success",
                "is_error": error,
                "result": answer,
            },
            indent=2,
        )
        + "\n"
    )


def opencode_stream(answer: str) -> str:
    half = len(answer) // 2
    lines = [
        {"type": "text", "part": {"messageID": "m1", "text": "thinking aloud"}},
        {"type": "tool_use", "part": {"tool": "skill"}},
        {"type": "text", "part": {"messageID": "m2", "text": answer[:half]}},
        {"type": "text", "part": {"messageID": "m2", "text": answer[half:]}},
        {"type": "step_finish", "part": {"reason": "stop"}},
    ]
    return "\n".join(json.dumps(line) for line in lines) + "\n"


@pytest.mark.parametrize(
    "cli,stream", [("copilot", copilot_stream), ("opencode", opencode_stream)]
)
def test_final_answer_is_the_last_message(cli, stream):
    assert verdict.final_answer(cli, verdict.events_from_text(stream(ANSWER))) == ANSWER


def test_claude_answer_is_the_result_object_over_several_lines():
    assert (
        verdict.final_answer("claude", verdict.events_from_text(claude_result(ANSWER)))
        == ANSWER
    )


def test_claude_error_result_is_no_answer():
    assert (
        verdict.final_answer(
            "claude", verdict.events_from_text(claude_result("boom", error=True))
        )
        == ""
    )


def test_non_string_content_is_ignored():
    stream = [{"type": "assistant.message", "data": {"content": [{"type": "text"}]}}]
    assert verdict.final_answer("copilot", stream) == ""
    stream = [{"type": "text", "part": {"messageID": "m", "text": {"x": 1}}}]
    assert verdict.final_answer("opencode", stream) == ""


def test_the_verdict_is_the_rendering_s_lines_and_the_block_s_summary():
    assert verdict.parse_verdict(ANSWER) == {
        "status": "warning",
        "summary": "Three commits await a verification.",
        "todo": TODO,
    }


def test_fence_variants_and_flattening():
    for fence in ("```JSON", "```json "):
        block = fence + '\r\n{"summary": "a\\nb  c"}\r\n```'
        assert verdict.parse_block(block) == "a b c"
    nested = '````markdown\n```json\n{"summary": "nested"}\n```\n````\n'
    assert verdict.parse_block(nested) == "nested"


def test_the_last_block_with_a_summary_wins():
    answer = '```json\n{"summary": "first"}\n```\ntext\n```json\n{"summary": "last"}\n```\n```json\n{"status": "ok"}\n```\n'
    assert verdict.parse_block(answer) == "last"


@pytest.mark.parametrize(
    "block",
    [
        "",
        "```json\n{not json}\n```",
        '```json\n{"summary": ""}\n```',
        '```json\n{"summary": 3}\n```',
        '```json\n["a"]\n```',
    ],
)
def test_a_missing_or_malformed_block_is_no_summary(block):
    answer = (
        "- verdict: error - a finding regressed\n- todo: rule on F2 - regressed\n"
        + block
    )
    assert verdict.parse_verdict(answer) == {
        "status": "error",
        "summary": "the run wrote no summary",
        "todo": [{"action": "rule on F2", "why": "regressed"}],
    }


@pytest.mark.parametrize("answer", [NO_VERDICT_LINE, "no rendering at all"])
def test_no_verdict_line_is_an_error_naming_the_minimum(answer):
    assert verdict.MINIMUM.startswith("v")
    assert verdict.parse_verdict(answer) == {
        "status": "error",
        "summary": f"no verdict line in the rendering: oddyssey {verdict.MINIMUM} or newer is needed",
        "todo": [],
    }


@pytest.mark.parametrize(
    "lines",
    [
        "- verdict: ok - every lineage can rest\n- todo: nothing to do\n",
        "- **verdict: ok** — every lineage can rest\n- **todo: nothing to do**\n",
        "* **Verdict:** OK – every lineage can rest\n* **Todo:** nothing to do\n",
        "verdict: ok\ntodo:\n",
        "- **Verdict:** `ok` \u2014 every lineage can rest\n- **Todo:** `nothing to do`\n",
    ],
)
def test_a_dressed_up_rendering_still_reads(lines):
    rendered = verdict.rendered_verdict("# ODD loop status\n\n" + lines)
    assert rendered == {"status": "ok", "todo": []}


def test_prose_naming_a_verdict_is_not_the_rendering_s_line():
    assert (
        verdict.rendered_verdict(
            "Verdict: the loop rests.\n- verdict 1 of 8 rulings closed\n"
        )
        is None
    )
    assert verdict.rendered_verdict("- checkout: verdict: ok\n") is None


def test_backticks_around_each_todo_item_are_dressing():
    answer = "- verdict: warning - due\n- todo: `a: b - c` · `d`\n"
    assert verdict.rendered_verdict(answer)["todo"] == [
        {"action": "a: b", "why": "c"},
        {"action": "d", "why": ""},
    ]


def test_the_first_verdict_line_is_the_rendering_s():
    answer = (
        "- verdict: error - a finding regressed\n- todo: rule on F1 - regressed.\n\n"
        "My reading:\n- verdict: ok - all good\n- todo: nothing to do\n"
    )
    assert verdict.rendered_verdict(answer) == {
        "status": "error",
        "todo": [{"action": "rule on F1", "why": "regressed"}],
    }


def test_the_action_declares_every_output_the_script_writes(tmp_path):
    import yaml

    declared = yaml.safe_load((SCRIPT.parents[1] / "action.yml").read_text())["outputs"]
    out = tmp_path / "out"
    verdict.write_outputs(out, verdict.parse_verdict(ANSWER), "report")
    written = {
        line.partition("<<")[0] for line in out.read_text().splitlines() if "<<" in line
    }
    assert written == set(declared) == {"status", "summary", "todo", "report"}


def run(tmp_path: Path, cli: str, text: str, fail_on: str) -> tuple[int, str, dict]:
    events = tmp_path / "run.jsonl"
    events.write_text(text)
    outputs, summary = tmp_path / "out", tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cli",
            cli,
            "--events",
            str(events),
            "--fail-on",
            fail_on,
            "--outputs",
            str(outputs),
            "--summary",
            str(summary),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    parsed = {}
    lines = outputs.read_text().splitlines() if outputs.exists() else []
    i = 0
    while i < len(lines):
        key, _, delim = lines[i].partition("<<")
        j = lines.index(delim, i + 1)
        parsed[key] = "\n".join(lines[i + 1 : j])
        i = j + 1
    return proc.returncode, proc.stdout + proc.stderr, parsed


def test_outputs_and_gate(tmp_path):
    code, out, outputs = run(tmp_path, "opencode", opencode_stream(ANSWER), "warning")
    assert code == 1
    assert outputs["status"] == "warning"
    assert outputs["summary"] == "Three commits await a verification."
    assert json.loads(outputs["todo"]) == TODO
    assert outputs["report"] == ANSWER.rstrip("\n")
    assert "odd-status: warning - Three commits await a verification. (2 todo)" in out
    assert "::error::odd-status is warning and fail-on is warning." in out
    summary = (tmp_path / "summary.md").read_text()
    assert summary.startswith(
        "### odd-status: ⚠️ warning\n\nThree commits await a verification.\n\n| # | Action | Why |"
    )
    assert "<details><summary>The run's report</summary>" in summary


@pytest.mark.parametrize("fail_on,code", [("none", 0), ("warning", 1), ("error", 0)])
def test_fail_on_levels(tmp_path, fail_on, code):
    assert run(tmp_path, "copilot", copilot_stream(ANSWER), fail_on)[0] == code


ERROR_ANSWER = "- verdict: error - a verification failed\n- todo: nothing to do\n"


@pytest.mark.parametrize(
    "answer,fail_on,code",
    [
        (ERROR_ANSWER, "error", 1),
        (ERROR_ANSWER, "warning", 1),
        (ERROR_ANSWER, "none", 0),
        (NO_VERDICT_LINE, "error", 1),
        (NO_VERDICT_LINE, "none", 0),
    ],
)
def test_error_verdicts_gate(tmp_path, answer, fail_on, code):
    rc, _out, outputs = run(tmp_path, "copilot", copilot_stream(answer), fail_on)
    assert rc == code
    assert outputs["status"] == "error"


def test_no_answer_fails_whatever_fail_on(tmp_path):
    code, out, outputs = run(
        tmp_path, "copilot", '{"type": "result", "data": {}}\n', "none"
    )
    assert code == 1
    assert "::error::the run produced no answer." in out
    assert outputs["status"] == "error"
    assert outputs["summary"] == "the run produced no answer"
