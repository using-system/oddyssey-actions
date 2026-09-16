"""Run one script of an action, as its step on the runner would.

A test names an action and a script under `<action>/scripts/`, gives it
its environment, and gets back the exit code, the output, and what the
script wrote to GITHUB_OUTPUT, GITHUB_ENV, GITHUB_PATH and
GITHUB_STEP_SUMMARY. The script is the one in this checkout, never a
released one. HOME and RUNNER_TEMP are the test's temporary directory, so
a script that writes under the runner's home writes there.

A step that calls a tool gets a fake one on PATH: `fake_cli` records the
arguments and prints what the test asks, `fake_curl` serves the files the
test prepared, keyed by the URL's basename, so an install step downloads,
verifies and extracts an archive the test built.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# the case modules shared by several actions' tests live next to this file
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
TOKENS = ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN")


@dataclasses.dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    outputs: dict[str, str]
    env: dict[str, str]
    path: list[str]
    summary: str

    @property
    def log(self) -> str:
        return self.stdout + self.stderr


def _pairs(path: pathlib.Path) -> dict[str, str]:
    return dict(
        line.split("=", 1) for line in path.read_text().splitlines() if "=" in line
    )


class Script:
    def __init__(self, action: str, name: str, tmp: pathlib.Path):
        self.path = ROOT / action / "scripts" / name
        assert self.path.is_file(), self.path
        self.tmp = tmp

    def run(self, env: dict[str, str]) -> Result:
        files = {
            name: self.tmp / name.lower()
            for name in (
                "GITHUB_OUTPUT",
                "GITHUB_ENV",
                "GITHUB_PATH",
                "GITHUB_STEP_SUMMARY",
            )
        }
        for file in files.values():
            file.write_text("")
        home = self.tmp / "home"
        home.mkdir(exist_ok=True)
        clean = {k: v for k, v in os.environ.items() if k not in TOKENS}
        result = subprocess.run(
            [str(self.path)],
            env={
                **clean,
                "HOME": str(home),
                "RUNNER_TEMP": str(self.tmp),
                **{name: str(file) for name, file in files.items()},
                **env,
            },
            text=True,
            capture_output=True,
            check=False,
        )
        return Result(
            result.returncode,
            result.stdout,
            result.stderr,
            _pairs(files["GITHUB_OUTPUT"]),
            _pairs(files["GITHUB_ENV"]),
            files["GITHUB_PATH"].read_text().splitlines(),
            files["GITHUB_STEP_SUMMARY"].read_text(),
        )


class Argv:
    """What a fake tool was called with: one record per call, the
    arguments NUL-separated inside it."""

    def __init__(self, path: pathlib.Path):
        self.path = path

    @property
    def called(self) -> bool:
        return self.path.exists()

    def calls(self) -> list[list[str]]:
        return [
            call.split("\0")[:-1] for call in self.path.read_text().split("\x1e")[:-1]
        ]

    def list(self) -> list[str]:
        """The last call's arguments."""
        return self.calls()[-1]


@pytest.fixture
def script(tmp_path):
    return lambda action, name: Script(action, name, tmp_path)


@pytest.fixture
def home(tmp_path) -> pathlib.Path:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return home


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    """Put a fake `<name>` first on PATH: it records its argv, runs `script`
    (bash, with the argv still in `$@`) and prints `stdout`."""

    def make(name: str, stdout: str = "", script: str = "") -> Argv:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        argv = tmp_path / f"{name}.argv"
        out = tmp_path / f"{name}.stdout"
        out.write_text(stdout)
        (bin_dir / name).write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\0' \"$@\" >> {str(argv)!r}; printf '\\x1e' >> {str(argv)!r}\n"
            f"{script}\n"
            f"cat {str(out)!r}\n"
        )
        (bin_dir / name).chmod(0o755)
        monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
        return Argv(argv)

    return make


@pytest.fixture
def fake_curl(tmp_path, fake_cli):
    """A `curl -o <file> <url>` that copies the file the test prepared under
    the URL's basename, and fails as curl -f does when there is none."""

    served = tmp_path / "served"
    served.mkdir()

    def make(files: dict[str, bytes]) -> Argv:
        for name, content in files.items():
            (served / name).write_bytes(content)
        return fake_cli(
            "curl",
            script=textwrap.dedent(
                f"""\
                out=""; url=""
                while [ $# -gt 0 ]; do
                  case "$1" in
                    -o) out="$2"; shift 2 ;;
                    --retry) shift 2 ;;
                    -*) shift ;;
                    *) url="$1"; shift ;;
                  esac
                done
                src={str(served)!r}/$(basename "$url")
                [ -f "$src" ] || {{ echo "curl: (22) not served: $url" >&2; exit 22; }}
                cp "$src" "$out"
                """
            ),
        )

    return make
