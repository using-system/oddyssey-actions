import json
import os
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
# what the package's script renders for ANSWER's loop: the same two lines
RENDERED_WARNING = ANSWER.split("\n## Loop state")[0] + "\n"
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


def test_the_verdict_is_the_package_s_lines_and_the_block_s_summary(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package(tmp_path, "copilot", RENDERED_WARNING)
    assert verdict.parse_verdict(ANSWER, "copilot", tmp_path) == {
        "status": "warning",
        "summary": "Three commits await a verification.",
        "todo": TODO,
        "rendering": RENDERED_WARNING,
        "answered": "warning",
        "scope": [],
        "rulings": [],
    }


def test_fence_variants_and_flattening():
    for fence in ("```JSON", "```json "):
        block = fence + '\r\n{"summary": "a\\nb  c"}\r\n```'
        assert verdict.parse_block(block)["summary"] == "a b c"
    nested = '````markdown\n```json\n{"summary": "nested"}\n```\n````\n'
    assert verdict.parse_block(nested)["summary"] == "nested"


def test_the_last_block_with_a_summary_wins():
    answer = '```json\n{"summary": "first"}\n```\ntext\n```json\n{"summary": "last"}\n```\n```json\n{"status": "ok"}\n```\n'
    assert verdict.parse_block(answer)["summary"] == "last"


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
def test_a_missing_or_malformed_block_is_no_summary(block, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package(tmp_path, "copilot")
    answer = (
        "- verdict: error - a finding regressed\n- todo: rule on F2 - regressed\n"
        + block
    )
    parsed = verdict.parse_verdict(answer, "copilot", tmp_path)
    assert parsed["status"] == "error"
    assert parsed["summary"] == "the run wrote no summary"
    assert parsed["todo"] == [
        {"action": "checkout / grafana / prod: rule on F2", "why": "regressed"}
    ]


@pytest.mark.parametrize("answer", [NO_VERDICT_LINE, "no rendering at all"])
def test_an_answer_without_a_verdict_line_still_gets_the_package_s(
    answer, tmp_path, monkeypatch
):
    # the answer's line was never the verdict: the package's rendering is
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package(tmp_path, "claude")
    parsed = verdict.parse_verdict(answer, "claude", tmp_path)
    assert parsed["status"] == "error" and parsed["answered"] is None
    assert parsed["todo"] == [
        {"action": "checkout / grafana / prod: rule on F2", "why": "regressed"}
    ]


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
    parsed = {"status": "warning", "summary": "s", "todo": TODO, "answered": None}
    verdict.write_outputs(out, parsed, "report")
    written = {
        line.partition("<<")[0] for line in out.read_text().splitlines() if "<<" in line
    }
    assert written == set(declared) == {"status", "summary", "todo", "report"}


RENDERING = (
    "# ODD loop status\n\n"
    "- verdict: error - checkout / grafana / prod: F2 regressed\n"
    "- todo: checkout / grafana / prod: rule on F2 - regressed\n\n"
    "## Loop state\n"
)
FAKE_SCRIPT = """\
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
(here / "argv.json").write_text(json.dumps(sys.argv[1:]))
(here / "cwd.txt").write_text(str(Path.cwd()))
if (here / "fail").exists():
    print("boom", file=sys.stderr)
    sys.exit(3)
if "--render" not in sys.argv:
    if "--full" in sys.argv:
        print("odd_status.py: error: --full only applies with --render", file=sys.stderr)
        sys.exit(2)
    matched = int((here / "matched").read_text()) if (here / "matched").exists() else 1
    print(json.dumps({"matched": matched, "verdict": {"status": "x"}}))
    sys.exit(0)
sys.stdout.write((here / "rendering.md").read_text())
"""


def package(home: Path, cli: str, rendering: str = RENDERING) -> Path:
    """The package's get-status script, as the setup for `cli` deploys it
    under the runner's home: a fake that prints `rendering` and records
    its arguments and its working directory."""
    scripts = home / verdict.SKILLS[cli] / "get-status" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "odd_status.py").write_text(FAKE_SCRIPT)
    (scripts / "rendering.md").write_text(rendering)
    return scripts


def test_the_block_carries_the_summary_and_the_flags():
    block = '```json\n{"summary": "fine", "flags": ["--service", "checkout", "--full"]}\n```'
    assert verdict.parse_block(block) == {
        "summary": "fine",
        "flags": ["--service", "checkout", "--full"],
    }
    assert verdict.parse_block('```json\n{"summary": "fine"}\n```') == {
        "summary": "fine",
        "flags": [],
    }
    # a run that reported its flags but wrote no sentence still reports them
    assert verdict.parse_block('```json\n{"flags": ["--full"]}\n```') == {
        "summary": "",
        "flags": ["--full"],
    }


PROMPT = "the checkout service on prod, grafana"


@pytest.mark.parametrize(
    "flags,scope,rulings",
    [
        ([], [], []),
        (["--full"], ["--full"], []),
        (
            ["--service", "checkout", "--stack", "grafana", "--env", "prod"],
            ["--service", "checkout", "--stack", "grafana", "--env", "prod"],
            [],
        ),
        (["--service", "Checkout"], ["--service", "Checkout"], []),
        # the run's rulings are kept apart, never in the scope
        (
            ["--ruled", "2026-09-10-1200-checkout.md/F2=fixed", "--full"],
            ["--full"],
            ["--ruled", "2026-09-10-1200-checkout.md/F2=fixed"],
        ),
        (
            ["--runtime", "src", "--non-runtime", "docs"],
            [],
            ["--runtime", "src", "--non-runtime", "docs"],
        ),
        # the run's formatting is normalised
        (["--render", "--service checkout"], ["--service", "checkout"], []),
        (
            ["--service=checkout", "--env=prod"],
            ["--service", "checkout", "--env", "prod"],
            [],
        ),
    ],
)
def test_the_scope_the_prompt_names_is_kept_and_the_rulings_set_apart(
    flags, scope, rulings
):
    assert verdict.validate_flags(flags, PROMPT) == {"scope": scope, "rulings": rulings}


@pytest.mark.parametrize(
    "flags",
    [
        ["--repo", "/elsewhere"],
        ["--repository", "x=/elsewhere"],
        ["--today", "2020-01-01"],
        ["--service"],
        ["--service", "--full"],
        ["--full", "extra"],
        ["checkout"],
        ["--ruled", "a b"],
        [3],
        "not a list",
        ["--service", "x\ny"],
        ["--service", "=checkout"],
        # a scope the prompt does not name
        ["--service", "cart"],
        ["--env", "none"],
        ["--stack", "local"],
        # a word of the prompt, not a part of one
        ["--service", "check"],
        ["--service", "checkout-svc"],
    ],
)
def test_any_other_flag_or_scope_is_refused(flags):
    with pytest.raises(ValueError):
        verdict.validate_flags(flags, PROMPT)


def test_an_empty_prompt_is_the_whole_loop_and_takes_no_scope():
    with pytest.raises(ValueError, match="did not scope"):
        verdict.validate_flags(["--service", "checkout"], "")
    assert verdict.validate_flags(["--full"], "") == {
        "scope": ["--full"],
        "rulings": [],
    }


def test_the_status_and_todo_are_recomputed_by_the_package_script(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    scripts = package(tmp_path, "copilot")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    computed = verdict.computed_verdict("copilot", ["--service", "checkout"], checkout)
    assert computed == {
        "status": "error",
        "todo": [
            {"action": "checkout / grafana / prod: rule on F2", "why": "regressed"}
        ],
        "rendering": RENDERING,
    }
    assert json.loads((scripts / "argv.json").read_text()) == [
        "--render",
        "--service",
        "checkout",
    ]
    assert (scripts / "cwd.txt").read_text() == str(checkout)


def test_a_scope_matching_no_report_is_refused(tmp_path, monkeypatch):
    # narrowed to nothing, the status would read warning whatever the loop
    # holds: a gate that saw no report has gated nothing
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    scripts = package(tmp_path, "opencode")
    (scripts / "matched").write_text("0")
    with pytest.raises(verdict.ComputationError, match="matches no stored report"):
        verdict.computed_verdict("opencode", ["--service", "the"], tmp_path)
    assert json.loads((scripts / "argv.json").read_text()) == ["--service", "the"]
    # --full alone is no scope: nothing to match
    assert (
        verdict.computed_verdict("opencode", ["--full"], tmp_path)["status"] == "error"
    )


def test_full_goes_to_the_rendering_only(tmp_path, monkeypatch):
    # the package's parser refuses --full without --render: the fact-sheet
    # run gets the scope alone, the rendering gets both
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    scripts = package(tmp_path, "claude")
    computed = verdict.computed_verdict(
        "claude", ["--service", "checkout", "--full"], tmp_path
    )
    assert computed["status"] == "error"
    assert json.loads((scripts / "argv.json").read_text()) == [
        "--render",
        "--service",
        "checkout",
        "--full",
    ]


@pytest.mark.parametrize("cli", ["copilot", "opencode", "claude"])
def test_the_script_is_looked_up_where_the_cli_s_setup_deploys_it(
    tmp_path, monkeypatch, cli
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package(tmp_path, cli, "- verdict: ok - all\n- todo: nothing to do\n")
    assert verdict.computed_verdict(cli, [], tmp_path)["status"] == "ok"


def test_a_missing_script_is_an_error_naming_the_path_and_the_minimum(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises(verdict.ComputationError) as failure:
        verdict.computed_verdict("claude", [], tmp_path)
    assert ".claude/skills/get-status/scripts/odd_status.py" in str(failure.value)
    assert verdict.MINIMUM in str(failure.value)


def test_a_failing_script_is_an_error_carrying_its_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    scripts = package(tmp_path, "claude")
    (scripts / "fail").touch()
    with pytest.raises(verdict.ComputationError) as failure:
        verdict.computed_verdict("claude", [], tmp_path)
    assert "exited 3" in str(failure.value) and "boom" in str(failure.value)


def test_a_rendering_without_a_verdict_line_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package(tmp_path, "claude", "no verdict here\n")
    with pytest.raises(verdict.ComputationError) as failure:
        verdict.computed_verdict("claude", [], tmp_path)
    assert verdict.MINIMUM in str(failure.value)


def run(
    tmp_path: Path,
    cli: str,
    text: str,
    fail_on: str,
    rendering: str | None = None,
    prompt: str = "",
) -> tuple[int, str, dict]:
    """verdict.py as the step runs it: HOME carries the package's script
    (printing `rendering`; none when `rendering` is None), the checkout
    is `tmp_path / "checkout"`."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    if rendering is not None:
        package(home, cli, rendering)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
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
            "--checkout",
            str(checkout),
            "--prompt",
            prompt,
            "--fail-on",
            fail_on,
            "--outputs",
            str(outputs),
            "--summary",
            str(summary),
        ],
        env={**os.environ, "HOME": str(home)},
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
    code, out, outputs = run(
        tmp_path, "opencode", opencode_stream(ANSWER), "warning", RENDERED_WARNING
    )
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
    rc, _out, _outputs = run(
        tmp_path, "copilot", copilot_stream(ANSWER), fail_on, RENDERED_WARNING
    )
    assert rc == code


ERROR_ANSWER = "- verdict: error - a verification failed\n- todo: nothing to do\n"


@pytest.mark.parametrize("fail_on,code", [("error", 1), ("warning", 1), ("none", 0)])
@pytest.mark.parametrize("answer", [ERROR_ANSWER, NO_VERDICT_LINE])
def test_a_recomputed_error_gates_whatever_the_answer_said(
    tmp_path, answer, fail_on, code
):
    rc, _out, outputs = run(
        tmp_path, "copilot", copilot_stream(answer), fail_on, RENDERING
    )
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


@pytest.mark.parametrize(
    "flags,why",
    [
        ('["--repo", "/tmp/x"]', "flag '--repo'"),
        (
            '["--service", "none"]',
            "--service none names a scope the prompt does not name",
        ),
        # a word of the prompt that names no service: matched 0, refused
        (
            '["--service", "the"]',
            "the scope the run reported (--service the) matches no",
        ),
    ],
)
def test_a_flag_or_a_scope_the_action_refuses_fails_closed(tmp_path, flags, why):
    answer = (
        "- verdict: ok - x\n- todo: nothing to do\n"
        '```json\n{"summary": "fine", "flags": ' + flags + "}\n```\n"
    )
    home = tmp_path / "home"
    home.mkdir()
    scripts = package(home, "claude", RENDERED_WARNING)
    (scripts / "matched").write_text("0")
    code, out, outputs = run(
        tmp_path, "claude", claude_result(answer), "none", prompt="the checkout service"
    )
    assert code == 1
    assert outputs["status"] == "error"
    assert why in outputs["summary"]
    assert f"::error::the package's verdict could not be computed: {why}" in out
    # no divergence line on the failed path: there is no rendering
    assert "the package's rendering reads" not in out


def test_no_answer_fails_before_any_recomputation(tmp_path):
    code, out, outputs = run(
        tmp_path, "claude", claude_result("", error=True), "none", RENDERING
    )
    assert code == 1
    assert outputs["status"] == "error"
    assert "::error::the run produced no answer." in out
    scripts = tmp_path / "home" / verdict.SKILLS["claude"] / "get-status" / "scripts"
    assert not (scripts / "argv.json").exists()
