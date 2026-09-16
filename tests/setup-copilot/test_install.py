"""The Copilot CLI install: the release's archive, verified against the
release's SHA256SUMS before extraction, and the version checked."""

import stat

from archives import runner, sha256, tar_gz

VERSION = "1.0.85"
OS, ARCH = runner()
ASSET = f"copilot-{OS}-{ARCH}.tar.gz"
ANSWER = f"GitHub Copilot CLI {VERSION}.\nRun 'copilot update' to check for updates."


def env(tmp_path):
    return {"COPILOT_CLI_VERSION": VERSION, "PREFIX": str(tmp_path / "copilot-cli")}


def sums(archive: bytes, asset: str = ASSET) -> bytes:
    return f"{sha256(archive)}  {asset}\n{'0' * 64}  copilot-other.tar.gz\n".encode()


def test_installs_the_verified_archive_and_checks_the_version(
    script, fake_curl, tmp_path
):
    archive = tar_gz("copilot", ANSWER)
    curl = fake_curl({ASSET: archive, "SHA256SUMS.txt": sums(archive)})
    result = script("setup-copilot", "install-copilot.sh").run(env(tmp_path))
    assert result.returncode == 0, result.log
    assert result.outputs == {"version": VERSION}
    assert result.path == [str(tmp_path / "copilot-cli" / "bin")]
    binary = tmp_path / "copilot-cli" / "bin" / "copilot"
    assert binary.stat().st_mode & stat.S_IXUSR
    assert f"Copilot CLI {VERSION} ({ASSET}, checksum verified)" in result.stdout
    base = f"https://github.com/github/copilot-cli/releases/download/v{VERSION}"
    urls = [a for call in curl.calls() for a in call if a.startswith("https://")]
    assert urls == [f"{base}/{ASSET}", f"{base}/SHA256SUMS.txt"]


def test_fails_on_a_checksum_mismatch_before_extracting(script, fake_curl, tmp_path):
    archive = tar_gz("copilot", ANSWER)
    fake_curl({ASSET: archive, "SHA256SUMS.txt": sums(b"something else")})
    result = script("setup-copilot", "install-copilot.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert f"::error::{ASSET} does not match SHA256SUMS.txt" in result.stdout
    assert not (tmp_path / "copilot-cli").exists()
    assert result.path == []


def test_fails_when_the_checksums_carry_no_entry(script, fake_curl, tmp_path):
    archive = tar_gz("copilot", ANSWER)
    fake_curl(
        {ASSET: archive, "SHA256SUMS.txt": sums(archive, asset="copilot-other.tar.gz")}
    )
    result = script("setup-copilot", "install-copilot.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert "carries no entry for" in result.stdout
    assert not (tmp_path / "copilot-cli").exists()


def test_fails_when_the_checksums_cannot_be_read(script, fake_curl, tmp_path):
    fake_curl({ASSET: tar_gz("copilot", ANSWER)})
    result = script("setup-copilot", "install-copilot.sh").run(env(tmp_path))
    assert result.returncode != 0
    assert not (tmp_path / "copilot-cli").exists()


def test_fails_when_the_installed_cli_answers_another_version(
    script, fake_curl, tmp_path
):
    archive = tar_gz("copilot", "GitHub Copilot CLI 1.0.84.")
    fake_curl({ASSET: archive, "SHA256SUMS.txt": sums(archive)})
    result = script("setup-copilot", "install-copilot.sh").run(env(tmp_path))
    assert result.returncode == 1
    assert (
        "::error::the installed Copilot CLI answered 'GitHub Copilot CLI 1.0.84.', not version 1.0.85"
        in result.stdout
    )
    assert result.outputs == {}
