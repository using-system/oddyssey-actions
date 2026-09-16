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
A setup action reads no secret; the prompt-running action takes the
ambient `github.token`, or the token its `token` input names, and sets
it on the one step of the one CLI that needs it. Placeholder values are
obviously fake.

## What an action is here

- One directory per action at the repository root, `<name>/action.yml`
  and `<name>/README.md`, consumed as
  `using-system/oddyssey-actions/<name>@<ref>`.
- **One setup action per CLI** (`setup-copilot`, `setup-opencode`; a
  `setup-claude` when a consumer needs it): the install, the auth, the
  model and where the package lands differ per CLI, so a shared input
  list would mean something else per value. Never one action with a
  `cli` input. Every setup action exports `ODDYSSEY_CLI` and
  `ODDYSSEY_MODEL` (the model in that CLI's own form): the contract an
  action that runs a prompt reads to pick its launch line.
- **An action runs a prompt; a consumer never writes a headless line.**
  The README of a setup action shows the prompt-running action
  (`odd-status`) as the next step, never a hand-written `copilot -p` or
  `opencode run`; CI smokes a setup through that action too. The launch
  line per CLI lives in the prompt-running action, once, and reads
  `ODDYSSEY_CLI` and `ODDYSSEY_MODEL`.
- **A script an action ships carries its tests** under
  `<action>/tests/`, run by CI with pytest and linted with ruff at the
  versions the `ci` workflow pins; the action calls the script through
  `${{ github.action_path }}`, and the script's docstring states its
  whole flag surface.
- **A composite action is its `action.yml` as the wiring over
  `<action>/scripts/`.** Every step's logic is one script there, bash
  with `set -euo pipefail` (Python where the work is Python, run
  through `uv` at a pinned pyyaml), whose header states what it reads
  from its environment and what it writes (`GITHUB_OUTPUT`,
  `GITHUB_ENV`, `GITHUB_PATH`, the summary, a file); the step passes
  the inputs and the pins as `env:` and runs `"$SCRIPT"`, `SCRIPT`
  being `${{ github.action_path }}/scripts/<name>`. A `run:` block
  holds no logic: a script runs the same from a terminal, from a test
  and from the runner. An action installs and prints
  what it installed (the CLI version, the package version resolved,
  what was deployed) so the workflow log states what ran; it validates
  nothing beyond the CLI answering. The token is the launch step's:
  the prompt-running action sets it as `GITHUB_TOKEN` on its Copilot
  step and nowhere else - the workflow's own `github.token` by default,
  under `copilot-requests: write`, or the one its `token` input names
  (a user token when the run must be billed to a user); a setup action
  reads no token, and the opencode step receives none.
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
  `OPENCODE_VERSION` with its four `SHA256_*` (setup-opencode; opencode
  publishes no checksum file, compute them from the release's assets),
  `APM_CLI_VERSION` and `APM_CLI_PINNED_ON` (both setups; follow
  oddyssey's pin), `PYYAML_VERSION` (setup-opencode), `ACTIONLINT_VERSION`,
  `pyyaml==`, `pytest==` with its `--exclude-newer` date, and `ruff@`
  (ci), the
  `v1.12.0` matrix cell (ci; it is also a required check's name in the
  `main` ruleset - change both together, and a new job in `ci` is added
  to the ruleset's required checks when it lands), the versions
  CONTRIBUTING.md quotes.
- **No token reaches code the repository does not control.** A step
  that downloads or runs a third party's code carries no `GITHUB_TOKEN`
  unless that code provably needs one, and the PR says for what. A
  setup action never reads a caller's secret; the prompt-running action
  takes the ambient `github.token`, or the one its `token` input names,
  for the CLI that needs it, on that CLI's step only - the launch is
  one step per CLI so the other CLI's step never sees it - and fails
  when a `COPILOT_GITHUB_TOKEN` or `GH_TOKEN` in the environment would
  make the CLI prefer another token over the input.
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
  It parses workflows only: the actions' scripts go through
  `shellcheck --severity=style ./*/scripts/*.sh` (shellcheck on PATH; the
  actionlint image carries one: `docker run --rm -v "$PWD:/repo" -w /repo --entrypoint shellcheck rhysd/actionlint:1.7.12 --severity=style ./*/scripts/*.sh`),
  the same pass CI runs.
- The scripts the actions ship, with their tests:
  `uvx ruff@0.16.4 check ./*/scripts ./*/tests`, the same with
  `format --check`, and
  `uv run --no-project --exclude-newer 2026-09-16 --with pytest==9.0.2 pytest -v ./*/tests`.
- Each action's CI job runs the action for real on a bare checkout,
  latest and a pinned package version, and asserts what the runner
  carries afterwards, then runs the smoke - the `odd-status` action
  through that setup, on the workflow's own token or the repository's
  endpoint key; a PR touching an action is green when both pass.

A PR pushed red costs a review round-trip; run the checks first.

## Releases

Push a tag `vX.Y.Z`: the release workflow creates the GitHub release
with notes generated from the merged PR titles and moves the `vX`
floating major tag to it. Consumers pin `@vX`, an exact tag or a SHA.
The `/publish` command (`.claude/commands/publish.md`) drives it from
a Claude Code session: preflight on `main`, the bump picked from the
merged PR titles, the tag pushed on confirmation, the run watched to
completion, then each shipped issue labelled `release: vX.Y.Z`.

## Title and label every issue

Issue titles follow the Conventional Commits form `type(scope): summary`
like commits and PR titles. Every issue carries a type label (`bug`,
`enhancement`, `documentation`), a `priority: low|medium|high` label,
and the label of the CLI it concerns (`copilot`, ...) when it concerns
one; `cicd` when it concerns this repository's own workflows. An issue
closed as not planned carries `wontfix` and a comment stating why.
