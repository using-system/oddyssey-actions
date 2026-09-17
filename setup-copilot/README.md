# setup-copilot

Installs the GitHub Copilot CLI and the oddyssey package on the runner,
so a later step can run an oddyssey prompt headlessly:

```yaml
- uses: using-system/oddyssey-actions/setup-copilot@v1
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `model` | no | `gpt-5.6-luna` | The Copilot model the missions run on, as the CLI's model picker names it. The default is the cheapest model of the [oddyssey benchmark](https://github.com/using-system/oddyssey/blob/main/.llms-benchmark/README.md). Exported to the later steps as `COPILOT_MODEL` (which `--model` on a launch line overrides) and as `ODDYSSEY_MODEL`; never written to a config file. |
| `oddyssey-version` | no | `latest` | The oddyssey release to install: a release tag (`v1.12.2`), a full commit SHA (the one immutable form), or `latest`, the newest release tag at the time the workflow runs. A tag is at least the minimum this release of the actions names ([`ODDYSSEY_MINIMUM_VERSION`](../ODDYSSEY_MINIMUM_VERSION)): below it, the minimum is installed and the log and the summary say so. |

## Outputs

| Output | What it is |
| --- | --- |
| `copilot-version` | The Copilot CLI version installed (`1.0.85`). |
| `oddyssey-version` | The oddyssey ref resolved and installed (`v1.12.2`, or the SHA given). |
| `model` | The `model` input, echoed. |

The later steps also receive `ODDYSSEY_CLI=copilot` and
`ODDYSSEY_MODEL=<the model>` in their environment: the
[`odd-status`](../odd-status/README.md) action reads them to know which
CLI to launch and how. The step's log and the run's summary state the
same three values.

## Auth

The step that runs `copilot` authenticates with the workflow's own
token: the job grants `copilot-requests: write`, and the
[`odd-status`](../odd-status/README.md) action reads `github.token`
itself on its Copilot launch step (the CLI's usage is then billed to
the repository's owner - an organization needs its "Copilot CLI" policy
on). Nothing is set on the caller's step. A user token passed as that
action's `token` input is the alternative when the run must be billed
to a user; a `COPILOT_GITHUB_TOKEN` or `GH_TOKEN` in the environment
fails that step instead, since the CLI would prefer it over the input.
This action itself reads no token at all: every download it makes is
anonymous, and it validates nothing beyond the CLI answering.

## What lands where

- The Copilot CLI at the release the action pins (`1.0.85`, bumped by a
  release of this action), under the runner's temporary directory, on
  the `PATH` of the later steps. The action downloads the archive from
  that release's assets on github.com and checks it against the
  release's `SHA256SUMS` itself, failing when the checksums cannot be
  read or do not match; no installer script runs.
- The oddyssey package at the resolved ref, in **user scope**
  (`apm install --global --target copilot`, apm-cli at oddyssey's own
  pin, its dependency closure bounded to what PyPI carried on the day
  of that pin): prompts, agents, hooks and the MCP server registration
  under `~/.copilot/`, the skills under `~/.agents/skills/`. The
  checkout stays clean. `latest` is resolved **on the consumer's
  runner, at run time**, as the highest `vX.Y.Z` tag of the oddyssey
  repository, and a tag is a mutable ref: a workflow that must
  reproduce pins a full commit SHA. The action fails when nothing was
  deployed, and prints the count it found.

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
          model: claude-sonnet-5 # optional; gpt-5.6-luna without it
      - uses: using-system/oddyssey-actions/odd-status@v1
```

The step that runs a prompt is an action of this repository, never a
hand-written headless line: [`odd-status`](../odd-status/README.md)
launches the CLI with the packaged command, scoped, and turns the
answer into outputs a workflow can gate on. The Copilot CLI does not
expand a slash command: the text reaches the model as written, and the
model routes it to the packaged skill.

## What this grants

A step that launches the CLI (`--allow-all-tools`, which
non-interactive mode requires, grants a shell; the actions of this
repository add `--add-dir "$HOME/.agents/skills"` in place of
`--allow-all-paths`, `--no-custom-instructions`,
`--disable-builtin-mcps`, `--secret-env-vars GITHUB_TOKEN` and
`--no-auto-update`) lets the model run any shell command the runner
allows, read and write the checkout and the skills' directory, reach
the network, and read whatever the prompt and the skills put in front
of it. Keep the job at `contents: read` and `copilot-requests: write`,
never put the step on a trigger that carries untrusted input
(`issue_comment`, `pull_request_target`, a fork's `pull_request`), and
treat the answer as untrusted text before it reaches a place that acts
on it. The oddyssey package the step runs is what the resolved ref
contains: pin a commit SHA when that must not move under you.

## Pinning

`@v1` follows the latest release of this major; an exact tag or a
commit SHA freezes the action. `oddyssey-version` freezes the package.
