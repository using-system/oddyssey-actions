"""The oddyssey release resolution, the one step every setup action runs
(scripts/resolve-oddyssey.sh, behind each setup's resolve.sh): a fake
`git ls-remote` serves the release tags, and the step picks, never
below the minimum the repository names."""

import re
from pathlib import Path

MINIMUM = (
    (Path(__file__).resolve().parents[1] / "ODDYSSEY_MINIMUM_VERSION")
    .read_text()
    .strip()
)
assert re.fullmatch(r"v\d+\.\d+\.\d+", MINIMUM), MINIMUM
_major, _minor, _patch = map(int, MINIMUM[1:].split("."))
NEXT = f"v{_major}.{_minor}.{_patch + 1}"
# v1.10.0 predates every minimum this repository names (the first was v1.12.2)
TAGS = "\n".join(
    f"{i:040x}\trefs/tags/{tag}"
    for i, tag in enumerate(["v1.9.0", "v1.10.0", "v1.10.0-rc1", MINIMUM, NEXT])
)
SHA = "a" * 40
BELOW = "requested: {requested}, below the minimum"

RESOLVES = [
    # the highest plain vX.Y.Z, sorted as versions, no pre-release
    ("latest", NEXT, ""),
    (NEXT, NEXT, ""),
    (MINIMUM, MINIMUM, ""),
    (MINIMUM[1:], MINIMUM, ""),  # the v prefix is added
    ("v1.10.0", MINIMUM, BELOW),  # below the minimum: the minimum, and the run says so
    ("1.10.0", MINIMUM, BELOW),
    (SHA, SHA, ""),  # a full commit SHA is taken as is, no remote read, no minimum
]

REJECTS = [
    ("", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v1.10.0\nv1.9.0", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v1.10.0;rm", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v9.9.9", "is not a release tag of using-system/oddyssey"),
    ("v1.10.0-rc1", "is not a release tag of using-system/oddyssey"),
]


def check_resolves(script, fake_cli, action, requested, expected, note):
    git = fake_cli("git", stdout=TAGS + "\n")
    result = script(action, "resolve.sh").run({"REQUESTED": requested})
    assert result.returncode == 0, result.log
    note = note.format(requested=requested)
    assert result.outputs == {"version": expected, "note": note}
    if note:
        assert f"::notice::oddyssey {expected} ({note})" in result.stdout
    else:
        assert f"oddyssey {expected} (requested: {requested}" in result.stdout
    if requested == SHA:
        assert not git.called
        assert "a commit SHA taken as is" in result.stdout
    else:
        assert git.list()[:3] == ["ls-remote", "--tags", "--refs"]


def check_rejects(script, fake_cli, action, requested, error):
    fake_cli("git", stdout=TAGS + "\n")
    result = script(action, "resolve.sh").run({"REQUESTED": requested})
    assert result.returncode == 1
    assert "::error::" in result.stdout and error in result.stdout
    assert result.outputs == {}


def check_no_tags_readable(script, fake_cli, action):
    fake_cli("git", script="exit 128")
    result = script(action, "resolve.sh").run({"REQUESTED": "latest"})
    assert result.returncode == 1
    assert (
        "::error::no release tag of using-system/oddyssey could be read"
        in result.stdout
    )


def check_minimum_not_released(script, fake_cli, action):
    # the remote no longer carries the minimum: nothing older is installed
    fake_cli(
        "git", stdout=TAGS.replace(f"refs/tags/{MINIMUM}", "refs/tags/v0.0.1") + "\n"
    )
    result = script(action, "resolve.sh").run({"REQUESTED": "v1.10.0"})
    assert result.returncode == 1
    assert (
        f"::error::the minimum oddyssey version {MINIMUM} is not a release tag"
        in result.stdout
    )
    assert result.outputs == {}
