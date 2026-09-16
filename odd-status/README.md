# odd-status

Runs the packaged `/odd-status` through the CLI a setup action
installed, and turns its verdict into outputs a workflow can gate on:

```yaml
- uses: using-system/oddyssey-actions/setup-copilot@v1
- uses: using-system/oddyssey-actions/odd-status@v1
  with:
    fail-on: error
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `prompt` | no | | What the status is about, in the caller's words: a service, a stack, a question (`the checkout service on prod`). Passed to the packaged command as its arguments; empty for the whole loop; never starting with a dash. |
| `fail-on` | no | `none` | Fail the step when the judged status reaches this level: `warning` (warning or error fail), `error` (error fails), `none` (the outputs carry the verdict; the step still fails when the run produced no answer). |
| `token` | no | `${{ github.token }}` | The token the Copilot run authenticates with, set as `GITHUB_TOKEN` on the Copilot launch step and nowhere else; the opencode and Claude Code runs never receive it. The workflow's own token by default, under the job permission `copilot-requests: write`; a user token (`${{ secrets.COPILOT_USER_TOKEN }}`) when the run must be billed to a user. Passed as given. |

## Outputs

| Output | What it is |
| --- | --- |
| `status` | The model's judgement of the loop's state: `ok`, `warning` or `error`. |
| `summary` | One sentence on that judgement. |
| `todo` | The next actions, most urgent first, as a JSON array of `{action, why}`. |
| `report` | The run's whole answer, the status as the packaged command renders it. |

The run's summary carries the verdict, the todo as a table and the
report. The judgement is the model's, anchored on the loop's own rule:
the action asks it to end its answer with one JSON verdict whose status
follows the **Action** column of the loop state table - `ok` when every
lineage's action is `loop can rest` (or `plan verified`) and the
`Regr.` column is 0, `warning` when a lineage's action is
`verification due`, `observation overdue`, `fix pending` or `plan
awaits verification`, when there is no loop state table at all (the
loop has not started, or nothing matches the prompt), or when a
"Judgment needed" item - or a `judgment needed` lineage - is one the
maintainer can settle with a command, `error` when a verification
failed, a finding regressed, a report could not be read or the memory
invariant reports a violation (a report failing the contract; a skipped ledger row,
including one naming an entry that no longer exists, is a fact it
reports, never a violation) - and parses that block. Telemetry gaps,
declined findings, "Judgment needed" items (or lineages) the rules
cannot settle from the memory, and the decisions a report leaves to
the spec are facts the summary names and the todo may list; they never
set the status. A missing or
malformed block is an `error` whose summary says so; a run with no
answer fails whatever `fail-on` says.

## Which CLI

The action reads `ODDYSSEY_CLI` and `ODDYSSEY_MODEL`, which every setup
action of this repository exports, and launches that CLI with the
packaged `odd-status` command on that model, scoped as the setup's README
documents:

- **Copilot** ([`setup-copilot`](../setup-copilot/README.md)): the
  action sets the `token` input as `GITHUB_TOKEN` on its Copilot launch
  step, and only there; the job grants `copilot-requests: write` for
  the default, the workflow's own token, and that permission is the
  only thing the caller sets. The launch line grants a shell, file
  access to the skills only, no instructions from the checkout, no
  built-in GitHub MCP server, the token stripped from the shells the
  run opens. What the CLI accepts is GitHub's: its Actions
  documentation names the workflow's `GITHUB_TOKEN` under
  `copilot-requests: write`, and the CLI's own help says only that the
  variable holds "an authentication token"; the action passes the
  input as given and checks nothing about it. A GitHub App
  installation token is not documented as carrying a Copilot
  entitlement and was not tried. The CLI reads
  `COPILOT_GITHUB_TOKEN`, then `GH_TOKEN`, then
  `GITHUB_TOKEN` (its `copilot help environment`), so either of the
  first two in the step's environment would replace the input: the
  step fails when it finds one and names the `token` input instead.
- **opencode** ([`setup-opencode`](../setup-opencode/README.md)):
  nothing beyond the setup; the launch line auto-approves the tools
  (non-interactive mode requires it), and the checkout's instruction
  files (`AGENTS.md` and its kin) reach the run: opencode has no
  equivalent of `--no-custom-instructions`, so a branch writes part of
  the run's instructions - one more reason to keep the step off any
  trigger that carries untrusted input.
- **Claude Code** ([`setup-claude`](../setup-claude/README.md)):
  nothing beyond the setup; the launch step reads the credential file
  the setup kept into the CLI's own variable (`ANTHROPIC_API_KEY` or
  `CLAUDE_CODE_OAUTH_TOKEN`, by its kind) for that one process, and
  fails when either is already in its environment, since the CLI would
  prefer it. The launch line bypasses permissions (non-interactive mode
  requires it), loads the user-scope settings only (nothing from the
  checkout's `.claude/`), writes no session to disk and runs with the
  updater off; the checkout's `CLAUDE.md` still reaches the run.

Without a setup action earlier in the job, the step fails and says so.
The action needs `python3` on the runner's `PATH` (the ubuntu and macOS
runners carry one).

## Example workflow

A status gate on every push to `main`, on the cheapest model:

```yaml
name: odd-status

on:
  push:
    branches: [main]

permissions:
  contents: read
  copilot-requests: write

jobs:
  status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: using-system/oddyssey-actions/setup-copilot@v1
      - id: status
        uses: using-system/oddyssey-actions/odd-status@v1
        with:
          prompt: the checkout service
          fail-on: error
      - run: echo "$TODO"
        env:
          TODO: ${{ steps.status.outputs.todo }}
```

With opencode or Claude Code, replace the setup step by
`setup-opencode` with its `openai-api-key`, or `setup-claude` with its
`claude-oauth-token` or `anthropic-api-key`, and drop the
`copilot-requests` permission: those steps receive no token. To bill the Copilot run to a user,
add `token: ${{ secrets.COPILOT_USER_TOKEN }}` under `with:`.

## What this grants

The run is the setup's launch line: the model runs any shell command the
runner allows, reads and writes the checkout and the package's
directory, and reaches the network. Keep the job at `contents: read`
(plus `copilot-requests: write` for Copilot), never put the step on a
trigger that carries untrusted input (`issue_comment`,
`pull_request_target`, a fork's `pull_request`), and treat the outputs
as the model's text before a later step acts on them - a `todo` is a
list to read, not a command to run.

## Pinning

`@v1` follows the latest release of this major; an exact tag or a
commit SHA freezes the action.
