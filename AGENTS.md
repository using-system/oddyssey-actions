# AGENTS.md

## Working conventions

- Never commit on the default branch: branch first, named
  `type/short-description` (`feat/setup-claude`, `fix/copilot-path`).
- Commit messages, PR titles and issue titles follow
  [Conventional Commits](https://www.conventionalcommits.org/):
  `type(scope): lowercase imperative description`. The scope is the
  action's name (`setup-copilot`) or `ci`, `docs`, `release`. The PR
  title becomes the squash commit and the release note, and drives the
  version (`feat:` minor, `fix:` and others patch). **Never add a `!`
  or a `BREAKING CHANGE` marker without discussing it first.**
- One logical change per PR. **Every PR references an existing issue**
  (`Closes #N`), here or in oddyssey when the work was specified there
  (`Closes using-system/oddyssey#N`); open the issue first when none
  exists. When the implementation deviates from what the issue
  specified, record each amended choice as a comment on that issue
  before opening the PR: the issue is the decision record.
- The full contributor workflow lives in
  [CONTRIBUTING.md](CONTRIBUTING.md); where this file and
  CONTRIBUTING.md speak of the same thing, they say the same thing.

## English only

Every committed artifact is written in English, whatever language the
conversation uses: YAML comments, docs, commit messages, PR and issue
text, labels, release notes. Translate user-provided content instead
of copying it verbatim.

## No secrets, anywhere

Never write a token, a credential or a real endpoint into anything
committed or published: an action, a workflow, a README, an issue, a PR.
An action names the variable the caller sets (`COPILOT_GITHUB_TOKEN`)
and never reads a secret itself. Placeholder values are obviously fake.

## What an action is here

- One directory per action at the repository root, `<name>/action.yml`
  and `<name>/README.md`, consumed as
  `using-system/oddyssey-actions/<name>@<ref>`.
- **One setup action per CLI** (`setup-copilot`; a `setup-claude` or a
  `setup-opencode` when a consumer needs it): the install, the auth,
  the model and where the package lands differ per CLI, so a shared
  input list would mean something else per value. Never one action
  with a `cli` input.
- A composite action, its steps in bash. An action installs and prints
  what it installed (the CLI version, the package version resolved,
  what was deployed) so the workflow log states what ran; it validates
  nothing beyond the CLI answering.
- The apm-cli pin an action installs the package with is oddyssey's
  (its `CONTRIBUTING.md`); bump it here when oddyssey bumps it, never
  ahead of it.
- Every `uses:` in an action or a workflow is pinned to a full commit
  SHA with the version in a trailing comment. An expression never goes
  into a `run:` block directly; it passes through `env:`.
- An action's README states its inputs, its outputs, the one-sentence
  token rule and one complete example workflow: checkout, the action,
  one launch step. The root README's catalog carries one row per
  action; both change in the same PR as the action.

## Run what CI runs before a PR

- actionlint on `.github/workflows/`, at the version the `ci`
  workflow pins:
  `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12 -color`
  It parses workflows only: the actions' bash steps go through
  `python3 scripts/shellcheck_actions.py` (shellcheck on PATH, or
  `--shellcheck <binary>`), the same pass CI runs.
- Each action's CI job runs the action for real on a bare checkout,
  latest and a pinned package version, and asserts what the runner
  carries afterwards. Its headless smoke step - the CLI running a
  packaged prompt - runs only when the repository carries that CLI's
  token secret; a PR touching an action is green when both pass.

A PR pushed red costs a review round-trip; run the checks first.

## Releases

Push a tag `vX.Y.Z`: the release workflow creates the GitHub release
with notes generated from the merged PR titles and moves the `vX`
floating major tag to it. Consumers pin `@vX`, an exact tag or a SHA.

## Title and label every issue

Issue titles follow the Conventional Commits form `type(scope): summary`
like commits and PR titles. Every issue carries a type label (`bug`,
`enhancement`, `documentation`), a `priority: low|medium|high` label,
and the label of the CLI it concerns (`copilot`, ...) when it concerns
one; `cicd` when it concerns this repository's own workflows. An issue
closed as not planned carries `wontfix` and a comment stating why.
