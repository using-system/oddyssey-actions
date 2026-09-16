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
| `<action>/action.yml`, `<action>/README.md` | One composite action per directory, consumed as `using-system/oddyssey-actions/<action>@<ref>`. |
| `.github/workflows/ci.yml` | actionlint on the workflows, shellcheck on the actions' bash steps, and one job per action that runs it for real on a bare checkout. |
| `.github/workflows/release.yml` | A `vX.Y.Z` tag creates the GitHub release and moves the `vX` floating major tag. |

## Building and testing

```bash
# The workflows, at the version CI pins (actionlint parses workflows only)
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12 -color -ignore 'unknown permission scope "copilot-requests"'

# The actions' bash steps, one shellcheck run per step (shellcheck on PATH,
# or --shellcheck <binary>; the actionlint image carries one)
python3 scripts/shellcheck_actions.py
```

An action's install steps are proven by its CI job on a real runner:
open the PR and read the job's log and summary, including the headless
smoke step (the CLI running a packaged prompt on the workflow's own
token).

## Pull requests

- **Every PR references an existing issue** (`Closes #N`, or
  `Closes using-system/oddyssey#N` when the work was specified there).
  The issue carries the problem and its discussion, the PR carries the
  change; open the issue first when none exists.
- **The issue is the decision record.** When the implementation
  deviates from what the issue specified, record each amended choice as
  a comment on that issue, what changed and why, before opening the PR.
- **The PR title IS the release note.** We squash-merge with the PR
  title as the commit message, and versions follow
  [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:` a minor, `fix:` and others a patch. Use
  `type(scope): lowercase imperative description`.
- **Never add a `!` or `BREAKING CHANGE` marker** without discussing it
  in the PR first: it means a major release, and consumers pinned on the
  floating major tag would not follow it.
- CI must be green: actionlint, the actions' shellcheck, and the
  action's job on a bare checkout.
- Every `uses:` pinned to a full commit SHA with the version in a
  trailing comment; no `${{ }}` inside a `run:` block.
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
