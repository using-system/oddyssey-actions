# oddyssey-actions

GitHub Actions for [oddyssey](https://github.com/using-system/oddyssey),
Observability-Driven Development for coding agents. Each action prepares
a runner so the oddyssey prompts can run headlessly through a coding CLI
inside a workflow.

## Actions

| Action | What it does |
| --- | --- |
| [`setup-copilot`](setup-copilot/README.md) | Installs the GitHub Copilot CLI and the oddyssey package on the runner, the model and the package version as its only inputs. |

**One setup action per CLI.** Each CLI installs, authenticates, takes its
model and loads the package differently, so a `setup-<cli>` action owns
one CLI end to end. There is never one action with a `cli` input whose
other inputs mean something else per value. A `setup-claude` or
`setup-opencode` gets its own directory when a consumer needs it.

## Using an action

```yaml
- uses: using-system/oddyssey-actions/<action>@v1
```

Pin the floating major tag (`v1`, moved on every release of that
major), an exact release tag (`v1.0.0`), or a commit SHA. Each action's
README states its inputs, its outputs, which token the caller provides
and one complete example workflow.

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
