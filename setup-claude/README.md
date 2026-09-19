# setup-claude

Installs Claude Code and the oddyssey package on the runner, an
Anthropic API key or a Claude OAuth token as its credential, so a later
step can run an oddyssey prompt:

```yaml
- uses: using-system/oddyssey-actions/setup-claude@v1
  with:
    claude-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

## Inputs

| Input | Required | Default | What it is |
| --- | --- | --- | --- |
| `model` | no | `claude-sonnet-5` | The Claude model the missions run on, as `claude --model` names it: an alias for the latest of a tier (`fable`, `opus`, `sonnet`, `haiku`) or a full id (`claude-sonnet-5`, `claude-haiku-4-5`). The default is the cheapest Claude model of the [oddyssey benchmark](https://github.com/using-system/oddyssey/blob/main/.llms-benchmark/README.md). Exported to the later steps as `ODDYSSEY_MODEL`; never written to a config file. |
| `oddyssey-version` | no | `latest` | The oddyssey release to install: a release tag (`v1.12.2`), a full commit SHA (the one immutable form), or `latest`, the newest release tag at the time the workflow runs. A tag is at least the minimum this release of the actions names ([`ODDYSSEY_MINIMUM_VERSION`](../ODDYSSEY_MINIMUM_VERSION)): below it, the minimum is installed and the log and the summary say so. |
| `anthropic-api-key` | one of the two | | An Anthropic API key from the [Claude Console](https://platform.claude.com), a secret. |
| `claude-oauth-token` | one of the two | | A Claude OAuth token from `claude setup-token`, a secret: it authenticates with the subscription of the person who ran it (Pro, Max, Team or Enterprise), for one year. |

Exactly one of `anthropic-api-key` and `claude-oauth-token`: none fails
the setup, both fail it too.

## Outputs

| Output | What it is |
| --- | --- |
| `claude-version` | The Claude Code version installed (`2.1.267`). |
| `oddyssey-version` | The oddyssey ref resolved and installed (`v1.12.2`, or the SHA given). |
| `model` | The `model` input, echoed. |

The later steps also receive `ODDYSSEY_CLI=claude` and
`ODDYSSEY_MODEL=<the model>` in their environment: the
[`odd-status`](../odd-status/README.md) action reads them to know which
CLI to launch and how. They also receive `CLAUDE_CREDENTIAL_FILE` and
`CLAUDE_CREDENTIAL_KIND` (`api-key` or `oauth-token`): where the
credential is, never what it is. The step's log and the run's summary
state the versions, the model and the credential's kind.

## Auth

The credential is the caller's, passed as one of the two inputs from a
secret. The action writes it to a file under the runner's temporary
directory, readable by the runner's user only; it is never written to
`GITHUB_ENV`, so no later step of the job sees it, and never printed.
The launch step of [`odd-status`](../odd-status/README.md) reads that
file into the CLI's own variable, `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN` by the kind, for that one process. The file
lives for the job: a hosted runner discards it with the workspace, a
self-hosted one keeps it. The action itself reads no other token: every
download it makes - Claude Code, uv, apm-cli, the package - is
anonymous.

Which credential: an API key is billed to the Console organisation and
can be shared across repositories; an OAuth token is tied to one
person's subscription (Claude Code's own GitHub Actions documentation
says the same and names the same two secrets). The CLI reads
`ANTHROPIC_API_KEY` before `CLAUDE_CODE_OAUTH_TOKEN` (its authentication
documentation), so the launch step fails when either is already in its
environment rather than let one silently replace the input.

## What lands where

- Claude Code at the release the action pins (`2.1.267`, the `stable`
  channel's version when the pin was set, bumped by a release of this
  action), under the runner's temporary directory, on the `PATH` of the
  later steps. The action downloads the binary from the release
  channel's own assets (`downloads.claude.ai/claude-code-releases/<version>/<platform>/claude`)
  and checks it against that release's `manifest.json` itself, failing
  when the manifest cannot be read or the checksum does not match; no
  installer script runs, nothing comes from npm. The manifest's GPG
  signature is not verified.
- uv at the release the action pins (`0.12.12`, bumped by a release of
  this action), installed by `astral-sh/setup-uv` at a pinned commit
  into the runner's tool cache and put on the `PATH` of the later
  steps: the binary is downloaded from Astral's mirror, falling back to
  the release's assets on github.com, anonymously (the action passes no
  token), its URL read from Astral's versions manifest (`astral-sh/versions`,
  fetched at run time) and its checksum from the table that commit of
  setup-uv bundles for the version - the manifest can break the
  download, never swap the binary. setup-uv's Actions cache is off:
  nothing is hashed for a key, restored or saved; it still reads the
  checkout's `uv.toml` and `pyproject.toml` (for a `cache-dir`) and runs
  `uv python find` there. It runs `uvx` for the package install below.
- The oddyssey package at the resolved ref, in **user scope**
  (`apm install --global --target claude`, apm-cli at oddyssey's own
  pin, its dependency closure bounded to what PyPI carried on the day
  of that pin): commands, agents and skills under `~/.claude/`, the MCP
  server registered in `~/.claude.json`. The checkout stays clean.
  `latest` is resolved **on the consumer's runner, at run time**, as
  the highest `vX.Y.Z` tag of the oddyssey repository, and a tag is a
  mutable ref: a workflow that must reproduce pins a full commit SHA.
  The action fails when nothing was deployed, and prints the count it
  found.
- The credential, in `$RUNNER_TEMP/claude-code/credential`, mode 600.

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
        with:
          persist-credentials: false
      - uses: using-system/oddyssey-actions/setup-claude@v1
        with:
          model: haiku # optional; claude-sonnet-5 without it
          claude-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
      - uses: using-system/oddyssey-actions/odd-status@v1
```

With an API key, `anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}`
in place of the token line. The step that runs a prompt is an action of
this repository, never a hand-written headless line:
[`odd-status`](../odd-status/README.md) launches Claude Code with the
packaged command, scoped, and turns the answer into outputs a workflow
can gate on. Claude Code expands `/odd-status` itself, from the
user-scope command the package deployed.

## What this grants

A later step that launches Claude Code with
`--permission-mode bypassPermissions` (what non-interactive mode
requires) lets the model run any shell command the runner allows, read
and write the checkout and the package's directory, reach the network,
and read the credential file through a shell, since the runner's user
owns it (as it can read the job token `actions/checkout` persists in
`.git/config` at its defaults: the example sets
`persist-credentials: false`, since nothing here uses git with it).
The actions of this repository add `--setting-sources user`
(nothing from the checkout's `.claude/`: no project settings, no
hooks), `--no-session-persistence` and `DISABLE_AUTOUPDATER=1`; the
checkout's `CLAUDE.md` still reaches the run, since the CLI reads it
outside its settings. Keep the job at `contents: read`, never put such
a step on a trigger that carries untrusted input (`issue_comment`,
`pull_request_target`, a fork's `pull_request`), and treat the answer
as untrusted text before it reaches a place that acts on it. The
oddyssey package the step runs is what the resolved ref contains: pin a
commit SHA when that must not move under you.

## Pinning

`@v1` follows the latest release of this major; a commit SHA freezes
the action; an exact tag is never deleted or rewound (the repository's
`v*` tag ruleset blocks both, for admins too), though a writer can
still move it forward along `main`. `oddyssey-version` freezes the
package: a tag at or above the minimum, or a commit SHA.
