"""Stateful contract tests for standard GitHub wheel/sdist publication."""

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


def _packages(directory: Path) -> list[str]:
    name = PROJECT["name"]
    version = PROJECT["version"]
    wheel_name = f"{name}-{version}-py3-none-any.whl"
    metadata_path = f"{name.replace('-', '_')}-{version}.dist-info/METADATA"
    with zipfile.ZipFile(directory / wheel_name, "w") as wheel:
        wheel.writestr(
            metadata_path,
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
        )
    sdist_name = f"{name}-{version}.tar.gz"
    with tarfile.open(directory / sdist_name, "w:gz") as archive:
        content = (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n".encode()
        )
        item = tarfile.TarInfo(f"{name}-{version}/PKG-INFO")
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))
    return [wheel_name, sdist_name]


def _prepared(directory: Path) -> tuple[StatefulReleaseApi, list[str]]:
    directory.mkdir()
    names = _packages(directory)
    api = StatefulReleaseApi()
    notes = directory / "release-notes.md"
    notes.write_text("Release notes\n", encoding="utf-8")
    release_assets.prepare(api, "HisQu/buildben", TAG, COMMIT, notes)
    return api, names


def test_draft_publishes_exactly_one_validated_wheel_and_sdist(tmp_path: Path) -> None:
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


def test_upload_rejects_mismatched_package_metadata_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    with zipfile.ZipFile(payload / names[0], "w") as wheel:
        wheel.writestr(
            f"{PROJECT['name']}-{VERSION}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: other-project\nVersion: {VERSION}\n\n",
        )

    with pytest.raises(release_assets.ReleaseError, match="does not match"):
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

    with pytest.raises(release_assets.ReleaseError, match="exactly one wheel"):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.release is not None and api.release["draft"] is True


def test_upload_rejects_partial_and_unsafe_sdist_before_mutating_draft(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)

    with pytest.raises(release_assets.ReleaseError, match="exactly one wheel"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names[:1])
    unsafe = payload / names[1]
    with tarfile.open(unsafe, "w:gz") as archive:
        content = b"escape"
        item = tarfile.TarInfo("../escape/PKG-INFO")
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))
    with pytest.raises(release_assets.ReleaseError, match="Unsafe archive member"):
        release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.assets == {}
    assert api.release is not None and api.release["draft"] is True


def test_finalize_rejects_unexpected_asset_without_publishing(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    api.assets[99] = ("unowned.bin", b"unowned")

    with pytest.raises(
        release_assets.ReleaseError, match="exactly one wheel and one source archive"
    ):
        release_assets.finalize(api, "HisQu/buildben", TAG, COMMIT)

    assert api.release is not None and api.release["draft"] is True
    assert api.assets[99] == ("unowned.bin", b"unowned")


def test_upload_replaces_only_same_named_draft_assets(tmp_path: Path) -> None:
    payload = tmp_path / "packages"
    api, names = _prepared(payload)
    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)
    wheel = payload / names[0]
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"{PROJECT['name']}-{VERSION}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {PROJECT['name']}\nVersion: {VERSION}\n\nupdated",
        )

    release_assets.upload(api, "HisQu/buildben", TAG, COMMIT, payload, names)

    assert api.deleted == [names[0]]
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
