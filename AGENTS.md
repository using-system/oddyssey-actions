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
  nothing beyond the CLI answering. The token is the launch step's:
  the workflow's own `GITHUB_TOKEN` under `copilot-requests: write`,
  or a user token in the CLI's variable; the action reads neither.
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

## Security

- **Every `uses:` is a full commit SHA** with the version in a trailing
  comment, in a workflow and in an action alike; the repository's
  Actions setting enforces it.
- **Anything fetched at run time is pinned and integrity-checked by the
  step itself.** No script is piped to a shell. A binary comes from a
  release's own assets at a pinned version and is verified against that
  release's checksums before extraction, failing closed when the
  checksums cannot be read. A Python tool names its exact version, and
  a `uvx` closure is bounded with `--exclude-newer` at the pin's date.
  A git ref a consumer may pass accepts a full commit SHA, and the
  README says a tag and `latest` resolve at run time.
- **A pin that lives in an `env:` or a `run:` string is invisible to
  Dependabot.** They are, and they are bumped by hand, each with its
  date or its checksums: `COPILOT_CLI_VERSION` (setup-copilot),
  `APM_CLI_VERSION` and `APM_CLI_PINNED_ON` (setup-copilot; follow
  oddyssey's pin), `ACTIONLINT_VERSION` and `pyyaml==` (ci), the
  `v1.12.0` matrix cell (ci; it is also a required check's name in the
  `main` ruleset - change both together), the versions CONTRIBUTING.md
  quotes.
- **No token reaches code the repository does not control.** A step
  that downloads or runs a third party's code carries no `GITHUB_TOKEN`
  unless that code provably needs one, and the PR says for what. An
  action never reads a caller's secret.
- **An expression never enters a `run:` block**; it passes through
  `env:`. Every input that reaches a shell, `$GITHUB_ENV` or
  `$GITHUB_OUTPUT` is validated against an explicit pattern first: a
  newline in an unvalidated value sets variables for every later step
  of the caller's job.
- **The headless run is scoped at its launch line**, in CI and in the
  README's example alike: `--allow-all-tools` is what non-interactive
  mode requires and it grants a shell; the rest is earned -
  `--add-dir <dir>` in place of `--allow-all-paths`,
  `--no-custom-instructions` unless the checkout's instructions are the
  thing under test, `--secret-env-vars` for every token in the
  environment, `--disable-builtin-mcps` unless a GitHub tool is needed,
  `--no-auto-update` so the version installed is the version that runs.
  A `--deny-url` is not a boundary when every tool is auto-approved.
- **A CI step that spends money or holds a token never runs on a
  fork's PR**: it is gated on the PR's head repository in the workflow,
  and the repository's fork-approval policy stays at all external
  contributors while such a step exists.
- **The release path publishes only what went through `main`**: the
  release workflow checks the tagged commit is an ancestor of `main`
  before it creates the release or moves the floating major tag, the
  floating tag is annotated, `contents: write` lives on that one job,
  and the `v*` tag ruleset blocks deleting or rewinding a release tag,
  for admins too: a floating tag only ever moves forward along `main`.
- **An action's README discloses what lands on the consumer's runner
  and with which credentials**: what is downloaded and from where, what
  is pinned and what resolves at run time, which token each step sees,
  and what the launch line's flags grant. A capability the README does
  not name is one the consumer did not agree to.
- **A security claim in a doc is verified against the code that makes
  it** - the flag's help, the release's assets, a run's events - or it
  is not written.
- **A vulnerability is reported privately** ([SECURITY.md](SECURITY.md));
  private vulnerability reporting stays enabled for that link to work.

## Run what CI runs before a PR

- actionlint on `.github/workflows/`, at the version the `ci`
  workflow pins:
  `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12 -color -ignore 'unknown permission scope "copilot-requests"'`
  (the ignore: actionlint 1.7.12 predates the `copilot-requests` scope)
  It parses workflows only: the actions' bash steps go through
  `uv run --no-project --with pyyaml==6.0.3 python scripts/shellcheck_actions.py`
  (shellcheck on PATH, or `--shellcheck <binary>`), the same pass CI
  runs.
- Each action's CI job runs the action for real on a bare checkout,
  latest and a pinned package version, and asserts what the runner
  carries afterwards, then runs the headless smoke - the CLI running a
  packaged prompt on the workflow's own token; a PR touching an action
  is green when both pass.

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
