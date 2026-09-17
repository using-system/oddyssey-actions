"""The step that checks the inputs before anything is fetched."""

import pytest

ENV = {
    "MODEL": "openai/gpt-5.6-luna",
    "BASE_URL": "https://openrouter.ai/api/v1",
}


def test_the_defaults_pass(script):
    result = script("setup-opencode", "check.sh").run(ENV)
    assert result.returncode == 0, result.log


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"MODEL": ""}, "model must be a plain model id"),
        ({"MODEL": "openai/gpt 5"}, "model must be a plain model id"),
        ({"MODEL": "a\nb"}, "model must be a plain model id"),
        ({"BASE_URL": ""}, "openai-base-url must be a single https:// URL"),
        (
            {"BASE_URL": "https://a.example/v1 x"},
            "openai-base-url must be a single https:// URL",
        ),
        (
            {"BASE_URL": "http://a.example/v1"},
            "openai-base-url must be an https:// URL made of URL characters",
        ),
        (
            {"BASE_URL": 'https://a.example/v1"'},
            "openai-base-url must be an https:// URL made of URL characters",
        ),
    ],
)
def test_a_bad_input_fails_and_says_which(script, override, error):
    result = script("setup-opencode", "check.sh").run({**ENV, **override})
    assert result.returncode == 1
    assert f"::error::{error}" in result.stdout
