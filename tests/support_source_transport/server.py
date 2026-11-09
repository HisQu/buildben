"""Loopback GitHub source bytes for the real installer transport smoke."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


class SourceFixture:
    """Serve staged release assets and captured/moving main-source identities."""

    def __init__(
        self,
        *,
        assets_directory: Path,
        main_installer: Path,
        main_installer_path: str,
        main_archive: Path,
        repository: str,
        commit: str,
        tag: str,
        moving_commit: str | None = None,
        moving_archive: bytes | None = None,
    ) -> None:
        self.assets = {
            path.name: path.read_bytes()
            for path in assets_directory.iterdir()
            if path.is_file()
        }
        self.main_installer = main_installer.read_bytes()
        self.main_archive = main_archive.read_bytes()
        self.repository = repository.removesuffix(".git")
        self.commit = commit
        self.tag = tag
        self.moving_commit = moving_commit
        self.moving_archive = moving_archive
        self.main_resolution_count = 0
        self.main_archive_requests: list[str] = []
        self._main_lock = threading.Lock()
        self.closed = False
        self._release: bytes | None = None
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                path = urlsplit(self.path).path
                if path.endswith("/releases/latest") or path.endswith(
                    f"/releases/tags/{fixture.tag}"
                ):
                    body = fixture._release
                elif path.endswith("/commits/main"):
                    with fixture._main_lock:
                        fixture.main_resolution_count += 1
                        resolved = (
                            fixture.commit
                            if fixture.main_resolution_count == 1
                            or fixture.moving_commit is None
                            else fixture.moving_commit
                        )
                    body = json.dumps({"sha": resolved}).encode()
                elif path.endswith(f"/tarball/{fixture.commit}"):
                    fixture.main_archive_requests.append(fixture.commit)
                    body = fixture.main_archive
                elif fixture.moving_commit and path.endswith(
                    f"/tarball/{fixture.moving_commit}"
                ):
                    fixture.main_archive_requests.append(fixture.moving_commit)
                    body = fixture.moving_archive
                elif path == "/main-installer.py":
                    body = fixture.main_installer
                elif path.startswith("/assets/"):
                    body = fixture.assets.get(unquote(path.removeprefix("/assets/")))
                else:
                    body = None
                if body is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.api_url = "https://api.github.com"
        owner_repo = self.repository.removeprefix("https://github.com/")
        assets = [
            {
                "name": name,
                "size": len(self.assets[name]),
                "browser_download_url": (
                    f"https://github.com/{owner_repo}/releases/download/"
                    f"{self.tag}/{quote(name)}"
                ),
            }
            for name in sorted(self.assets)
        ]
        self._release = json.dumps(
            {
                "tag_name": self.tag,
                "draft": False,
                "prerelease": False,
                "assets": assets,
            }
        ).encode()
        installer_path = main_installer_path.lstrip("/")
        contents_url = (
            f"https://api.github.com/repos/{owner_repo}/contents/"
            f"{installer_path}?ref={self.commit}"
        )
        raw_url = (
            f"https://raw.githubusercontent.com/{owner_repo}/{self.commit}/"
            f"{installer_path}"
        )
        self.url_map = {
            f"https://api.github.com/repos/{owner_repo}/releases/latest": f"{self.base_url}/api/repos/{owner_repo}/releases/latest",
            f"https://api.github.com/repos/{owner_repo}/releases/tags/{self.tag}": f"{self.base_url}/api/repos/{owner_repo}/releases/tags/{self.tag}",
            f"https://api.github.com/repos/{owner_repo}/commits/main": f"{self.base_url}/api/repos/{owner_repo}/commits/main",
            f"https://api.github.com/repos/{owner_repo}/tarball/{self.commit}": f"{self.base_url}/api/repos/{owner_repo}/tarball/{self.commit}",
            contents_url: f"{self.base_url}/main-installer.py",
            raw_url: f"{self.base_url}/main-installer.py",
        }
        if self.moving_commit is not None:
            self.url_map[
                f"https://api.github.com/repos/{owner_repo}/tarball/"
                f"{self.moving_commit}"
            ] = f"{self.base_url}/api/repos/{owner_repo}/tarball/{self.moving_commit}"
        for asset in self.assets:
            self.url_map[
                f"https://github.com/{owner_repo}/releases/download/"
                f"{self.tag}/{quote(asset)}"
            ] = f"{self.base_url}/assets/{quote(asset)}"

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
