"""Tests for verified release-wheel installation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from buildben_dev.distribution.install_release import ReleaseSelection, install_release


class FixtureSource:
    """Serve genuine asset bytes from a temporary release fixture."""

    def __init__(self, assets: dict[str, bytes]):
        self.assets = assets
        self.resolutions = 0

    def resolve(self, version: str | None) -> ReleaseSelection:
        self.resolutions += 1
        return ReleaseSelection("owner/app", "v1.2.3", "1" * 40, 7, False, False)

    def download_asset(
        self, selection: ReleaseSelection, filename: str, destination: Path
    ) -> None:
        destination.write_bytes(self.assets[filename])


def _payload() -> dict[str, bytes]:
    entries = {
        "runtime-requirements.txt": b"dep==1.0\n",
        "runtime-constraints.txt": b"dep==1.0\n",
        "app-1.2.3-py3-none-any.whl": b"wheel bytes",
    }
    manifest = {
        "schema_version": 1,
        "project": "app",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repository": "owner/app",
        "commit_sha": "1" * 40,
        "python_requires": ">=3.12",
        "application_wheel": {
            "filename": "app-1.2.3-py3-none-any.whl",
            "sha256": hashlib.sha256(entries["app-1.2.3-py3-none-any.whl"]).hexdigest(),
        },
        "source_archive": {"filename": "app-1.2.3.tar.gz", "sha256": "e" * 64},
        "runtime_lock": {
            "filename": "runtime-requirements.txt",
            "sha256": hashlib.sha256(entries["runtime-requirements.txt"]).hexdigest(),
        },
        "runtime_constraints": {
            "filename": "runtime-constraints.txt",
            "sha256": hashlib.sha256(entries["runtime-constraints.txt"]).hexdigest(),
        },
        "platforms": {
            "windows-x86_64": "app-1.2.3-windows-x86_64.zip",
            "linux-x86_64": "app-1.2.3-linux-x86_64.tar.gz",
            "macos-arm64": "app-1.2.3-macos-arm64.tar.gz",
        },
        "archive_members": {
            "windows-x86_64": sorted(
                [
                    "install_release.py",
                    "install-windows.cmd",
                    "install-windows.ps1",
                    "prepare-powershell-windows.cmd",
                    "release-manifest.json",
                    "runtime-constraints.txt",
                    "runtime-requirements.txt",
                ]
            ),
            "linux-x86_64": sorted(
                [
                    "install-linux-macos.sh",
                    "install_release.py",
                    "release-manifest.json",
                    "runtime-constraints.txt",
                    "runtime-requirements.txt",
                ]
            ),
            "macos-arm64": sorted(
                [
                    "install-linux-macos.sh",
                    "install-macos.command",
                    "install_release.py",
                    "release-manifest.json",
                    "runtime-constraints.txt",
                    "runtime-requirements.txt",
                ]
            ),
        },
    }
    entries["release-manifest.json"] = json.dumps(manifest).encode()
    return entries


def test_install_downloads_and_verifies_all_assets_before_uv(tmp_path: Path) -> None:
    source = FixtureSource(_payload())
    captured = tmp_path / "uv-arguments.json"
    uv = tmp_path / "uv"
    uv.write_text(
        "#!" + __import__("sys").executable + "\n"
        "import json, pathlib, sys\n"
        f"pathlib.Path({str(captured)!r}).write_text(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    install_release(
        repository="owner/app",
        distribution="app",
        uv=uv,
        python=Path("/python"),
        source=source,
    )
    assert source.resolutions == 1
    args = json.loads(captured.read_text(encoding="utf-8"))
    assert args[:7] == [
        "tool",
        "install",
        "--force",
        "--refresh",
        "--python",
        "/python",
        "--with-requirements",
    ]
    assert Path(args[-1]).name == "app-1.2.3-py3-none-any.whl"


def test_install_rejects_a_corrupt_lock_before_uv(tmp_path: Path) -> None:
    assets = _payload()
    assets["runtime-requirements.txt"] = b"tampered\n"
    source = FixtureSource(assets)
    uv = tmp_path / "uv"
    uv.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    uv.chmod(0o755)
    with pytest.raises(ValueError, match="runtime_lock"):
        install_release(
            repository="owner/app",
            distribution="app",
            uv=uv,
            python=Path("/python"),
            source=source,
        )


def test_install_rejects_requested_version_mismatch_before_uv(tmp_path: Path) -> None:
    source = FixtureSource(_payload())
    uv = tmp_path / "uv"
    uv.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    uv.chmod(0o755)

    with pytest.raises(ValueError, match="Requested version disagrees"):
        install_release(
            repository="owner/app",
            distribution="app",
            uv=uv,
            python=Path("/python"),
            version="9.8.7",
            source=source,
        )


def test_install_rejects_draft_release_before_downloading_payload(
    tmp_path: Path,
) -> None:
    class DraftSource(FixtureSource):
        def resolve(self, version: str | None) -> ReleaseSelection:
            self.resolutions += 1
            return ReleaseSelection("owner/app", "v1.2.3", "1" * 40, 7, True, False)

    source = DraftSource(_payload())
    uv = tmp_path / "uv"
    uv.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    uv.chmod(0o755)
    with pytest.raises(ValueError, match="ineligible"):
        install_release(
            repository="owner/app",
            distribution="app",
            uv=uv,
            python=Path("/python"),
            source=source,
        )
    assert source.resolutions == 1


def test_explicit_local_payload_must_be_complete(tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "release-manifest.json").write_bytes(_payload()["release-manifest.json"])
    uv = tmp_path / "uv"
    uv.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    uv.chmod(0o755)
    with pytest.raises(ValueError, match="Incomplete installer asset directory"):
        install_release(
            repository="owner/app",
            distribution="app",
            uv=uv,
            python=Path("/python"),
            asset_dir=payload,
        )
