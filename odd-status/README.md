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
| `prompt` | no | | What the status is about, in the caller's words: a service, a stack, a question (`the checkout service on prod`). Passed to the packaged command as its arguments, and the bound of the scope the verdict is recomputed with (name the service, the stack and the environment as the reports name them); empty for the whole loop; never starting with a dash. |
| `fail-on` | no | `none` | Fail the step when the status reaches this level: `warning` (warning or error fail), `error` (error fails), `none` (the outputs carry the verdict; the step still fails when the run produced no answer). |
| `token` | no | `${{ github.token }}` | The token the Copilot run authenticates with, set as `GITHUB_TOKEN` on the Copilot launch step and nowhere else; the opencode and Claude Code steps receive none from this action (the checkout's `persist-credentials: false` keeps the job token out of the checkout's `.git/config`, see "What this grants"). The workflow's own token by default, under the job permission `copilot-requests: write`; a user token (`${{ secrets.COPILOT_USER_TOKEN }}`) when the run must be billed to a user, readable by the model's shell as the Copilot bullet below says. Passed as given. |

## Outputs

| Output | What it is |
| --- | --- |
| `status` | The loop's verdict, `ok`, `warning` or `error`: the package's own, recomputed on the runner by its `get-status` script on the checkout, scoped as the `prompt` names (the verdict line its rendering opens with), never a line of the model's answer. `error` when the script cannot compute, and the step then fails whatever `fail-on` says. |
| `summary` | One sentence on that verdict, the model's. |
| `todo` | The next actions, most urgent first, as a JSON array of `{action, why}`: the todo line of that same rendering. |
| `report` | The run's whole answer, the status as the packaged command renders it. |

The intelligence is the package's, and the gate is bound to it:
`get-status` opens its rendering with `- verdict: <status> - <reasons>`
and `- todo: <the next actions>`, computed by its rules from every
stored report, ruling and ledger row. The model's part is the
one-sentence summary and the flags it ran the script with, in the JSON
block the action asks it to end with. The verdict step then runs the
script the setup deployed (`get-status/scripts/odd_status.py` under the
CLI's skills directory) again on the checkout, and `status` and `todo`
are that rendering's two lines - never a line of the model's answer.
What the run reports bounds the recomputation this far and no further:

- the scope (`--service`, `--stack`, `--env`, `--full`) is kept only
  where the `prompt` input names it - each value a whole word of the
  prompt, so name the service, the stack and the environment as the
  reports name them; an empty prompt is the whole loop and takes no
  scope. A scope the prompt does not name is refused, and so is a scope
  that matches no stored report (the package's own count): narrowed to
  nothing, a status reads `warning` whatever the loop holds, and a gate
  that saw no report has gated nothing - whether the run was steered or
  the prompt names the service otherwise than the reports do;
- the run's rulings (`--ruled`, `--runtime`, `--non-runtime`) are its
  own judgment and are dropped: the gate reads the package's rules over
  the committed memory alone, and the log and the run's summary say how
  many rulings were dropped. A ruling that should hold is persisted in
  `.odd/decisions.md` or `.odd/entry-classifications.md` - reviewed,
  committed - and the script reads it on every run; the model's one-run
  rulings stay visible in its report;
- anything else is refused: `--repository` (no other clone is on the
  runner), a path, a date, a rendering switch.

So whoever can put text in front of the model - a report under `.odd/`,
an instruction file - cannot print the verdict, narrow the status to a
scope the caller did not ask for, or rule a regression away; what the
run passed is in the log and the summary (`recomputed with ...`), and
when the answer's own verdict line differs from the recomputed one, both
say so. That binding holds against text: the run also has a shell, as
"What this grants" says, and a run that edits `.odd/` or the package's
directory edits what the recomputation reads. The run's summary carries
the verdict, the todo as a table, the report and the package's
rendering. A refused flag, a script that is not found (the setup deploys
it from [`ODDYSSEY_MINIMUM_VERSION`](../ODDYSSEY_MINIMUM_VERSION) on) or
a script that fails is an `error` whose summary says why, and the step
fails whatever `fail-on` says, as a run with no answer does.

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
  built-in GitHub MCP server, and keeps the token out of the
  environment of the shells and MCP servers the run opens and out of
  the output (`--secret-env-vars GITHUB_TOKEN`, as the CLI's help
  states it). That flag is a filter, not a boundary: the CLI process
  itself holds the token, and a shell running as the runner's user can
  read a process's environment (`/proc/<pid>/environ` on Linux), so
  the model's shell can reach it the way it can reach opencode's key
  file and Claude Code's credential file. A user token passed as
  `token` is exposed the same way: scope it to Copilot requests alone
  and keep it short-lived. What the CLI accepts is GitHub's: its Actions
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
        with:
          persist-credentials: false
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
`copilot-requests` permission: those steps receive no token from this
action. To bill the Copilot run to a user, add
`token: ${{ secrets.COPILOT_USER_TOKEN }}` under `with:`.

## What this grants

The run is the setup's launch line: the model runs any shell command the
runner allows, reads and writes the checkout and the package's
directory, and reaches the network. The checkout is part of that: with
`actions/checkout` at its defaults the job token is persisted in the
checkout's `.git/config`, readable by the model's shell on every CLI,
which is why the examples set `persist-credentials: false` - nothing
in these actions uses git with the token. Keep the job at
`contents: read` (plus `copilot-requests: write` for Copilot), never
put the step on a trigger that carries untrusted input
(`issue_comment`, `pull_request_target`, a fork's `pull_request`), and
mind a same-repository `pull_request` too: its author writes the
checkout's `.odd/`, which the run reads on every CLI, and the
instruction files opencode and Claude Code read. Treat the outputs as
the model's text before a later step
acts on them - a `todo` is a list to read, not a command to run.

## Pinning

`@v1` follows the latest release of this major; a commit SHA freezes
the action; an exact tag is never deleted or rewound (the repository's
`v*` tag ruleset blocks both, for admins too), though a writer can
still move it forward along `main`.
