"""What the runner carries, in the log and the run's summary."""

ENV = {
    "COPILOT_VERSION": "1.0.85",
    "VERSION": "v1.12.0",
    "SKILLS": "9",
    "MODEL": "gpt-5.6-luna",
}


def test_states_the_three_values(script):
    result = script("setup-copilot", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "Copilot CLI 1.0.85, oddyssey v1.12.0 (9 skills), model gpt-5.6-luna"
        in result.stdout
    )
    assert result.summary.startswith("### setup-copilot\n")
    for row in (
        "| Copilot CLI | 1.0.85 |",
        "| oddyssey | v1.12.0 (9 skills) |",
        "| model | gpt-5.6-luna |",
    ):
        assert row in result.summary
