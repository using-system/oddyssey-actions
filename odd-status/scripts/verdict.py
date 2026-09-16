"""Turn a headless run's event stream into the odd-status verdict.

    verdict.py --cli copilot|opencode --events <run.jsonl> --fail-on none|warning|error \
        [--outputs <GITHUB_OUTPUT>] [--summary <GITHUB_STEP_SUMMARY>]

Reads the CLI's JSON event stream, takes the run's final answer (copilot:
the last `assistant.message` with content; opencode: the text parts of
the last message), and extracts the one fenced ```json block the prompt
asked for: {"status": "ok"|"warning"|"error", "summary": str,
"todo": [{"action": str, "why": str}, ...]}. A missing or malformed block
is an `error` verdict whose summary says so. Writes `status`, `summary`,
`todo` (a JSON array) and `report` (the whole answer) as step outputs, the
verdict and the report to the step summary, prints the verdict line, and
exits 1 when the status reaches the --fail-on level, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

LEVELS = {"ok": 0, "warning": 1, "error": 2}
FENCE = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)


def events(path: Path) -> list[dict]:
    return events_from_text(path.read_text(errors="replace"))


def events_from_text(text: str) -> list[dict]:
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
            if event.get("type") == "assistant.message" and data.get("content"):
                answer = data["content"]
        return answer
    # opencode: the text parts of the last message that carried any
    last_message, parts = None, []
    for event in stream:
        part = event.get("part") or {}
        if event.get("type") != "text" or not part.get("text"):
            continue
        if part.get("messageID") != last_message:
            last_message, parts = part.get("messageID"), []
        parts.append(part["text"])
    return "".join(parts)


def parse_verdict(answer: str) -> tuple[dict, bool]:
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
                    {"action": str(item["action"]), "why": str(item.get("why", ""))}
                )
            elif isinstance(item, str) and item:
                clean.append({"action": item, "why": ""})
        summary = data.get("summary")
        return {
            "status": data["status"],
            "summary": str(summary) if summary else "",
            "todo": clean,
        }, True
    return {
        "status": "error",
        "summary": "the run returned no verdict block (a fenced json block with status, summary and todo)",
        "todo": [],
    }, False


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
    lines = [f"### odd-status: {icon} {verdict['status']}", ""]
    if verdict["summary"]:
        lines += [verdict["summary"], ""]
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
    parser.add_argument("--cli", required=True, choices=("copilot", "opencode"))
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
        f" ({len(verdict['todo'])} todo, verdict block {'found' if well_formed else 'missing'})"
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
