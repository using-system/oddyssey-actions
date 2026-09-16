<!-- PR title = the squash commit = the release note.
     Conventional Commits required - the rules live in CONTRIBUTING.md#pull-requests. -->

## What


## Why


## How to test


## Checklist

- [ ] References an existing issue (`Closes #N`, or `Closes using-system/oddyssey#N` when the work was specified there - open the issue first when none exists)
- [ ] PR title follows Conventional Commits (it becomes the squash commit and the release note - see CONTRIBUTING)
- [ ] No `!` / breaking marker (or it was explicitly discussed first)
- [ ] Every `uses:` is pinned to a full commit SHA with the version in a trailing comment
- [ ] No `${{ }}` expression inside a `run:` block - values pass through `env:`
- [ ] actionlint and shellcheck on `<action>/scripts/` pass, and the action's CI job is green on a bare checkout
- [ ] The action's README and the root catalog say what the action does now (inputs, outputs, the token sentence, the example workflow)
- [ ] No secrets in the diff - tokens by variable name only
