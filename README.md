# oddyssey-actions

GitHub Actions for [oddyssey](https://github.com/using-system/oddyssey),
Observability-Driven Development for coding agents. Each action prepares
a runner so the oddyssey prompts can run headlessly through a coding CLI
inside a workflow.

## Actions

| Action | What it does |
| --- | --- |
| [`setup-copilot`](setup-copilot/README.md) | Installs the GitHub Copilot CLI (pinned, checksum-verified) and the oddyssey package on the runner, the model (default `gpt-5.6-luna`) and the package version (default `latest`; a tag or a commit SHA) as its only inputs. |
| [`setup-opencode`](setup-opencode/README.md) | Installs opencode (pinned, checksum-verified) and the oddyssey package on the runner, an OpenAI-compatible endpoint as its provider (default OpenRouter, the key as a secret input), the same model and package version inputs. |
| [`odd-status`](odd-status/README.md) | Runs the packaged `/odd-status` through the CLI a setup action installed and turns its verdict (`ok`, `warning`, `error`, the next actions) into outputs; `fail-on` makes it a gate. |

**One setup action per CLI.** Each CLI installs, authenticates, takes its
model and loads the package differently, so a `setup-<cli>` action owns
one CLI end to end. There is never one action with a `cli` input whose
other inputs mean something else per value. Every setup action exports
`ODDYSSEY_CLI` and `ODDYSSEY_MODEL` to the later steps, which is how an
action that runs a prompt knows which CLI to launch and how. A
`setup-claude` gets its own directory when a consumer needs it.

## Using an action

```yaml
- uses: using-system/oddyssey-actions/<action>@v1
```

Pin the floating major tag (`v1`, moved on every release of that
major), an exact release tag (`v1.0.0`), or a commit SHA. Each action's
README states its inputs, its outputs, how the launch step
authenticates and one complete example workflow.

## Releases

A release is a tag `vX.Y.Z` pushed to this repository: the release
workflow creates the GitHub release from the merged PR titles and moves
the `vX` tag to it. Versions follow
[Conventional Commits](https://www.conventionalcommits.org/) on the PR
titles (`feat:` a minor, `fix:` a patch).

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) is the workflow, [AGENTS.md](AGENTS.md)
the conventions a coding agent reads, and the
[Code of Conduct](CODE_OF_CONDUCT.md) applies. Security reports go through
[private reporting](https://github.com/using-system/oddyssey-actions/security/advisories/new),
never a public issue ([SECURITY.md](SECURITY.md)).

## License

[MIT](LICENSE).
