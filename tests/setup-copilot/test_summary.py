"""What the runner carries, in the log and the run's summary."""

ENV = {
    "COPILOT_VERSION": "1.0.85",
    "VERSION": "v1.12.2",
    "NOTE": "",
    "SKILLS": "9",
    "MODEL": "gpt-5.6-luna",
}


def test_states_the_three_values(script):
    result = script("setup-copilot", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "Copilot CLI 1.0.85, oddyssey v1.12.2 (9 skills), model gpt-5.6-luna"
        in result.stdout
    )
    assert result.summary.startswith("### setup-copilot\n")
    for row in (
        "| Copilot CLI | 1.0.85 |",
        "| oddyssey | v1.12.2 (9 skills) |",
        "| model | gpt-5.6-luna |",
    ):
        assert row in result.summary


def test_says_why_the_version_is_not_the_one_requested(script):
    result = script("setup-copilot", "summary.sh").run(
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
