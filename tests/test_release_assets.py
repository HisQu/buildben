"""Stateful contract tests for rerunnable GitHub draft publication."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
import threading
import tomllib
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from buildben_dev.packaging import release_assets

COMMIT = "a" * 40
TAG_OBJECT = "b" * 40


class StatefulReleaseApi:
    """Store tags, drafts, and uploaded bytes behind the publisher API boundary."""

    def __init__(self) -> None:
        self.commit = COMMIT
        self.release: dict[str, object] | None = None
        self.preceding_releases: list[dict[str, object]] = []
        self.release_list_error: str | None = None
        self.malformed_release_list_page = False
        self.assets: dict[int, tuple[str, bytes]] = {}
        self.next_asset_id = 1
        self.created_release_count = 0
        self.deleted_asset_names: list[str] = []
        self.asset_downloads = 0
        self.include_asset_digests = True
        self.corrupt_uploads = False
        self.watch_calls: list[int] = []
        self.watch_status = 0
        self.ci_runs: list[dict[str, object]] = []
        self.ci_queries = 0

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        data: bytes | None = None,
        headers: tuple[str, ...] = (),
    ) -> bytes:
        parsed = urlsplit(endpoint)
        path = parsed.path
        if path.endswith("/git/ref/tags/" + TAG):
            return self._json({"object": {"type": "tag", "sha": TAG_OBJECT}})
        if path.endswith("/git/tags/" + TAG_OBJECT):
            return self._json({"object": {"type": "commit", "sha": self.commit}})
        if path.endswith("/releases/tags/" + TAG):
            if self.release is None or self.release.get("draft") is True:
                raise release_assets.ReleaseError("HTTP 404: Not Found")
            return self._json(self._release_payload())
        if path.endswith("/releases") and method == "GET":
            if self.release_list_error is not None:
                raise release_assets.ReleaseError(self.release_list_error)
            if self.malformed_release_list_page:
                return self._json({"releases": []})
            query = parse_qs(parsed.query)
            per_page = int(query["per_page"][0])
            page = int(query["page"][0])
            releases = [*self.preceding_releases]
            if self.release is not None:
                releases.append(self._release_payload())
            start = (page - 1) * per_page
            return self._json(releases[start : start + per_page])
        if path.endswith("/actions/workflows/ci.yml/runs"):
            self.ci_queries += 1
            return self._json({"workflow_runs": self.ci_runs})
        if "/releases/assets/" in path:
            asset_id = int(path.rsplit("/", 1)[1])
            if method == "GET":
                self.asset_downloads += 1
                return self.assets[asset_id][1]
            if method == "DELETE":
                name, _ = self.assets.pop(asset_id)
                self.deleted_asset_names.append(name)
                return b""
        if path.endswith("/releases") and method == "POST":
            payload = json.loads(data or b"{}")
            assert payload["draft"] is True
            assert payload["prerelease"] is False
            self.created_release_count += 1
            self.release = {
                "id": 22,
                "tag_name": payload["tag_name"],
                "target_commitish": payload["target_commitish"],
                "draft": True,
                "prerelease": False,
                "body": payload["body"],
            }
            return self._json(self._release_payload())
        if parsed.netloc == "uploads.github.com" and method == "POST":
            name = parse_qs(parsed.query)["name"][0]
            uploaded = data or b""
            if self.corrupt_uploads:
                uploaded += b"corrupt"
            self._store(name, uploaded)
            return self._json({"name": name})
        if "/releases/" in path and method == "PATCH":
            assert self.release is not None
            self.release.update(json.loads(data or b"{}"))
            return self._json(self._release_payload())
        raise AssertionError(f"Unexpected API request: {method} {endpoint}")

    def watch_ci(self, repository: str, run_id: int) -> int:
        self.watch_calls.append(run_id)
        return self.watch_status

    def _store(self, name: str, data: bytes) -> None:
        assert self.release is not None
        for asset_id, (existing_name, _) in list(self.assets.items()):
            if existing_name == name:
                raise AssertionError(f"Asset {name} was not deleted before replacement")
        asset_id = self.next_asset_id
        self.next_asset_id += 1
        self.assets[asset_id] = (name, data)

    def _release_payload(self) -> dict[str, object]:
        assert self.release is not None
        asset_records = []
        for asset_id, (name, data) in self.assets.items():
            record: dict[str, object] = {"id": asset_id, "name": name}
            if self.include_asset_digests:
                record["digest"] = "sha256:" + hashlib.sha256(data).hexdigest()
            asset_records.append(record)
        return {**self.release, "assets": asset_records}

    @staticmethod
    def _json(value: object) -> bytes:
        return json.dumps(value, sort_keys=True).encode()


TAG = "v" + tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]


def _archive_bytes(root: str, files: dict[str, bytes], *, zipped: bool) -> bytes:
    output = io.BytesIO()
    if zipped:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(root + "/", b"")
            for name, data in files.items():
                archive.writestr(root + "/" + name, data)
    else:
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            root_info = tarfile.TarInfo(root + "/")
            root_info.type = tarfile.DIRTYPE
            archive.addfile(root_info)
            for name, data in files.items():
                info = tarfile.TarInfo(root + "/" + name)
                info.size = len(data)
                info.mode = 0o755 if name.endswith(".sh") else 0o644
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def _prepared_payload(directory: Path) -> list[str]:
    version = TAG[1:]
    wheel = f"buildben-{version}-py3-none-any.whl"
    sdist = f"buildben-{version}.tar.gz"
    runtime = b"# locked runtime requirements\n"
    constraints = b"# locked runtime constraints\n"
    helper = b"release helper\n"
    shell = b"#!/bin/sh\n"
    powershell = b"# PowerShell bootstrap\n"
    windows_files = {
        "install_release.py": helper,
        "install-windows.cmd": b"@echo off\r\n",
        "install-windows.ps1": powershell,
        "prepare-powershell-windows.cmd": b"@echo off\r\n",
        "release-manifest.json": b"",
        "runtime-requirements.txt": runtime,
        "runtime-constraints.txt": constraints,
    }
    linux_files = {
        "install-linux-macos.sh": shell,
        "install_release.py": helper,
        "release-manifest.json": b"",
        "runtime-requirements.txt": runtime,
        "runtime-constraints.txt": constraints,
    }
    macos_files = {
        **linux_files,
        "install-macos.command": b"#!/bin/sh\n",
    }
    archive_members = {
        "windows-x86_64": sorted(windows_files),
        "linux-x86_64": sorted(linux_files),
        "macos-arm64": sorted(macos_files),
    }
    files: dict[str, bytes] = {
        wheel: b"wheel payload",
        sdist: b"source payload",
        "runtime-requirements.txt": runtime,
        "runtime-constraints.txt": constraints,
        "release-notes.md": b"Release notes\n",
        "install-linux-macos.sh": shell,
        "install-windows.ps1": powershell,
        "install_release.py": helper,
    }
    manifest = {
        "schema_version": 1,
        "project": "buildben",
        "version": version,
        "tag": TAG,
        "repository": "HisQu/buildben",
        "commit_sha": COMMIT,
        "python_requires": ">=3.12",
        "application_wheel": {
            "filename": wheel,
            "sha256": hashlib.sha256(files[wheel]).hexdigest(),
        },
        "source_archive": {
            "filename": sdist,
            "sha256": hashlib.sha256(files[sdist]).hexdigest(),
        },
        "runtime_lock": {
            "filename": "runtime-requirements.txt",
            "sha256": hashlib.sha256(runtime).hexdigest(),
        },
        "runtime_constraints": {
            "filename": "runtime-constraints.txt",
            "sha256": hashlib.sha256(constraints).hexdigest(),
        },
        "platforms": {
            "windows-x86_64": f"buildben-{version}-windows-x86_64.zip",
            "linux-x86_64": f"buildben-{version}-linux-x86_64.tar.gz",
            "macos-arm64": f"buildben-{version}-macos-arm64.tar.gz",
        },
        "archive_members": archive_members,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    files["release-manifest.json"] = manifest_bytes
    windows_files["release-manifest.json"] = manifest_bytes
    linux_files["release-manifest.json"] = manifest_bytes
    macos_files["release-manifest.json"] = manifest_bytes
    for name, data in (
        ("runtime-requirements.txt", runtime),
        ("runtime-constraints.txt", constraints),
    ):
        windows_files[name] = data
        linux_files[name] = data
        macos_files[name] = data
    root = f"buildben-{version}"
    files[manifest["platforms"]["windows-x86_64"]] = _archive_bytes(
        root + "-windows-x86_64", windows_files, zipped=True
    )
    files[manifest["platforms"]["linux-x86_64"]] = _archive_bytes(
        root + "-linux-x86_64", linux_files, zipped=False
    )
    files[manifest["platforms"]["macos-arm64"]] = _archive_bytes(
        root + "-macos-arm64", macos_files, zipped=False
    )
    for name, data in files.items():
        (directory / name).write_bytes(data)
    return list(files)


def test_upload_rejects_boolean_manifest_schema_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    manifest_path = payload / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")

    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    with pytest.raises(
        release_assets.ReleaseError, match="unsupported schema or fields"
    ):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_upload_retry_reuses_identical_assets_and_finalizes_complete_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")

    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    original_count = len(api.assets)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert len(api.assets) == original_count
    release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)
    assert api.release is not None
    assert api.release["draft"] is False
    assert api.created_release_count == 1
    checksum = dict(api.assets.values())["SHA256SUMS"]
    expected_lines = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(
            (name, data) for name, data in api.assets.values() if name != "SHA256SUMS"
        )
    ).encode()
    assert checksum == expected_lines


def test_prepare_reuses_and_uploads_draft_when_by_tag_lookup_is_published_only(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    api.release = {
        "id": 22,
        "tag_name": TAG,
        "target_commitish": COMMIT,
        "draft": True,
        "prerelease": False,
        "body": "Existing draft",
    }
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")

    release = release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert release["id"] == 22
    assert api.created_release_count == 0
    assert api.release is not None and api.release["draft"] is True
    assert {name for name, _data in api.assets.values()} == set(names)


def test_prepare_finds_matching_draft_after_first_release_page(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.preceding_releases = [
        {"id": 100 + index, "tag_name": f"v1.0.{index}"} for index in range(100)
    ]
    api.release = {
        "id": 22,
        "tag_name": TAG,
        "target_commitish": COMMIT,
        "draft": True,
        "prerelease": False,
        "body": "Existing draft",
    }

    release = release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert release["id"] == 22
    assert api.created_release_count == 0


def test_prepare_does_not_create_draft_when_release_listing_fails(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.release_list_error = "HTTP 403: Resource not accessible"

    with pytest.raises(release_assets.ReleaseError, match="403"):
        release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert api.created_release_count == 0
    assert api.release is None


def test_prepare_rejects_malformed_release_listing_without_creation(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.malformed_release_list_page = True

    with pytest.raises(release_assets.ReleaseError, match="listing page is malformed"):
        release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert api.created_release_count == 0
    assert api.release is None


def test_prepare_rejects_ambiguous_matching_releases_without_mutation(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.preceding_releases = [{"id": 23, "tag_name": TAG}]
    api.release = {
        "id": 22,
        "tag_name": TAG,
        "target_commitish": COMMIT,
        "draft": True,
        "prerelease": False,
        "body": "Existing draft",
    }

    with pytest.raises(release_assets.ReleaseError, match="ambiguously identifies"):
        release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert api.created_release_count == 0
    assert api.release is not None
    assert api.release["draft"] is True
    assert api.release["body"] == "Existing draft"


def test_prepare_rejects_published_matching_release_without_mutation(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.release = {
        "id": 22,
        "tag_name": TAG,
        "target_commitish": COMMIT,
        "draft": False,
        "prerelease": False,
        "body": "Published release",
    }
    with pytest.raises(release_assets.ReleaseError, match="published"):
        release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert api.created_release_count == 0
    assert api.release is not None
    assert api.release["draft"] is False
    assert api.release["body"] == "Published release"


def test_upload_rejects_bytes_that_github_does_not_retain(tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    api.corrupt_uploads = True
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    with pytest.raises(release_assets.ReleaseError, match="incorrect digest"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert len(api.assets) == 1
    assert api.release is not None and api.release["draft"] is True


def test_prepare_rejects_draft_with_empty_target_commitish(tmp_path: Path) -> None:
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    api = StatefulReleaseApi()
    api.release = {
        "id": 22,
        "tag_name": TAG,
        "target_commitish": "",
        "draft": True,
        "prerelease": False,
        "body": "Existing draft",
    }

    with pytest.raises(release_assets.ReleaseError, match="target commit"):
        release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert api.created_release_count == 0
    assert api.release["draft"] is True


def test_partial_upload_retry_keeps_release_draft_and_replaces_only_owned_asset(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    partial = [*names[:3], "release-manifest.json"]
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, partial)
    with pytest.raises(release_assets.ReleaseError, match="incomplete"):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)
    assert api.release is not None and api.release["draft"] is True

    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    (payload / "release-notes.md").write_bytes(b"Corrected notes\n")
    release_assets.upload(
        api, "HisQu/buildben", TAG, COMMIT, payload, ["release-notes.md"]
    )
    assert api.deleted_asset_names == ["release-notes.md"]
    assert api.release is not None and api.release["draft"] is True


def test_wrong_tag_identity_and_unexpected_asset_never_publish(tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    api.commit = "c" * 40
    with pytest.raises(release_assets.ReleaseError, match="points to"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    api.commit = COMMIT
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    api._store("unexpected.bin", b"unowned")
    with pytest.raises(release_assets.ReleaseError, match="unexpected"):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)
    assert api.release is not None and api.release["draft"] is True


def test_wait_ci_requires_exact_workflow_sha_event_and_branch() -> None:
    api = StatefulReleaseApi()
    api.ci_runs = [
        {
            "id": 1,
            "head_sha": "d" * 40,
            "path": ".github/workflows/ci.yml",
            "event": "push",
            "head_branch": "main",
        },
        {
            "id": 2,
            "head_sha": COMMIT,
            "path": ".github/workflows/other.yml",
            "event": "push",
            "head_branch": "main",
        },
        {
            "id": 3,
            "head_sha": COMMIT,
            "path": ".github/workflows/ci.yml",
            "event": "pull_request",
            "head_branch": "main",
        },
        {
            "id": 4,
            "head_sha": COMMIT,
            "path": ".github/workflows/ci.yml",
            "event": "push",
            "head_branch": "main",
            "created_at": "2026-10-20T10:00:00Z",
            "status": "in_progress",
            "conclusion": None,
            "repository": {"full_name": "HisQu/buildben"},
            "head_repository": {"full_name": "HisQu/buildben"},
        },
    ]
    now = [0.0]

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    assert (
        release_assets.wait_ci(
            api,
            "HisQu/buildben",
            TAG,
            COMMIT,
            timeout=10,
            interval=5,
            clock=clock,
            sleep=sleep,
        )
        == 4
    )
    assert api.watch_calls == [4]


def test_wait_ci_times_out_without_dispatching_or_accepting_a_wrong_run() -> None:
    api = StatefulReleaseApi()
    api.ci_runs = [
        {
            "id": 5,
            "head_sha": COMMIT,
            "path": ".github/workflows/ci.yml",
            "event": "push",
            "head_branch": "release",
        },
        {
            "id": 6,
            "head_sha": COMMIT,
            "path": ".github/workflows/ci.yml",
            "event": "push",
            "head_branch": "main",
            "repository": {"full_name": "other/buildben"},
            "head_repository": {"full_name": "other/buildben"},
        },
    ]
    now = [0.0]

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    with pytest.raises(release_assets.ReleaseError, match="Dispatch ci.yml"):
        release_assets.wait_ci(
            api,
            "HisQu/buildben",
            TAG,
            COMMIT,
            timeout=6,
            interval=5,
            clock=clock,
            sleep=sleep,
        )
    assert api.watch_calls == []


def test_wait_ci_accepts_only_same_repository_tag_dispatch() -> None:
    api = StatefulReleaseApi()
    api.ci_runs = [
        {
            "id": 9,
            "head_sha": COMMIT,
            "path": ".github/workflows/ci.yml",
            "event": "workflow_dispatch",
            "head_branch": TAG,
            "repository": {"full_name": "HisQu/buildben"},
            "head_repository": {"full_name": "HisQu/buildben"},
        }
    ]
    now = [0.0]

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    assert (
        release_assets.wait_ci(
            api,
            "HisQu/buildben",
            TAG,
            COMMIT,
            timeout=10,
            interval=5,
            clock=clock,
            sleep=sleep,
        )
        == 9
    )
    assert api.watch_calls == [9]


def test_fetch_validates_lock_files_before_writing_application_wheel(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    destination = tmp_path / "download"
    requested = [
        "buildben-" + TAG[1:] + "-py3-none-any.whl",
        "runtime-requirements.txt",
        "runtime-constraints.txt",
    ]
    release_assets.fetch(api, "HisQu/buildben", TAG, COMMIT, destination, requested)
    assert (destination / requested[0]).read_bytes() == (
        payload / requested[0]
    ).read_bytes()
    assert (destination / "release-manifest.json").is_file()


def test_upload_rejects_tampered_application_wheel_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    wheel_name = next(name for name in names if name.endswith(".whl"))
    (payload / wheel_name).write_bytes(b"tampered wheel")
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    with pytest.raises(release_assets.ReleaseError, match="digest mismatch"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_upload_rejects_unsafe_archive_member_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    archive_name = next(name for name in names if "linux-x86_64" in name)
    archive_path = payload / archive_name
    root = f"buildben-{TAG[1:]}-linux-x86_64"
    with tarfile.open(archive_path, "r:gz") as archive:
        files: dict[str, bytes] = {}
        for member in archive.getmembers():
            if not member.isfile():
                continue
            contents = archive.extractfile(member)
            if contents is None:
                continue
            with contents:
                files[member.name.removeprefix(root + "/")] = contents.read()
    files["../escape"] = b"outside the archive root"
    archive_path.write_bytes(_archive_bytes(root, files, zipped=False))
    api = StatefulReleaseApi()
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    with pytest.raises(release_assets.ReleaseError, match="Unsafe archive member"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_upload_retry_verifies_identical_bytes_without_digest_metadata(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    names = _prepared_payload(payload)
    api = StatefulReleaseApi()
    api.include_asset_digests = False
    notes = tmp_path / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    first_download_count = api.asset_downloads
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert first_download_count > 0
    assert api.asset_downloads > first_download_count
    assert api.deleted_asset_names == []
    assert len(api.assets) == len(names)


def test_gh_upload_sends_length_and_preserves_binary_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("gh") is None:
        pytest.skip("gh executable is unavailable")

    payload = bytes(range(256)) * 4
    received: list[bytes] = []
    received_headers: list[tuple[list[str], str | None]] = []
    ref_path = f"/repos/HisQu/buildben/git/ref/tags/{TAG}"
    tag_path = f"/repos/HisQu/buildben/git/tags/{TAG_OBJECT}"

    class StrictHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: int, value: object) -> None:
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == ref_path:
                self._send_json(200, {"object": {"type": "tag", "sha": TAG_OBJECT}})
            elif path == tag_path:
                self._send_json(200, {"object": {"type": "commit", "sha": COMMIT}})
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            lengths = self.headers.get_all("Content-Length", [])
            transfer_encoding = self.headers.get("Transfer-Encoding")
            received_headers.append((lengths, transfer_encoding))
            if (
                len(lengths) != 1
                or lengths[0] != str(len(payload))
                or transfer_encoding is not None
            ):
                self.send_error(400, "Bad Content-Length")
                return
            body = self.rfile.read(int(lengths[0]))
            if body != payload:
                self.send_error(400, "Binary payload mismatch")
                return
            received.append(body)
            self._send_json(201, {"name": "binary-payload.bin"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), StrictHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    config_dir = tmp_path / "gh-config"
    config_dir.mkdir()
    monkeypatch.setenv("GH_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("GH_TOKEN", "dummy-github-token")
    monkeypatch.setenv("GH_ENTERPRISE_TOKEN", "dummy-enterprise-token")
    monkeypatch.setenv("GH_NO_UPDATE_NOTIFIER", "1")

    class LoopbackGitHubApi(release_assets.GitHubApi):
        def request(
            self,
            method: str,
            endpoint: str,
            *,
            data: bytes | None = None,
            headers: tuple[str, ...] = (),
        ) -> bytes:
            parsed = urlsplit(endpoint)
            local_endpoint = (
                f"http://127.0.0.1:{server.server_port}/{parsed.path.lstrip('/')}"
            )
            if parsed.query:
                local_endpoint += f"?{parsed.query}"
            return super().request(method, local_endpoint, data=data, headers=headers)

    thread.start()
    try:
        release_assets._upload(
            LoopbackGitHubApi(),
            release_assets.Identity("HisQu/buildben", TAG, COMMIT),
            22,
            "binary-payload.bin",
            payload,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert received_headers == [([str(len(payload))], None)]
    assert received == [payload]
