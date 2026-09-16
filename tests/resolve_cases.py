"""The oddyssey release resolution, the same step in every setup action:
a fake `git ls-remote` serves the release tags, and the step picks."""

TAGS = "\n".join(
    f"{i:040x}\trefs/tags/{tag}"
    for i, tag in enumerate(["v1.9.0", "v1.10.0", "v1.10.0-rc1", "v1.12.0"])
)
SHA = "a" * 40

RESOLVES = [
    (
        "latest",
        "v1.12.0",
    ),  # the highest plain vX.Y.Z, sorted as versions, no pre-release
    ("v1.10.0", "v1.10.0"),
    ("1.10.0", "v1.10.0"),  # the v prefix is added
    (SHA, SHA),  # a full commit SHA is taken as is, no remote read
]

REJECTS = [
    ("", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v1.10.0\nv1.9.0", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v1.10.0;rm", "oddyssey-version must be a tag, a full commit SHA or latest"),
    ("v9.9.9", "is not a release tag of using-system/oddyssey"),
    ("v1.10.0-rc1", "is not a release tag of using-system/oddyssey"),
]


def check_resolves(script, fake_cli, action, requested, expected):
    git = fake_cli("git", stdout=TAGS + "\n")
    result = script(action, "resolve.sh").run({"REQUESTED": requested})
    assert result.returncode == 0, result.log
    assert result.outputs == {"version": expected}
    assert f"oddyssey {expected} (requested: {requested})" in result.stdout
    if requested == SHA:
        assert not git.called
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
