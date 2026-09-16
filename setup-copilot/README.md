# setup-copilot

Installs the GitHub Copilot CLI and the oddyssey package on the runner,
so a later step can run an oddyssey prompt headlessly:

```yaml
- uses: using-system/oddyssey-actions/setup-copilot@v1
  with:
    model: claude-sonnet-5
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `model` | yes | | The Copilot model the missions run on, as the CLI's model picker names it. Exported to the later steps as `COPILOT_MODEL`, which `--model` on the launch line overrides; never written to a config file. |
| `oddyssey-version` | no | `latest` | The oddyssey release to install: a release tag (`v1.12.1`) or `latest`, the newest release tag. |

## Outputs

| Output | What it is |
| --- | --- |
| `copilot-version` | The Copilot CLI version installed (`1.0.85`). |
| `oddyssey-version` | The oddyssey release tag resolved and installed (`v1.12.1`). |
| `model` | The `model` input, echoed. |

The step's log and the run's summary state the same three values.

## Auth

The step that runs `copilot` authenticates with the workflow's own
token: the job grants `copilot-requests: write` and the step sets
`GITHUB_TOKEN: ${{ github.token }}` (the CLI's usage is then billed to
the repository's owner - an organization needs its "Copilot CLI" policy
on). A personal token in the CLI's own variable, `COPILOT_GITHUB_TOKEN`,
is the alternative when the run must be billed to a user. The action
needs no Copilot token: it hands the ambient `github.token` to the
CLI's installer only, to lift the anonymous download rate limit, and
validates nothing beyond the CLI answering.

## What lands where

- The Copilot CLI, at its latest release, under the runner's temporary
  directory, on the `PATH` of the later steps. It comes through GitHub's
  own installer, `curl -fsSL https://gh.io/copilot-install | bash`,
  fetched on every run, which checks the archive against the release's
  `SHA256SUMS` and aborts on a mismatch.
- The oddyssey package at the resolved release, in **user scope**
  (`apm install --global --target copilot`, apm-cli at oddyssey's own
  pin): prompts, agents, hooks and the MCP server registration under
  `~/.copilot/`, the skills under `~/.agents/skills/`. The checkout
  stays clean. `latest` is the highest `vX.Y.Z` tag of the oddyssey
  repository; the action fails when nothing was deployed, and prints the
  count it found.

## Example workflow

```yaml
name: odd-status

on:
  workflow_dispatch:

permissions:
  contents: read
  copilot-requests: write

jobs:
  status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: using-system/oddyssey-actions/setup-copilot@v1
        with:
          model: claude-sonnet-5
      - name: Where is the ODD loop?
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: copilot -p "/odd-status" --allow-all-tools --allow-all-paths --no-ask-user
```

The launch line is the caller's, and each flag is load-bearing:
`--allow-all-tools` is what non-interactive mode requires;
`--allow-all-paths` lets the run execute the skills' scripts, which live
under the runner's home rather than the checkout; `--no-ask-user`
removes the tool a run would otherwise use to ask a question nobody
answers. The Copilot CLI does not expand a slash command: `/odd-status`
reaches the model as written, and the model routes it to the packaged
skill. Add `--model` to override `COPILOT_MODEL` for one step, and
`--output-format json` with `--usage-output-file <path>` to keep the
session's events and its usage.

## Pinning

`@v1` follows the latest release of this major; an exact tag or a
commit SHA freezes the action. `oddyssey-version` freezes the package.
