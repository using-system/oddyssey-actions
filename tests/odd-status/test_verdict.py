import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "odd-status" / "scripts" / "verdict.py"
sys.path.insert(0, str(SCRIPT.parent))
import verdict

ANSWER = (
    "# ODD loop status\n\nThe loop has not started.\n\n```json\n"
    '{"status": "warning", "summary": "No report yet.", '
    '"todo": [{"action": "run /odd-observe", "why": "nothing measured"}, "commit the report"]}\n```\n'
)


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


def test_parse_verdict_reads_the_block_and_normalises_todo():
    parsed, well_formed = verdict.parse_verdict(ANSWER)
    assert well_formed
    assert parsed["status"] == "warning"
    assert parsed["source"] == "model"
    assert parsed["summary"] == "No report yet."
    assert parsed["todo"] == [
        {"action": "run /odd-observe", "why": "nothing measured"},
        {"action": "commit the report", "why": ""},
    ]


def test_fence_variants_and_flattening():
    for fence in ("```JSON", "```json "):
        block = fence + '\r\n{"status": "ok", "summary": "a\\nb  c"}\r\n```'
        parsed, ok = verdict.parse_block(block)
        assert ok and parsed["status"] == "ok" and parsed["summary"] == "a b c"
    nested = '````markdown\n```json\n{"status": "ok"}\n```\n````\n'
    assert verdict.parse_block(nested)[0]["status"] == "ok"


def test_non_string_content_is_ignored():
    stream = [{"type": "assistant.message", "data": {"content": [{"type": "text"}]}}]
    assert verdict.final_answer("copilot", stream) == ""
    stream = [{"type": "text", "part": {"messageID": "m", "text": {"x": 1}}}]
    assert verdict.final_answer("opencode", stream) == ""


def test_parse_verdict_takes_the_last_valid_block():
    answer = '```json\n{"status": "ok"}\n```\ntext\n```json\n{"status": "error", "todo": []}\n```\n'
    parsed, _ = verdict.parse_block(answer)
    assert parsed["status"] == "error"


@pytest.mark.parametrize(
    "answer",
    [
        "no block at all",
        "```json\n{not json}\n```",
        '```json\n{"status": "fine"}\n```',
        '```json\n["a"]\n```',
    ],
)
def test_missing_or_malformed_block_is_an_error(answer):
    parsed, well_formed = verdict.parse_verdict(answer)
    assert not well_formed
    assert parsed["status"] == "error"
    assert parsed["source"] == "model"
    assert "no verdict block" in parsed["summary"]


# The rendering get-status opens with (oddyssey#601): the verdict and the
# todo lines are the package's own, the model writes the summary only.
RENDERED = (
    "# ODD loop status\n\n"
    "- verdict: warning - checkout / grafana / prod: verification due\n"
    "- todo: checkout / grafana / prod: verification due - 3 commits since 2026-09-10-1200-checkout.md"
    " (observe); last verify PASS · start the loop: /odd-instrument-otel or /odd-observe\n\n"
    "## Loop state\n\n| Lineage | Action |\n|---|---|\n| checkout / grafana / prod | verification due |\n\n"
    "- checkout / grafana / prod: last report 2026-09-10-1200-checkout.md (observe); verdict 1 of 8 rulings closed\n\n"
    "Verdict: the loop is due.\n\n"
    '```json\n{"status": "ok", "summary": "Three commits await a verification.", '
    '"todo": [{"action": "the models own todo", "why": "ignored"}]}\n```\n'
)


def test_the_rendering_s_verdict_and_todo_win_over_the_block():
    parsed, well_formed = verdict.parse_verdict(RENDERED)
    assert well_formed
    assert parsed["source"] == "rendering"
    assert parsed["status"] == "warning"
    assert parsed["summary"] == "Three commits await a verification."
    assert parsed["todo"] == [
        {
            "action": "checkout / grafana / prod: verification due",
            "why": "3 commits since 2026-09-10-1200-checkout.md (observe); last verify PASS",
        },
        {"action": "start the loop: /odd-instrument-otel or /odd-observe", "why": ""},
    ]


@pytest.mark.parametrize(
    "lines",
    [
        "- verdict: ok - every lineage can rest\n- todo: nothing to do\n",
        "- **verdict: ok** \u2014 every lineage can rest\n- **todo: nothing to do**\n",
        "* **Verdict:** OK \u2013 every lineage can rest\n* **Todo:** nothing to do\n",
        "verdict: ok\ntodo:\n",
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


def test_a_rendering_without_a_block_keeps_its_verdict():
    answer = "# ODD loop status\n\n- verdict: error - a finding regressed\n- todo: rule on F2 - regressed\n"
    parsed, well_formed = verdict.parse_verdict(answer)
    assert not well_formed
    assert parsed["status"] == "error"
    assert parsed["source"] == "rendering"
    assert parsed["summary"] == "the run wrote no summary"
    assert parsed["todo"] == [{"action": "rule on F2", "why": "regressed"}]


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
    code, out, outputs = run(tmp_path, "copilot", copilot_stream(ANSWER), "none")
    assert code == 0
    assert outputs["status"] == "warning"
    assert json.loads(outputs["todo"])[0]["action"] == "run /odd-observe"
    assert outputs["report"] == ANSWER.rstrip("\n")
    assert outputs["source"] == "model"
    assert "odd-status: warning" in out and "verdict from the model" in out
    summary = (tmp_path / "summary.md").read_text()
    assert summary.startswith("### odd-status: ⚠️ warning")
    assert "a package that predates it" in summary


def test_outputs_carry_the_rendering_s_verdict(tmp_path):
    code, out, outputs = run(tmp_path, "opencode", opencode_stream(RENDERED), "warning")
    assert code == 1
    assert outputs["status"] == "warning"
    assert outputs["source"] == "rendering"
    assert outputs["summary"] == "Three commits await a verification."
    assert json.loads(outputs["todo"])[1]["action"].startswith("start the loop")
    assert "verdict from the rendering" in out
    assert "the package's own verdict" in (tmp_path / "summary.md").read_text()


@pytest.mark.parametrize("fail_on,code", [("none", 0), ("warning", 1), ("error", 0)])
def test_fail_on_levels(tmp_path, fail_on, code):
    assert run(tmp_path, "opencode", opencode_stream(ANSWER), fail_on)[0] == code


ERROR_ANSWER = (
    '```json\n{"status": "error", "summary": "verification failed", "todo": []}\n```\n'
)


@pytest.mark.parametrize(
    "answer,fail_on,code",
    [
        (ERROR_ANSWER, "error", 1),
        (ERROR_ANSWER, "warning", 1),
        (ERROR_ANSWER, "none", 0),
        ("an answer with no block", "error", 1),
        ("an answer with no block", "none", 0),
    ],
)
def test_error_verdicts_gate(tmp_path, answer, fail_on, code):
    rc, _out, outputs = run(tmp_path, "copilot", copilot_stream(answer), fail_on)
    assert rc == code
    assert outputs["status"] == "error"


def test_no_answer_fails_whatever_fail_on(tmp_path):
    code, out, _ = run(tmp_path, "copilot", '{"type": "result", "data": {}}\n', "none")
    assert code == 1
    assert "no answer" in out


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
