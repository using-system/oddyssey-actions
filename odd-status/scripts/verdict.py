"""Turn a headless run's event stream into the odd-status verdict.

    verdict.py --cli copilot|opencode|claude --events <run.jsonl> --fail-on none|warning|error \
        [--outputs <GITHUB_OUTPUT>] [--summary <GITHUB_STEP_SUMMARY>]

Reads the CLI's JSON output, takes the run's final answer (copilot: the
last `assistant.message` with content; opencode: the text parts of the
last message; claude: the `result` of the one result object), and reads
the verdict from it. The status and the todo are the
`- verdict: <status> - <reasons>` and `- todo: <items>` lines the
package's status rendering opens with - computed by its get-status
rules, printed unchanged by the run; the summary is the one sentence of
the fenced ```json block the prompt asked for, {"summary": str}. An
answer with no verdict line is an `error` verdict whose summary names
the oddyssey version needed at minimum (ODDYSSEY_MINIMUM_VERSION at the
repository root), or says the run produced no answer. Writes `status`,
`summary`, `todo` (a JSON array) and `report` (the whole answer) as step
outputs, the verdict and the report to the step summary, prints the
verdict line, and exits 1 when the status reaches the --fail-on level,
0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

LEVELS = {"ok": 0, "warning": 1, "error": 2}
MINIMUM = (
    (Path(__file__).resolve().parents[2] / "ODDYSSEY_MINIMUM_VERSION")
    .read_text()
    .strip()
)
FENCE = re.compile(r"```json\s*\r?\n(.*?)\r?\n\s*```", re.DOTALL | re.IGNORECASE)
# The rendering's two lines, as get-status prints them (`- verdict:
# <status> - <reasons>`, `- todo: <item> · <item>` or `nothing to do`)
# and as a model may dress them up: bold markers, backticks, an en or
# em dash.
_LINE = r"^\s*[-*]?\s*\**\s*{key}\s*:?\**\s*:?\s*(?P<rest>.*?)\**\s*$"
VERDICT_LINE = re.compile(_LINE.format(key="verdict"), re.IGNORECASE | re.MULTILINE)
TODO_LINE = re.compile(_LINE.format(key="todo"), re.IGNORECASE | re.MULTILINE)
DASH = re.compile(r"\s+[-–—]\s+")


def events(path: Path) -> list[dict]:
    return events_from_text(path.read_text(errors="replace"))


def events_from_text(text: str) -> list[dict]:
    # one JSON document over several lines (claude's result object) is
    # one event; otherwise one event per line
    try:
        whole = json.loads(text)
    except json.JSONDecodeError:
        whole = None
    if isinstance(whole, dict):
        return [whole]
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            out.append(event)
    return out


def final_answer(cli: str, stream: list[dict]) -> str:
    """The run's final answer, as the CLI streams it."""
    if cli == "copilot":
        answer = ""
        for event in stream:
            data = event.get("data") or {}
            content = (
                data.get("content")
                if event.get("type") == "assistant.message"
                else None
            )
            if isinstance(content, str) and content:
                answer = content
        return answer
    if cli == "claude":
        # claude: one result object (--output-format json), its `result`
        # the final text; an error result carries no answer.
        for event in stream:
            if event.get("type") == "result" and not event.get("is_error"):
                result = event.get("result")
                return result if isinstance(result, str) else ""
        return ""
    # opencode: the text parts of the last message that carried any
    last_message, parts = None, []
    for event in stream:
        part = event.get("part") or {}
        if (
            event.get("type") != "text"
            or not isinstance(part.get("text"), str)
            or not part["text"]
        ):
            continue
        if part.get("messageID") != last_message:
            last_message, parts = part.get("messageID"), []
        parts.append(part["text"])
    return "".join(parts)


def flat(text: str) -> str:
    """One line: the model's text reaches stdout, a table cell and an
    output, where a newline is a workflow command or a row break."""
    return " ".join(text.split())


def rendered_verdict(answer: str) -> dict | None:
    """The status and the todo the package's rendering opens with, or None
    when the answer carries no verdict line. The first verdict line is the
    rendering's: a model restating one at the end never overrides it."""
    status = None
    for match in VERDICT_LINE.finditer(answer):
        rest = match.group("rest").strip("*` ").lower()
        head = re.split(r"[\s*:`]", rest, maxsplit=1)[0]
        if head in LEVELS:
            status = head
            break
    if status is None:
        return None
    todo = []
    match = TODO_LINE.search(answer, match.end())
    rest = flat(match.group("rest").strip("*` ")).rstrip(".") if match else ""
    if rest and rest.lower() != "nothing to do":
        for item in rest.split(" · "):
            # `lineage: action - evidence`: the dash splits the action
            # from its evidence; an item with no dash is all action.
            parts = DASH.split(item.strip("` "), maxsplit=1)
            action = parts[0].strip()
            if action:
                todo.append(
                    {
                        "action": action,
                        "why": parts[1].strip() if len(parts) > 1 else "",
                    }
                )
    return {"status": status, "todo": todo}


def parse_block(answer: str) -> str:
    """The model's summary, from the last fenced json block that carries
    one; empty when none does."""
    for block in reversed(FENCE.findall(answer)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("summary"), str):
            summary = flat(data["summary"])
            if summary:
                return summary
    return ""


def parse_verdict(answer: str) -> dict:
    """The verdict: the rendering's status and todo, the block's summary;
    an `error` that says why when the answer carries no verdict line."""
    rendered = rendered_verdict(answer)
    if rendered is None:
        summary = (
            f"no verdict line in the rendering: oddyssey {MINIMUM} or newer is needed"
            if answer.strip()
            else "the run produced no answer"
        )
        return {"status": "error", "summary": summary, "todo": []}
    return {**rendered, "summary": parse_block(answer) or "the run wrote no summary"}


def write_outputs(path: Path, verdict: dict, report: str) -> None:
    with path.open("a") as handle:
        for key, value in (
            ("status", verdict["status"]),
            ("summary", verdict["summary"]),
            ("todo", json.dumps(verdict["todo"], ensure_ascii=False)),
            ("report", report),
        ):
            delimiter = f"ODD_{uuid.uuid4().hex}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def write_summary(path: Path, verdict: dict, report: str) -> None:
    icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[verdict["status"]]
    lines = [f"### odd-status: {icon} {verdict['status']}", "", verdict["summary"], ""]
    if verdict["todo"]:
        lines.append("| # | Action | Why |")
        lines.append("| --- | --- | --- |")
        for i, item in enumerate(verdict["todo"], 1):
            action = item["action"].replace("|", "\\|")
            why = item["why"].replace("|", "\\|")
            lines.append(f"| {i} | {action} | {why} |")
        lines.append("")
    if report:
        lines += [
            "<details><summary>The run's report</summary>",
            "",
            report,
            "",
            "</details>",
            "",
        ]
    with path.open("a") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cli", required=True, choices=("copilot", "opencode", "claude")
    )
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument(
        "--fail-on", required=True, choices=("none", "warning", "error")
    )
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    report = final_answer(args.cli, events(args.events)).strip()
    verdict = parse_verdict(report)
    if args.outputs:
        write_outputs(args.outputs, verdict, report)
    if args.summary:
        write_summary(args.summary, verdict, report)
    print(
        f"odd-status: {verdict['status']} - {verdict['summary']} ({len(verdict['todo'])} todo)"
    )
    if not report:
        print("::error::the run produced no answer.")
        return 1
    if args.fail_on != "none" and LEVELS[verdict["status"]] >= LEVELS[args.fail_on]:
        print(
            f"::error::odd-status is {verdict['status']} and fail-on is {args.fail_on}."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
