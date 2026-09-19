# Contributing to oddyssey-actions

Thanks for helping oddyssey run on GitHub Actions. Issues, docs fixes and
actions are all welcome.

## Contributing with a coding agent

This repository is built for coding agents, and contributing through
one is the expected path. Agents read [AGENTS.md](AGENTS.md): the
working conventions, what an action is here, the checks to run before a
PR, the English-only and no-secrets rules. Point your agent at the repo
root so it picks the file up, and review what it produced before
pushing: **you remain responsible for everything your agent commits,
opens, or comments under your name.**

## The two-minute orientation

| Where | What |
| --- | --- |
| `<action>/action.yml`, `<action>/README.md` | One composite action per directory, consumed as `using-system/oddyssey-actions/<action>@<ref>`; the `action.yml` is the wiring, every step's logic is a script under `<action>/scripts/` (the one resolve step every setup shares and the one launch line per CLI every prompt-running action shares live at `scripts/`, behind a `resolve.sh` in each setup and a `run-<cli>.sh` in each prompt-running action). |
| `tests/<action>/` | Every action's tests, one tree: pytest runs each script of the checkout's action with fake tools on `PATH`; `test_runner.py`, marked `runner`, checks what the runner carries after the real action ran in CI. |
| `.github/workflows/ci.yml` | `lint` (actionlint on the workflows, shellcheck on the actions' scripts and the shared scripts at the root, ruff) and `tests`, one matrix cell per action: its tests off the runner, the action for real on a bare checkout, its `runner` tests. |
| `.github/workflows/release.yml` | A `vX.Y.Z` tag creates the GitHub release and moves the `vX` floating major tag. |

## Building and testing

```bash
# The workflows, at the version CI pins (actionlint parses workflows only)
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12 -color -ignore 'unknown permission scope "copilot-requests"'

# The actions' scripts and the shared scripts at the root (shellcheck on PATH; the actionlint
# image carries one: docker run --rm -v "$PWD:/repo" -w /repo --entrypoint shellcheck rhysd/actionlint:1.7.12 ...)
shellcheck --severity=style ./scripts/*.sh ./*/scripts/*.sh

# The actions' tests, off the runner (the `runner` tests are deselected)
uvx ruff@0.16.4 check ./*/scripts ./tests
uvx ruff@0.16.4 format --check ./*/scripts ./tests
uv run --no-project --exclude-newer 2026-09-16 --with pytest==9.0.2 --with pyyaml==6.0.3 pytest -v ./tests
```

An action's install is proven by its cells of the `tests` job on a
real runner: the action, then `pytest -m runner ./tests/<action>` on
what it left there; `odd-status`'s cells run it through each setup and
test its verdict. Open the PR and read the cell's log and summary.

## Pull requests

- **Every PR references an existing issue** (`Closes #N`, or
  `Closes using-system/oddyssey#N` when the work was specified there).
  The issue carries the problem and its discussion, the PR carries the
  change; open the issue first when none exists.
- **The issue is the decision record.** When the implementation
  deviates from what the issue specified, record each amended choice as
  a comment on that issue, what changed and why, before opening the PR.
- **The change is reviewed before the PR opens**, by a reader that did
  not write it: a coding agent dispatches one review subagent on the
  branch's diff against `main`, with the issue as the spec and AGENTS.md
  with this file as the standard, and fixes what it finds (critical
  and important findings fixed, minor ones fixed or named in the PR).
  Every fix goes back to the reviewer, until a review comes back green
  - nothing critical, nothing important: the push happens on a green
  review, never on a fixed one.
- **The PR title IS the release note.** We squash-merge with the PR
  title as the commit message, and versions follow
  [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:` a minor, `fix:` and others a patch. Use
  `type(scope): lowercase imperative description`.
- **Never add a `!` or `BREAKING CHANGE` marker** without discussing it
  in the PR first: it means a major release, and consumers pinned on the
  floating major tag would not follow it.
- CI must be green: `lint`, and every cell of `tests`.
- Every `uses:` pinned to a full commit SHA with the version in a
  trailing comment; no `${{ }}` inside a `run:` block; the rest of the
  security rules are AGENTS.md's "Security" section.
- One logical change per PR; an action's README and the root catalog
  change in the same PR as the action.

## Issues

Use the issue forms (bug / feature). Questions belong in the
[oddyssey Discussions](https://github.com/using-system/oddyssey/discussions).

## Security

Vulnerabilities go through
[private reporting](https://github.com/using-system/oddyssey-actions/security/advisories/new),
never a public issue; scope and expectations are in
[SECURITY.md](SECURITY.md).
