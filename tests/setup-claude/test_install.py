"""The Claude Code install: the release channel's binary, verified against
the release's manifest before it lands, and the version checked."""

import json
import stat

from archives import runner, script, sha256

VERSION = "2.1.267"
OS, ARCH = runner()
PLATFORM = f"{OS}-{ARCH}"
BASE = f"https://downloads.claude.ai/claude-code-releases/{VERSION}"


def binary(answer: str = f"{VERSION} (Claude Code)") -> bytes:
    return script("claude", answer)


def manifest(data: bytes, platform: str = PLATFORM) -> bytes:
    return json.dumps(
        {
            "version": VERSION,
            "platforms": {
                platform: {
                    "binary": "claude",
                    "checksum": sha256(data),
                    "size": len(data),
                },
                "win32-x64": {"binary": "claude.exe", "checksum": "0" * 64, "size": 1},
            },
        }
    ).encode()


def env(tmp_path):
    return {"CLAUDE_CODE_VERSION": VERSION, "PREFIX": str(tmp_path / "claude-code")}


def test_installs_the_verified_binary_and_checks_the_version(
    script, fake_curl, tmp_path
):
    data = binary()
    curl = fake_curl({"manifest.json": manifest(data), "claude": data})
    result = script("setup-claude", "install-claude.sh").run(env(tmp_path))
    assert result.returncode == 0, result.log
    assert result.outputs == {"version": VERSION}
    assert result.path == [str(tmp_path / "claude-code" / "bin")]
    installed = tmp_path / "claude-code" / "bin" / "claude"
    assert installed.stat().st_mode & stat.S_IXUSR
    assert f"Claude Code {VERSION} ({PLATFORM}, checksum verified)" in result.stdout
    urls = [a for call in curl.calls() for a in call if a.startswith("https://")]
    assert urls == [f"{BASE}/manifest.json", f"{BASE}/{PLATFORM}/claude"]


def test_fails_on_a_checksum_mismatch_before_installing(script, fake_curl, tmp_path):
    fake_curl({"manifest.json": manifest(b"something else"), "claude": binary()})
    result = script("setup-claude", "install-claude.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert f"::error::claude ({PLATFORM}) does not match the manifest" in result.stdout
    assert not (tmp_path / "claude-code").exists()
    assert result.path == []


def test_fails_when_the_manifest_carries_no_checksum_for_the_runner(
    script, fake_curl, tmp_path
):
    data = binary()
    curl = fake_curl(
        {"manifest.json": manifest(data, platform="win32-arm64"), "claude": data}
    )
    result = script("setup-claude", "install-claude.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert f"carries no checksum for {PLATFORM}" in result.stdout
    # nothing downloaded past the manifest
    assert len(curl.calls()) == 1


def test_fails_when_the_manifest_cannot_be_read(script, fake_curl, tmp_path):
    fake_curl({"claude": binary()})
    result = script("setup-claude", "install-claude.sh").run(env(tmp_path))
    assert result.returncode != 0
    assert not (tmp_path / "claude-code").exists()


def test_fails_when_the_installed_cli_answers_another_version(
    script, fake_curl, tmp_path
):
    data = binary("2.1.266 (Claude Code)")
    fake_curl({"manifest.json": manifest(data), "claude": data})
    result = script("setup-claude", "install-claude.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert (
        "::error::the installed Claude Code answered '2.1.266 (Claude Code)', not version 2.1.267"
        in result.stdout
    )
    assert result.outputs == {}
