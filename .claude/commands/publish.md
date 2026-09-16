---
description: Cut a release - inspect the last pushed tag, pick the bump (patch, minor, or major), then tag and push; the tag push starts the release workflow
---

Cut an oddyssey-actions release. Pushing the version tag IS the release
order: the release workflow checks the tag is a plain `vX.Y.Z` on
`main`, creates the GitHub release with notes generated from the merged
PR titles, and moves the `vX` floating major tag to it. There is no
release PR, no artifact to publish and no approval gate: once the tag
is pushed, the release happens or the run fails.

- Arguments: $ARGUMENTS
- Expected fields (optional, free-form): the bump to apply (`patch`,
  `minor`, `major`) or an exact version (`1.2.0`). When present, skip
  the question in step 3 - the confirmation in step 4 still applies.

Steps:

1. **Preflight** - all of these must hold; stop naming the failing one
   otherwise:
   - `git fetch origin --tags --force` first, so tags and main are
     current;
   - the working tree is clean and the current branch is `main`, in
     sync with `origin/main` (not ahead, not behind);
   - read the latest version tag:
     `git tag -l 'v*.*.*' --sort=-v:refname | head -1` (the pattern
     skips the floating `v1`; no tag at all = first release, treat the
     base as v0.0.0 and say so);
   - check the latest tag's release run
     (`gh run list --workflow release.yml --limit 1`): if it FAILED,
     do not offer a new version - guide the recovery instead. The
     `v*` tag ruleset blocks deleting or rewinding a tag, for admins
     too, so the only recovery is "Re-run all jobs" on that run once
     the cause is fixed (`gh run rerun <run-id>`); the workflow is
     idempotent - an existing release is kept, the major tag is moved
     again. If it is still `queued`/`in_progress`, jump to step 5 and
     watch it instead of offering a new version.

2. **Show what would ship**: the last tag, then
   `git log --oneline <last-tag>..origin/main`. An empty log means
   nothing to release - say so and stop. Derive the recommendation
   from the conventional commit types: any `feat` - minor; else patch.
   Major is NEVER derived or preselected - a breaking release moves
   every consumer pinned on `@vX` to a tag that no longer follows
   them, and it is always the user's explicit call. When a breaking
   marker (`!`) appears in the log, surface it as evidence that major
   may be warranted and let the user choose it themselves.

3. **Ask which bump to release** (unless the arguments already said):
   compute the three candidate versions from the last tag and offer
   patch / minor / major with the recommendation first, each option
   showing its resulting `vX.Y.Z`. An exact version given as argument
   must be strict `X.Y.Z` AND greater than the last tag - reject
   anything else (the workflow only gates the shape; monotonicity is
   this command's job).

4. **Confirm before firing**: show verbatim the two commands about to
   run -
   `git tag vX.Y.Z` and `git push origin vX.Y.Z` -
   and state plainly that the push creates the GitHub release and
   moves the `vX` tag, so every consumer pinned on `@vX` runs this
   version on its next workflow run, and that the tag ruleset makes
   the push irreversible. Only on explicit confirmation, run both
   commands.

5. **Watch the run to completion**: name the tag pushed and the
   release run (`gh run list --workflow release.yml --limit 1`), then
   poll `gh run view <run-id> --json status,conclusion` (every ~20 s,
   in the background when possible) until the status is `completed`:
   - `failure` - report which step failed with its log pointer
     (`gh run view <run-id> --log-failed`) and the step-1 recovery
     guidance; stop. The tag stays: never try to delete or move it;
   - `success` - verify the outcome before saying so: the GitHub
     release exists WITH its generated notes
     (`gh release view vX.Y.Z --json body,url`; a header-only body is
     a failure to report), and the floating major tag points at the
     new one (`git ls-remote origin refs/tags/vX refs/tags/vX.Y.Z`
     dereferenced: `git ls-remote origin 'refs/tags/vX^{}'` must name
     the tagged commit). Once both are verified, go to step 6.

6. **Label the issues this release shipped** - the version is known and
   so is the set of issues, and this is the only moment both are true.
   Closed issues carry a `release: vX.Y.Z` label naming the release
   that shipped them; without this step the scheme decays into a
   snapshot and every later release leaves its issues unlabelled.

   - **Collect the PRs in the range** between the tag read in step 1
     and the one just released - squash-merge leaves the number as a
     `(#N)` suffix on every subject:
     `git log <last-tag>..vX.Y.Z --pretty=%s | sed -n 's/.*(#\([0-9]*\))$/\1/p'`
   - **Resolve each PR's issues**, with the repository they live in -
     a PR here may close an oddyssey issue
     (`Closes using-system/oddyssey#N`):
     `gh pr view <N> --json closingIssuesReferences --jq '.closingIssuesReferences[].url'`
     (the URL names the repository; an issue of this repository is
     `https://github.com/using-system/oddyssey-actions/issues/<n>`).
     A PR that closes none (chores, docs) contributes nothing - that
     is normal, not an error. An issue in another repository is
     reported, not labelled: its own release labels name that
     repository's releases.
   - **Create the label if it does not exist yet**, matching
     oddyssey's exactly:
     `gh label create "release: vX.Y.Z" --color 6F42C1 --description "Shipped in release vX.Y.Z"`
     - already-exists is a success, not a failure.
   - **Apply it**: `gh issue edit <n> --add-label "release: vX.Y.Z"`,
     once per resolved issue of this repository. `--add-label` is
     additive and leaves the type, priority and CLI labels alone.
   - **Report** the count and name every issue that could not be
     resolved or labelled, so the gap is visible rather than assumed
     covered.

   **A failure here never fails the release.** By this point the tag,
   the GitHub release and the moved `vX` tag are all public and
   irreversible; labelling is bookkeeping about a release that already
   happened. Report what did not get labelled and let the user fix it
   - never re-run the workflow for a label, and never present the
   release as failed because a label did not stick.
