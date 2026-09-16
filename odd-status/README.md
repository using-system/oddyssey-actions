# odd-status

Runs the packaged `/odd-status` through the CLI a setup action
installed, and turns its verdict into outputs a workflow can gate on:

```yaml
- uses: using-system/oddyssey-actions/setup-copilot@v1
- uses: using-system/oddyssey-actions/odd-status@v1
  env:
    GITHUB_TOKEN: ${{ github.token }}
  with:
    fail-on: error
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `prompt` | no | | What the status is about, in the caller's words: a service, a stack, a question (`the checkout service on prod`). Passed to the packaged command as its arguments; empty for the whole loop; never starting with a dash. |
| `fail-on` | no | `none` | Fail the step when the judged status reaches this level: `warning` (warning or error fail), `error` (error fails), `none` (the outputs carry the verdict; the step still fails when the run produced no answer). |

## Outputs

| Output | What it is |
| --- | --- |
| `status` | The model's judgement of the loop's state: `ok`, `warning` or `error`. |
| `summary` | One sentence on that judgement. |
| `todo` | The next actions, most urgent first, as a JSON array of `{action, why}`. |
| `report` | The run's whole answer, the status as the packaged command renders it. |

The run's summary carries the verdict, the todo as a table and the
report. The judgement is the model's: the action asks it to end its
answer with one JSON verdict - `error` when something demands a fix
before the next step, `warning` when something is due or degraded but
not blocking, `ok` when nothing is due - and parses that block. A
missing or malformed block is an `error` whose summary says so; a run
with no answer fails whatever `fail-on` says.

## Which CLI

The action reads `ODDYSSEY_CLI` and `ODDYSSEY_MODEL`, which every setup
action of this repository exports, and launches that CLI with the
packaged `odd-status` command on that model, scoped as the setup's README
documents:

- **Copilot** ([`setup-copilot`](../setup-copilot/README.md)): the
  step needs the workflow's token in its environment
  (`GITHUB_TOKEN: ${{ github.token }}`) under the job permission
  `copilot-requests: write`; the launch line grants a shell, file access
  to the skills only, no instructions from the checkout, no built-in
  GitHub MCP server, the token stripped from the shells the run opens.
- **opencode** ([`setup-opencode`](../setup-opencode/README.md)):
  nothing beyond the setup; the launch line auto-approves the tools
  (non-interactive mode requires it).

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
        env:
          GITHUB_TOKEN: ${{ github.token }}
        with:
          prompt: the checkout service
          fail-on: error
      - run: echo "$TODO"
        env:
          TODO: ${{ steps.status.outputs.todo }}
```

With opencode, replace the setup step by `setup-opencode` with its
`openai-api-key`, drop the `GITHUB_TOKEN` line and the
`copilot-requests` permission.

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
