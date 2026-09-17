"""What the runner carries, in the log and the run's summary."""

ENV = {
    "OPENCODE_VERSION": "1.18.31",
    "VERSION": "v1.12.2",
    "NOTE": "",
    "SKILLS": "9",
    "MODEL": "openai/gpt-5.6-luna",
    "BASE_URL": "https://openrouter.ai/api/v1",
}


def test_states_the_versions_the_model_and_the_endpoint(script):
    result = script("setup-opencode", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "opencode 1.18.31, oddyssey v1.12.2 (9 skills), model openai/gpt-5.6-luna at https://openrouter.ai/api/v1"
        in result.stdout
    )
    assert result.summary.startswith("### setup-opencode\n")
    for row in (
        "| opencode | 1.18.31 |",
        "| oddyssey | v1.12.2 (9 skills) |",
        "| endpoint | https://openrouter.ai/api/v1 |",
    ):
        assert row in result.summary


def test_says_why_the_version_is_not_the_one_requested(script):
    result = script("setup-opencode", "summary.sh").run(
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
