"""What the runner carries, in the log and the run's summary."""

ENV = {
    "OPENCODE_VERSION": "1.18.31",
    "VERSION": "v1.12.0",
    "SKILLS": "9",
    "MODEL": "openai/gpt-5.6-luna",
    "BASE_URL": "https://openrouter.ai/api/v1",
}


def test_states_the_versions_the_model_and_the_endpoint(script):
    result = script("setup-opencode", "summary.sh").run(ENV)
    assert result.returncode == 0, result.log
    assert (
        "opencode 1.18.31, oddyssey v1.12.0 (9 skills), model openai/gpt-5.6-luna at https://openrouter.ai/api/v1"
        in result.stdout
    )
    assert result.summary.startswith("### setup-opencode\n")
    for row in (
        "| opencode | 1.18.31 |",
        "| oddyssey | v1.12.0 (9 skills) |",
        "| endpoint | https://openrouter.ai/api/v1 |",
    ):
        assert row in result.summary
