"""Tests for native release staging and publication."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from support_release import (
    copy_release_tooling,
    write_package_pair,
    write_release_fixture,
)

from buildben_dev.packaging import release_assets, release_manifest

COMMIT = "a" * 40
TAG_OBJECT = "b" * 40
PROJECT = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
VERSION = PROJECT["version"]
TAG = f"v{VERSION}"


class StatefulReleaseApi:
    """Model a tag, one draft, and GitHub's stored release assets."""

    def __init__(self) -> None:
        self.commit = COMMIT
        self.release: dict[str, object] | None = None
        self.deleted: list[str] = []
        self.assets: dict[int, tuple[str, bytes]] = {}
        self.next_asset = 1
        self.created = 0
        self.fail_upload_name: str | None = None

    def _body(self) -> dict[str, object]:
        assert self.release is not None
        assets = [
            {
                "id": asset_id,
                "name": name,
                "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
            }
            for asset_id, (name, data) in self.assets.items()
        ]
        return {**self.release, "assets": assets}

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
        if path.endswith(f"/git/ref/tags/{TAG}"):
            return json.dumps({"object": {"type": "tag", "sha": TAG_OBJECT}}).encode()
        if path.endswith(f"/git/tags/{TAG_OBJECT}"):
            return json.dumps(
                {"object": {"type": "commit", "sha": self.commit}}
            ).encode()
        if path.endswith("/releases") and method == "GET" and "page=1" in parsed.query:
            return json.dumps([self._body()] if self.release else []).encode()
        if path.endswith("/releases") and method == "POST":
            payload = json.loads(data or b"{}")
            self.release = {"id": 22, **payload}
            self.created += 1
            return json.dumps(self._body()).encode()
        if (
            ".github" not in path
            and parsed.netloc == "uploads.github.com"
            and method == "POST"
        ):
            name = parse_qs(parsed.query)["name"][0]
            if name == self.fail_upload_name:
                raise release_assets.ReleaseError("Injected upload failure.")
            asset_id = self.next_asset
            self.next_asset += 1
            self.assets[asset_id] = (name, data or b"")
            return json.dumps({"id": asset_id, "name": name}).encode()
        if "/releases/assets/" in path:
            asset_id = int(path.rsplit("/", 1)[1])
            if method == "GET":
                return self.assets[asset_id][1]
            if method == "DELETE":
                self.deleted.append(self.assets[asset_id][0])
                del self.assets[asset_id]
                return b"{}"
        if path.endswith("/releases/22") and method == "PATCH":
            assert self.release is not None
            self.release.update(json.loads(data or b"{}"))
            return json.dumps(self._body()).encode()
        raise AssertionError(f"Unexpected API request: {method} {endpoint}")

    def watch_ci(self, repository: str, run_id: int) -> int:
        return 0


def _refresh_checksums(directory: Path, names: list[str]) -> None:
    payload = {
        name: (directory / name).read_bytes()
        for name in names
        if name != release_manifest.CHECKSUMS_NAME
    }
    content = release_manifest.checksum_bytes(payload, app_id=PROJECT["name"])
    (directory / release_manifest.CHECKSUMS_NAME).write_bytes(content)


def _prepared(directory: Path) -> tuple[StatefulReleaseApi, list[str]]:
    directory.mkdir()
    names = write_release_fixture(
        directory,
        app_id=PROJECT["name"],
        distribution=PROJECT["name"],
        version=VERSION,
        commit=COMMIT,
    )
    api = StatefulReleaseApi()
    notes = directory.parent / f"{directory.name}-release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    return api, names


def test_draft_publishes_exact_verified_native_assets(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)

    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.created == 1
    assert {name for name, _ in api.assets.values()} == set(names)
    assert api.release is not None and api.release["draft"] is False
    assert api.deleted == []


def test_partial_upload_failure_keeps_draft_reusable(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    api.fail_upload_name = names[1]

    with pytest.raises(release_assets.ReleaseError, match="Injected upload failure"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.release is not None and api.release["draft"] is True
    assert {name for name, _ in api.assets.values()} == {names[0]}
    api.fail_upload_name = None
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.release is not None and api.release["draft"] is False
    assert {name for name, _ in api.assets.values()} == set(names)


def test_upload_rejects_corrupt_checksum_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "release"
    api, names = _prepared(payload)
    (payload / release_manifest.CHECKSUMS_NAME).write_bytes(b"corrupt\n")

    with pytest.raises(release_assets.ReleaseError):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_upload_rejects_changed_remote_tag_commit(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    api.commit = "c" * 40

    with pytest.raises(release_assets.ReleaseError, match="not"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_upload_refuses_published_release_without_deleting_assets(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    before = dict(api.assets)
    assert api.release is not None
    api.release["draft"] = False

    with pytest.raises(release_assets.ReleaseError, match="published"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == before


def test_finalize_rejects_missing_asset_without_publishing(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    asset_id = next(
        asset_id for asset_id, (name, _) in api.assets.items() if name == names[1]
    )
    del api.assets[asset_id]

    with pytest.raises(release_assets.ReleaseError):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.release is not None and api.release["draft"] is True


def test_upload_rejects_incomplete_or_malformed_native_inventory(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "release"
    api, names = _prepared(payload)

    with pytest.raises(release_assets.ReleaseError):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names[:1])
    (payload / release_manifest.CHECKSUMS_NAME).write_text(
        "malformed\n", encoding="ascii"
    )
    with pytest.raises(release_assets.ReleaseError):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_finalize_rejects_unexpected_asset_without_publishing(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    api.assets[99] = ("unowned.bin", b"unowned")

    with pytest.raises(release_assets.ReleaseError):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.release is not None and api.release["draft"] is True
    assert api.assets[99] == ("unowned.bin", b"unowned")


def test_upload_replaces_only_same_named_draft_assets(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    setup = payload / names[1]
    setup.write_bytes(b"updated native executable")
    _refresh_checksums(payload, names)

    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert set(api.deleted) == {names[1], release_manifest.CHECKSUMS_NAME}
    assert {name for name, _ in api.assets.values()} == set(names)
    assert api.release is not None and api.release["draft"] is True


def test_prepare_reuses_matching_draft_from_release_listing(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    payload.mkdir()
    notes = payload / "notes.md"
    notes.write_text("Notes\n", encoding="utf-8")
    api, _ = _prepared(tmp_path / "existing")

    result = release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)

    assert result["id"] == 22
    assert api.created == 1


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


def test_release_checksum_rejects_corrupt_native_payload_before_publication(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "release"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    setup_name = next(name for name in names if name.endswith("setup-linux-x86_64"))
    asset_id = next(key for key, (name, _) in api.assets.items() if name == setup_name)
    api.assets[asset_id] = (setup_name, b"corrupt replacement")
    with pytest.raises(release_assets.ReleaseError):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)
    assert api.release is not None and api.release["draft"] is True


@pytest.mark.parametrize(
    "corruption", ("digest", "duplicate", "unexpected", "malformed")
)
def test_checksum_contract_rejects_invalid_inventory(
    tmp_path: Path, corruption: str
) -> None:
    payload = tmp_path / "release"
    _, names = _prepared(payload)
    path = payload / release_manifest.CHECKSUMS_NAME
    lines = path.read_text(encoding="ascii").splitlines()
    if corruption == "digest":
        lines[0] = "0" * 64 + lines[0][64:]
    elif corruption == "duplicate":
        lines.append(lines[0])
    elif corruption == "unexpected":
        lines.append("a" * 64 + "  unexpected.exe")
    else:
        lines[0] = "malformed"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    with pytest.raises(ValueError):
        release_manifest.validate_checksums(
            {name: (payload / name).read_bytes() for name in names},
            app_id=PROJECT["name"],
        )


def test_manual_pypi_uses_separate_wheel_and_sdist_inputs(
    tmp_path: Path,
) -> None:
    release_directory = tmp_path / "release"
    api, names = _prepared(release_directory)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, release_directory, names)
    assert api.release is not None
    api.release["draft"] = False
    metadata = tmp_path / "github-release.json"
    metadata.write_text(json.dumps(api._body()), encoding="utf-8")
    package_directory = tmp_path / "pypi"
    package_directory.mkdir()
    package_names = write_package_pair(
        package_directory, distribution=PROJECT["name"], version=VERSION
    )
    (package_directory / ".gitignore").write_text("*\n", encoding="utf-8")
    assert release_assets.verify_pypi_packages(
        api,
        "HisQu/buildben",
        TAG,
        COMMIT,
        metadata=metadata,
        directory=package_directory,
    ) == tuple(sorted(package_names))
    (package_directory / "unexpected.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(
        release_assets.ReleaseError, match="exactly one wheel and one sdist"
    ):
        release_assets.verify_pypi_packages(
            api,
            "HisQu/buildben",
            TAG,
            COMMIT,
            metadata=metadata,
            directory=package_directory,
        )
    assert not set(package_names).intersection(
        release_manifest.native_asset_names(PROJECT["name"])
    )


@pytest.mark.parametrize("scaffold", (False, True))
def test_stage_and_verify_cli_check_actual_release_without_rewriting(
    tmp_path: Path,
    scaffold: bool,
) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    module = copy_release_tooling(
        project,
        Path(__file__).resolve().parents[1],
        scaffold=scaffold,
        package="fixture_dev",
    )
    (project / "pyproject.toml").write_text(
        '[project]\nname = "fixture-release"\nversion = "1.0.0"\n'
        '[tool.apprc.distribution]\napp-id = "separate-app-id"\n',
        encoding="utf-8",
    )
    payload = project / "release"
    payload.mkdir()
    names = write_release_fixture(
        payload,
        app_id="separate-app-id",
        distribution="fixture-release",
        version="1.0.0",
        commit=COMMIT,
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(project / "src")
    common = [
        "--repository",
        "owner/project",
        "--tag",
        "v1.0.0",
        "--commit",
        COMMIT,
        "--directory",
        str(payload),
    ]
    setup_names = [name for name in names if name != release_manifest.CHECKSUMS_NAME]
    (payload / release_manifest.CHECKSUMS_NAME).unlink()
    staged = subprocess.run(
        [sys.executable, "-m", module, "stage", *common, "--files", *setup_names],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert staged.returncode == 0, staged.stderr
    assert set(staged.stdout.splitlines()) == set(names)
    verified = subprocess.run(
        [sys.executable, "-m", module, "verify", *common],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert set(verified.stdout.splitlines()) == set(names)
    changed = payload / setup_names[0]
    changed.write_bytes(b"unexpected release payload")
    rejected = subprocess.run(
        [sys.executable, "-m", module, "verify", *common],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rejected.returncode != 0


def test_native_checksum_inventory_accepts_only_final_setup_assets(
    tmp_path: Path,
) -> None:
    """The release inventory contains exactly the two setup files and checksums."""
    app_id = "example-app"
    setups = {
        name: f"setup: {name}".encode()
        for name in release_manifest.native_asset_names(app_id)
        if name != release_manifest.CHECKSUMS_NAME
    }
    for name, content in setups.items():
        (tmp_path / name).write_bytes(content)
    (tmp_path / release_manifest.CHECKSUMS_NAME).write_bytes(
        release_manifest.checksum_bytes(setups, app_id=app_id)
    )
    assert release_manifest.validate_directory(
        tmp_path, app_id=app_id, exact=True
    ) == release_manifest.native_asset_names(app_id)

    changed = tmp_path / next(iter(setups))
    changed.write_bytes(b"tampered setup")
    with pytest.raises(ValueError, match="SHA-256"):
        release_manifest.validate_directory(tmp_path, app_id=app_id, exact=True)
    assert changed.read_bytes() == b"tampered setup"
