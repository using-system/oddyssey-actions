"""Turn a headless run's event stream into the odd-status verdict.

    verdict.py --cli copilot|opencode|claude --events <run.jsonl> --checkout <dir> \
        --fail-on none|warning|error [--prompt <text>] [--outputs <GITHUB_OUTPUT>] \
        [--summary <GITHUB_STEP_SUMMARY>]

Reads the CLI's JSON output, takes the run's final answer (copilot: the
last `assistant.message` with content; opencode: the text parts of the
last message; claude: the `result` of the one result object), and reads
the fenced ```json block the prompt asked for from it: {"summary": str,
"flags": [str]} - the model's one sentence, and the flags of the run's
last `odd_status.py --render` (the caller's scope, the run's rulings).
The status and the todo are then the package's own: the script the
CLI's setup deployed (get-status's odd_status.py, under that CLI's
skills directory in the runner's home) is run again on the checkout
with the run's scope flags - `--service`, `--stack`, `--env`, each value
a word of the caller's --prompt, and `--full`; none with an empty
prompt; a scope matching no stored report is refused - and the
`- verdict: <status> - <reasons>` and `- todo: <items>` lines its
rendering opens with are the verdict - never a line of the answer,
whoever wrote it. The run's ruling flags (`--ruled`,
`--runtime`, `--non-runtime`) are its own judgment and are dropped from
the recomputation, and the log says how many. Any other flag, a scope
the prompt does not name, a script that is not found, one that fails or
renders no verdict line is an `error` verdict whose summary says why
(naming the oddyssey version needed at minimum,
ODDYSSEY_MINIMUM_VERSION at the repository root, when the package may be
older), and the step then fails whatever --fail-on says. A run with no
answer is an `error` too. Writes `status`,
`summary`, `todo` (a JSON array) and `report` (the whole answer) as step
outputs, the verdict, the report and the package's rendering to the step
summary, prints the verdict line - and, when the answer's own verdict
line disagrees with the rendering's, says so - and exits 1 when the
status reaches the --fail-on level, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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
# Where each CLI's setup deploys the package's skills, under the runner's
# home (setup-<cli>/scripts/install-package.sh); get-status's script is
# under its skill.
SKILLS = {
    "copilot": ".agents/skills",
    "opencode": ".config/opencode/skills",
    "claude": ".claude/skills",
}
STATUS_SCRIPT = Path("get-status") / "scripts" / "odd_status.py"
# The flags a run may hand back: the script's scope flags, each with one
# value the caller's prompt names, and its ruling flags, dropped from the
# recomputation - never a path, a date or a rendering switch, which would
# move the computation off the checkout.
SCOPE_FLAGS = {"--service", "--stack", "--env"}
RULING_FLAGS = {"--ruled", "--runtime", "--non-runtime"}
FLAGS_WITH_VALUE = SCOPE_FLAGS | RULING_FLAGS
FLAGS_ALONE = {"--full"}
VALUE = re.compile(r"^[^\s-][^\s]*$")
# A scope value the prompt names: the value as a whole word of it
# (`checkout` in "the checkout service on prod", not in "checkout-svc").
NAMED_BY = r"(?<![A-Za-z0-9_-]){value}(?![A-Za-z0-9_-])"
SCRIPT_TIMEOUT = 120
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


def parse_block(answer: str) -> dict:
    """The model's summary and the run's flags, from the last fenced json
    object in the answer that carries either: an empty summary when it
    carries none, no flags when it names none. The flags are handed back
    as written, for validate_flags."""
    for block in reversed(FENCE.findall(answer)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        summary = data.get("summary")
        if isinstance(summary, str) or "flags" in data:
            return {
                "summary": flat(summary) if isinstance(summary, str) else "",
                "flags": data.get("flags", []),
            }
    return {"summary": "", "flags": []}


def normalized(flags) -> list[str]:
    """The flags one token each, as the script's parser sees them: a
    `--render` dropped (the action passes it), a `--x=v` or `--x v` inside
    one string split - so an honest run is not refused for its formatting.
    Whatever is not a list of strings is handed back for validate_flags to
    refuse."""
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        return flags
    out = []
    for flag in flags:
        for token in flag.split():
            if token == "--render":
                continue
            name, equals, value = token.partition("=")
            if equals and name in FLAGS_WITH_VALUE:
                out += [name, value]
            else:
                out.append(token)
    return out


def validate_flags(flags, prompt: str = "") -> dict:
    """The flags split into the scope the recomputation runs with and the
    rulings it drops, or a ValueError naming the first one the action
    refuses. A scope value must be named by the caller's prompt (a whole
    word of it, case-insensitive): the caller scoped the status, the run
    translated it; with no prompt there is no scope. A ruling is the
    run's own judgment and stays out of the gate."""
    flags = normalized(flags)
    if not isinstance(flags, list):
        raise ValueError("the block's flags are not a list")  # noqa: TRY004 - one error kind for the caller
    scope, rulings, pending = [], [], None
    for flag in flags:
        if not isinstance(flag, str):
            raise ValueError(f"flag {flag!r} is not a string")  # noqa: TRY004
        if pending:
            if not VALUE.match(flag):
                raise ValueError(f"{pending} takes one plain value, got {flag!r}")
            if pending in SCOPE_FLAGS:
                if not prompt.strip():
                    raise ValueError(
                        f"{pending} {flag} scopes a status the prompt did not scope"
                    )
                if not re.search(
                    NAMED_BY.format(value=re.escape(flag)), prompt, re.IGNORECASE
                ):
                    raise ValueError(
                        f"{pending} {flag} names a scope the prompt does not name"
                    )
                scope += [pending, flag]
            else:
                rulings += [pending, flag]
            pending = None
        elif flag in FLAGS_WITH_VALUE:
            pending = flag
        elif flag in FLAGS_ALONE:
            scope.append(flag)
        else:
            raise ValueError(f"flag {flag!r} is not one the action passes on")
    if pending:
        raise ValueError(f"{pending} takes a value")
    return {"scope": scope, "rulings": rulings}


class ComputationError(Exception):
    """The package's script could not compute the verdict; str(self) says why."""


def run_script(cli: str, args: list[str], checkout: Path) -> str:
    """The package's script run on the checkout, its stdout; a
    ComputationError when it is not there, does not finish, or fails.
    Its diagnostics go to stderr."""
    script = Path.home() / SKILLS[cli] / STATUS_SCRIPT
    if not script.is_file():
        raise ComputationError(
            f"the package's get-status script is not at {script}: "
            f"run a setup action earlier in the job, with oddyssey {MINIMUM} or newer"
        )
    what = f"odd_status.py {' '.join(args)}"
    try:
        run = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ComputationError(f"{what} did not finish in {SCRIPT_TIMEOUT}s") from None
    except OSError as why:
        raise ComputationError(f"{what} could not run: {why}") from None
    if run.stderr.strip():
        sys.stderr.write(run.stderr)
    if run.returncode != 0:
        tail = " ".join(run.stderr.split())[-300:]
        raise ComputationError(f"{what} exited {run.returncode}: {tail or 'no output'}")
    return run.stdout


def matched(cli: str, scope: list[str], checkout: Path) -> int:
    """How many stored reports the scope matches, from the script's fact
    sheet (its JSON output, `matched`; `--full` is the rendering's and
    the parser refuses it there)."""
    facts_scope = [flag for flag in scope if flag not in FLAGS_ALONE]
    try:
        facts = json.loads(run_script(cli, facts_scope, checkout))
        count = facts["matched"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise ComputationError(
            f"odd_status.py printed no fact sheet with a matched count: oddyssey "
            f"{MINIMUM} or newer is needed"
        ) from None
    if not isinstance(count, int):
        raise ComputationError("odd_status.py's matched count is not a number")
    return count


def computed_verdict(cli: str, scope: list[str], checkout: Path) -> dict:
    """The status and the todo as the package's own script renders them on
    the checkout with the scope, plus the rendering itself. A scope that
    matches no stored report is refused: narrowed to nothing, a status
    reads `warning` whatever the loop holds, and a gate that saw no report
    has gated nothing - whether the run was steered or the prompt names
    the service otherwise than the reports do."""
    if (
        any(flag in SCOPE_FLAGS for flag in scope)
        and matched(cli, scope, checkout) == 0
    ):
        raise ComputationError(
            f"the scope the run reported ({' '.join(scope)}) matches no stored "
            "report: name the service, the stack and the environment in the prompt "
            "as the reports name them"
        )
    rendering = run_script(cli, ["--render", *scope], checkout)
    rendered = rendered_verdict(rendering)
    if rendered is None:
        raise ComputationError(
            f"odd_status.py --render printed no verdict line: oddyssey {MINIMUM} "
            "or newer is needed"
        )
    return {**rendered, "rendering": rendering}


def parse_verdict(answer: str, cli: str, checkout: Path, prompt: str = "") -> dict:
    """The verdict: the package's status and todo, recomputed on the
    checkout with the scope the answer's block reports (bounded by the
    prompt; the run's rulings dropped); the block's summary; an `error`
    that says why when the run produced no answer, the flags are not the
    script's, or the script could not compute (`failed`: the step fails
    whatever fail-on says). For the record: `answered` is the status of
    the answer's own verdict line, or None; `scope` and `rulings` the
    flags kept and dropped."""
    answered = rendered_verdict(answer)
    answered = answered["status"] if answered else None
    record = {"answered": answered, "scope": [], "rulings": [], "rendering": ""}
    if not answer.strip():
        return {
            "status": "error",
            "summary": "the run produced no answer",
            "todo": [],
            **record,
        }
    block = parse_block(answer)
    try:
        flags = validate_flags(block["flags"], prompt)
        computed = computed_verdict(cli, flags["scope"], checkout)
    except (ValueError, ComputationError) as why:
        return {
            "status": "error",
            "summary": f"the package's verdict could not be computed: {why}",
            "todo": [],
            **record,
            "failed": True,
        }
    return {
        **record,
        **computed,
        "summary": block["summary"] or "the run wrote no summary",
        **flags,
    }


def recomputed_with(verdict: dict) -> str:
    """One line on the recomputation, for the log and the summary."""
    scope = " ".join(verdict["scope"]) if verdict["scope"] else "no scope"
    dropped = len(verdict["rulings"]) // 2
    line = f"recomputed with {scope}"
    if dropped:
        line += f"; {dropped} ruling(s) of the run dropped - the gate reads the package's rules alone"
    return line


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
    if not verdict.get("failed"):
        line = recomputed_with(verdict)
        lines += [line[0].upper() + line[1:] + ".", ""]
    if (
        verdict.get("answered")
        and verdict["answered"] != verdict["status"]
        and not verdict.get("failed")
    ):
        lines += [
            (
                f"The run's answer read `{verdict['answered']}`; the package's "
                f"rendering reads `{verdict['status']}` - the rendering is the verdict."
            ),
            "",
        ]
    for title, text in (
        ("The run's report", report),
        ("The package's rendering", verdict.get("rendering", "")),
    ):
        if text:
            lines += [
                f"<details><summary>{title}</summary>",
                "",
                text,
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
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--prompt", default="")
    parser.add_argument(
        "--fail-on", required=True, choices=("none", "warning", "error")
    )
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    report = final_answer(args.cli, events(args.events)).strip()
    verdict = parse_verdict(report, args.cli, args.checkout, args.prompt)
    if args.outputs:
        write_outputs(args.outputs, verdict, report)
    if args.summary:
        write_summary(args.summary, verdict, report)
    print(
        f"odd-status: {verdict['status']} - {verdict['summary']} ({len(verdict['todo'])} todo)"
    )
    if not verdict.get("failed"):
        print(recomputed_with(verdict))
    if (
        verdict["answered"]
        and verdict["answered"] != verdict["status"]
        and not verdict.get("failed")
    ):
        print(
            f"the run's answer read {verdict['answered']}; the package's rendering "
            f"reads {verdict['status']} - the rendering is the verdict."
        )
    if not report:
        print("::error::the run produced no answer.")
        return 1
    if verdict.get("failed"):
        # not a verdict of the loop but a failure of the action: the
        # step fails whatever fail-on says
        print(f"::error::{verdict['summary']}")
        return 1
    if args.fail_on != "none" and LEVELS[verdict["status"]] >= LEVELS[args.fail_on]:
        print(
            f"::error::odd-status is {verdict['status']} and fail-on is {args.fail_on}."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
