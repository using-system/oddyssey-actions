"""The opencode install: the release's archive, verified against the
checksum the action pins for this runner, and the version checked."""

from archives import runner, sha256, tar_gz, zip_

VERSION = "1.18.31"
OS, ARCH = runner()
ASSET = f"opencode-{OS}-{ARCH}." + ("zip" if OS == "darwin" else "tar.gz")
PIN = f"SHA256_{OS.upper()}_{ARCH.upper()}"


def archive(answer: str = VERSION) -> bytes:
    return (zip_ if ASSET.endswith(".zip") else tar_gz)("opencode", answer)


def env(tmp_path, archive: bytes):
    return {
        "OPENCODE_VERSION": VERSION,
        "PREFIX": str(tmp_path / "opencode"),
        "SHA256_LINUX_X64": "0" * 64,
        "SHA256_LINUX_ARM64": "0" * 64,
        "SHA256_DARWIN_ARM64": "0" * 64,
        "SHA256_DARWIN_X64": "0" * 64,
        PIN: sha256(archive),
    }


def test_installs_the_verified_archive_and_checks_the_version(
    script, fake_curl, tmp_path
):
    data = archive()
    curl = fake_curl({ASSET: data})
    result = script("setup-opencode", "install-opencode.sh").run(env(tmp_path, data))
    assert result.returncode == 0, result.log
    assert result.outputs == {"version": VERSION}
    assert result.path == [str(tmp_path / "opencode" / "bin")]
    assert (tmp_path / "opencode" / "bin" / "opencode").exists()
    assert f"opencode {VERSION} ({ASSET}, checksum verified)" in result.stdout
    urls = [a for call in curl.calls() for a in call if a.startswith("https://")]
    assert urls == [
        f"https://github.com/sst/opencode/releases/download/v{VERSION}/{ASSET}"
    ]
    # A reset connection is not a "transient" error to curl's --retry alone:
    # every download retries on every error, and what lands is checksummed.
    for call in curl.calls():
        assert "--retry" in call and "--retry-all-errors" in call, call


def test_fails_on_a_checksum_mismatch_before_extracting(script, fake_curl, tmp_path):
    data = archive()
    fake_curl({ASSET: data})
    result = script("setup-opencode", "install-opencode.sh").run(
        {**env(tmp_path, data), PIN: "f" * 64}
    )
    assert result.returncode == 1
    assert (
        f"::error::{ASSET} of opencode v{VERSION} does not match the checksum this action pins"
        in result.stdout
    )
    assert not (tmp_path / "opencode").exists()
    assert result.path == []


def test_fails_when_the_download_fails(script, fake_curl, tmp_path):
    fake_curl({})
    result = script("setup-opencode", "install-opencode.sh").run(env(tmp_path, b""))
    assert result.returncode != 0
    assert not (tmp_path / "opencode").exists()


def test_fails_when_the_installed_cli_answers_another_version(
    script, fake_curl, tmp_path
):
    data = archive("1.18.30")
    fake_curl({ASSET: data})
    result = script("setup-opencode", "install-opencode.sh").run(env(tmp_path, data))
    assert result.returncode == 1
    assert (
        "::error::the installed opencode answered '1.18.30', not version 1.18.31"
        in result.stdout
    )
    assert result.outputs == {}
