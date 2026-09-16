"""What the runner carries, in the log and the run's summary."""

ENV = {
    "CLAUDE_VERSION": "2.1.267",
    "VERSION": "v1.12.0",
    "SKILLS": "9",
    "MODEL": "claude-sonnet-5",
    "KIND": "oauth-token",
}


def test_states_the_values(script):
    result = script("setup-claude", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "Claude Code 2.1.267, oddyssey v1.12.0 (9 skills), model claude-sonnet-5, credential oauth-token"
        in result.stdout
    )
    assert result.summary.startswith("### setup-claude\n")
    for row in (
        "| Claude Code | 2.1.267 |",
        "| oddyssey | v1.12.0 (9 skills) |",
        "| model | claude-sonnet-5 |",
        "| credential | oauth-token |",
    ):
        assert row in result.summary
