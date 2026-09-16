# setup-opencode

Installs opencode and the oddyssey package on the runner, with an
OpenAI-compatible endpoint as the model provider, so a later step can
run an oddyssey prompt:

```yaml
- uses: using-system/oddyssey-actions/setup-opencode@v1
  with:
    openai-api-key: ${{ secrets.OPENROUTER_API_KEY }}
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `model` | no | `openai/gpt-5.6-luna` | The model the missions run on, as the endpoint names it. The default is the cheapest model of the [oddyssey benchmark](https://github.com/using-system/oddyssey/blob/main/.llms-benchmark/README.md), under its OpenRouter id. Declared to opencode under the `openai-compatible` provider; only this model is declared. |
| `oddyssey-version` | no | `latest` | The oddyssey release to install: a release tag (`v1.12.1`), a full commit SHA (the one immutable form), or `latest`, the newest release tag at the time the workflow runs. |
| `openai-base-url` | no | `https://openrouter.ai/api/v1` | The OpenAI-compatible endpoint (`/v1/chat/completions` behind it) the model is served from. |
| `openai-api-key` | yes | | The API key of that endpoint, a secret. |

## Outputs

| Output | What it is |
| --- | --- |
| `opencode-version` | The opencode version installed (`1.18.31`). |
| `oddyssey-version` | The oddyssey ref resolved and installed (`v1.12.1`, or the SHA given). |
| `model` | The model in opencode's form (`openai-compatible/openai/gpt-5.6-luna`). |

The later steps also receive `ODDYSSEY_CLI=opencode` and
`ODDYSSEY_MODEL=<the model output>` in their environment: the
[`odd-status`](../odd-status/README.md) action reads them to know which
CLI to launch and how. The step's log and the run's summary state the
versions, the model and the endpoint.

## Auth

The key is the caller's, passed as the `openai-api-key` input from a
secret. The action writes it to a file under the runner's temporary
directory, readable by the runner's user only, that opencode's provider
reads (`{file:...}`); it is never exported to the environment and never
printed. The action itself reads no other token: every download it
makes is anonymous.

## What lands where

- opencode at the release the action pins (`1.18.31`, bumped by a
  release of this action), under the runner's temporary directory, on
  the `PATH` of the later steps. The action downloads the archive from
  that release's assets on github.com and checks it against the
  SHA-256 the action carries for it (opencode publishes no checksum
  file), failing on a mismatch; no installer script runs.
- The oddyssey package at the resolved ref, in **user scope**
  (`apm install --global --target opencode --only apm`, apm-cli at
  oddyssey's own pin, its dependency closure bounded to what PyPI
  carried on the day of that pin): agents, commands and skills under
  `~/.config/opencode/`. The checkout stays clean. `latest` is resolved
  **on the consumer's runner, at run time**, as the highest `vX.Y.Z`
  tag of the oddyssey repository, and a tag is a mutable ref: a
  workflow that must reproduce pins a full commit SHA. The action fails
  when nothing was deployed, and prints the count it found.
- opencode's global config, `~/.config/opencode/opencode.json`,
  **replaced** by one that declares the endpoint as an
  `@ai-sdk/openai-compatible` provider named `openai-compatible` with
  the model, and registers the package's MCP server as the package's
  own manifest defines it (apm cannot register it at user scope for
  opencode).

## Example workflow

```yaml
name: odd-status

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: using-system/oddyssey-actions/setup-opencode@v1
        with:
          openai-api-key: ${{ secrets.OPENROUTER_API_KEY }}
      - uses: using-system/oddyssey-actions/odd-status@v1
```

The step that runs a prompt is an action of this repository, never a
hand-written headless line: [`odd-status`](../odd-status/README.md)
launches opencode with the packaged `odd-status` command, scoped, and
turns the answer into outputs a workflow can gate on.

## What this grants

A later step that launches opencode with `--auto` lets the model run any
shell command the runner allows, read and write the checkout and the
package's directory, reach the network, and read the key file through
the provider (and through a shell, since the runner's user owns it).
Keep the job at `contents: read`, never put such a step on a trigger
that carries untrusted input (`issue_comment`, `pull_request_target`, a
fork's `pull_request`), and treat the answer as untrusted text before it
reaches a place that acts on it. The oddyssey package the step runs is
what the resolved ref contains: pin a commit SHA when that must not
move under you.

## Pinning

`@v1` follows the latest release of this major; an exact tag or a
commit SHA freezes the action. `oddyssey-version` freezes the package.
