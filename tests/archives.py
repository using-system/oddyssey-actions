"""Archives an install step downloads, built by the test: a fake CLI that
answers its version, packed the way the release does, with its checksum."""

from __future__ import annotations

import hashlib
import io
import platform
import tarfile
import zipfile


def script(name: str, answer: str) -> bytes:
    return f"#!/usr/bin/env bash\ncat <<'ANSWER'\n{answer}\nANSWER\n".encode()


def tar_gz(name: str, answer: str) -> bytes:
    body = script(name, answer)
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(body)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(body))
    return out.getvalue()


def zip_(name: str, answer: str) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        info = zipfile.ZipInfo(name)
        info.external_attr = 0o755 << 16
        archive.writestr(info, script(name, answer))
    return out.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runner() -> tuple[str, str]:
    """(os, arch) as the install steps name them, for the machine the
    tests run on."""
    os_ = {"Linux": "linux", "Darwin": "darwin"}[platform.system()]
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}[
        platform.machine()
    ]
    return os_, arch
