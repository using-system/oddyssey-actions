"""Turn a headless run's event stream into the odd-status verdict.

    verdict.py --cli copilot|opencode|claude --events <run.jsonl> --fail-on none|warning|error \
        [--outputs <GITHUB_OUTPUT>] [--summary <GITHUB_STEP_SUMMARY>]

Reads the CLI's JSON output, takes the run's final answer (copilot: the
last `assistant.message` with content; opencode: the text parts of the
last message; claude: the `result` of the one result object), and reads
the verdict from it in two layers. The status and the todo are the
`- verdict: <status> - <reasons>` and `- todo: <items>` lines the
package's status rendering opens with - computed by its get-status
rules, printed unchanged by the run - and the model's part is the one
sentence of the fenced ```json block the prompt asked for:
{"status": "ok"|"warning"|"error", "summary": str,
"todo": [{"action": str, "why": str}, ...]}. When the rendering carries
no verdict line (a package that predates it), the block's status and
todo are the verdict, judged by the model; a missing or malformed block
then is an `error` verdict whose summary says so. Writes `status`,
`summary`, `todo` (a JSON array), `source` (`rendering` or `model`) and
`report` (the whole answer) as step outputs, the verdict and the report
to the step summary, prints the verdict line, and exits 1 when the status
reaches the --fail-on level, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

LEVELS = {"ok": 0, "warning": 1, "error": 2}
SOURCE_NOTE = {
    "rendering": "The status and the todo are the package's own verdict (the rendering's verdict and todo lines); the summary is the model's.",
    "model": "The rendering carries no verdict line (a package that predates it): the status and the todo are the model's judgement.",
}
FENCE = re.compile(r"```json\s*\r?\n(.*?)\r?\n\s*```", re.DOTALL | re.IGNORECASE)
# The rendering's two lines, as get-status prints them (`- verdict:
# <status> - <reasons>`, `- todo: <item> · <item>` or `nothing to do`)
# and as a model may dress them up: bold markers, an en or em dash.
_LINE = r"^\s*[-*]?\s*\**\s*{key}\s*:?\**\s*:?\s*(?P<rest>.*?)\**\s*$"
VERDICT_LINE = re.compile(_LINE.format(key="verdict"), re.IGNORECASE | re.MULTILINE)
TODO_LINE = re.compile(_LINE.format(key="todo"), re.IGNORECASE | re.MULTILINE)
DASH = re.compile(r"\s+[-\u2013\u2014]\s+")


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
    when the answer carries no verdict line (a package that predates it)."""
    status = None
    for match in VERDICT_LINE.finditer(answer):
        rest = match.group("rest").strip("* ").lower()
        head = re.split(r"[\s*:]", rest, maxsplit=1)[0]
        if head in LEVELS:
            status = head
    if status is None:
        return None
    todo = []
    for match in TODO_LINE.finditer(answer):
        rest = flat(match.group("rest").strip("* "))
        todo = []
        if rest and rest.lower() != "nothing to do":
            for item in rest.split(" \u00b7 "):
                # `lineage: action - evidence`: the dash splits the action
                # from its evidence; an item with no dash is all action.
                parts = DASH.split(item, maxsplit=1)
                action = parts[0].strip()
                if action:
                    todo.append(
                        {
                            "action": action,
                            "why": parts[1].strip() if len(parts) > 1 else "",
                        }
                    )
    return {"status": status, "todo": todo}


def parse_block(answer: str) -> tuple[dict, bool]:
    """The verdict block of the answer, and whether it was well-formed."""
    blocks = FENCE.findall(answer)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("status") not in LEVELS:
            continue
        todo = data.get("todo")
        if not isinstance(todo, list):
            todo = []
        clean = []
        for item in todo:
            if isinstance(item, dict) and item.get("action"):
                clean.append(
                    {
                        "action": flat(str(item["action"])),
                        "why": flat(str(item.get("why", ""))),
                    }
                )
            elif isinstance(item, str) and item:
                clean.append({"action": flat(item), "why": ""})
        summary = data.get("summary")
        return {
            "status": data["status"],
            "summary": flat(str(summary)) if summary else "",
            "todo": clean,
        }, True
    return {
        "status": "error",
        "summary": "the run returned no verdict block (a fenced json block with status, summary and todo)",
        "todo": [],
    }, False


def parse_verdict(answer: str) -> tuple[dict, bool]:
    """The verdict: the rendering's status and todo with the block's summary
    when the rendering carries a verdict line, the block alone otherwise.
    Returns it with `source` set, and whether the block was well-formed."""
    block, well_formed = parse_block(answer)
    rendered = rendered_verdict(answer)
    if rendered is None:
        return {**block, "source": "model"}, well_formed
    summary = block["summary"] if well_formed else "the run wrote no summary"
    return {**rendered, "summary": summary, "source": "rendering"}, well_formed


def write_outputs(path: Path, verdict: dict, report: str) -> None:
    with path.open("a") as handle:
        for key, value in (
            ("status", verdict["status"]),
            ("summary", verdict["summary"]),
            ("todo", json.dumps(verdict["todo"], ensure_ascii=False)),
            ("source", verdict["source"]),
            ("report", report),
        ):
            delimiter = f"ODD_{uuid.uuid4().hex}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def write_summary(path: Path, verdict: dict, report: str) -> None:
    icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[verdict["status"]]
    lines = [f"### odd-status: {icon} {verdict['status']}", ""]
    if verdict["summary"]:
        lines += [verdict["summary"], ""]
    lines += [SOURCE_NOTE[verdict["source"]], ""]
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
    verdict, well_formed = parse_verdict(report)
    if args.outputs:
        write_outputs(args.outputs, verdict, report)
    if args.summary:
        write_summary(args.summary, verdict, report)
    print(
        f"odd-status: {verdict['status']} - {verdict['summary'] or 'no summary'}"
        f" ({len(verdict['todo'])} todo, verdict from the {verdict['source']},"
        f" summary block {'found' if well_formed else 'missing'})"
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
