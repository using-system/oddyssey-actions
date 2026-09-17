"""What the runner carries, in the log and the run's summary."""

ENV = {
    "CLAUDE_VERSION": "2.1.267",
    "VERSION": "v1.12.2",
    "NOTE": "",
    "SKILLS": "9",
    "MODEL": "claude-sonnet-5",
    "KIND": "oauth-token",
}


def test_states_the_values(script):
    result = script("setup-claude", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "Claude Code 2.1.267, oddyssey v1.12.2 (9 skills), model claude-sonnet-5, credential oauth-token"
        in result.stdout
    )
    assert result.summary.startswith("### setup-claude\n")
    for row in (
        "| Claude Code | 2.1.267 |",
        "| oddyssey | v1.12.2 (9 skills) |",
        "| model | claude-sonnet-5 |",
        "| credential | oauth-token |",
    ):
        assert row in result.summary


def test_says_why_the_version_is_not_the_one_requested(script):
    result = script("setup-claude", "summary.sh").run(
        {**ENV, "NOTE": "requested: v1.10.0, below the minimum"}
    )
    assert result.returncode == 0, result.log
    assert (
        "oddyssey v1.12.2 (9 skills; requested: v1.10.0, below the minimum)"
        in result.stdout
    )
    assert (
        "| oddyssey | v1.12.2 (9 skills; requested: v1.10.0, below the minimum) |"
        in result.summary
    )
