"""Consumer tests for the canonical BuildBen source installers."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

import pytest

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "src/buildben_dev/distribution"


def _release_json(source: Path, asset_url: str) -> str:
    version = source.name.removesuffix(".tar.gz").rsplit("-", 1)[-1]
    return json.dumps(
        {
            "tag_name": f"v{version}",
            "draft": False,
            "prerelease": False,
            "assets": [{"name": source.name, "browser_download_url": asset_url}],
        }
    )


def _write_sdist(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(f"buildben-0.10.3/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _install_smoke_fixture(
    tmp_path: Path,
    source: Path,
    client: str,
    *,
    release_overrides: dict[str, object] | None = None,
    latest_release_overrides: dict[str, object] | None = None,
):
    source = source.resolve(strict=True)
    version = source.name.removesuffix(".tar.gz").rsplit("-", 1)[-1]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path != f"/assets/{quote(source.name)}":
                self.send_error(404)
                return
            data = source.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    asset_url = f"http://127.0.0.1:{server.server_port}/assets/{quote(source.name)}"
    release_value = json.loads(_release_json(source, asset_url))
    if release_overrides is not None:
        release_value.update(release_overrides)
    latest_value = dict(release_value)
    if latest_release_overrides is not None:
        latest_value.update(latest_release_overrides)
    release_json = json.dumps(release_value)
    latest_release_json = json.dumps(latest_value)

    shim_dir = tmp_path / "transport shims"
    shim_dir.mkdir()
    if os.name == "nt":
        module = shim_dir / "InstallerHttpFixture"
        module.mkdir()
        (module / "InstallerHttpFixture.psm1").write_text(
            "function Invoke-RestMethod { param([string]$Uri); "
            "if ($Uri -like 'https://api.github.com/repos/HisQu/buildben/releases/*') { "
            "$releasePath = $env:INSTALLER_SMOKE_RELEASE_JSON; "
            "if ($Uri -like '*/latest') { $releasePath = $env:INSTALLER_SMOKE_LATEST_RELEASE_JSON }; "
            "return (Get-Content -Raw -LiteralPath $releasePath | ConvertFrom-Json) }; "
            "Microsoft.PowerShell.Utility\\Invoke-RestMethod -Uri $Uri }\n"
            "function Invoke-WebRequest { param([string]$Uri, [string]$OutFile); "
            "Microsoft.PowerShell.Utility\\Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $OutFile }\n"
            "Export-ModuleMember -Function Invoke-RestMethod, Invoke-WebRequest\n",
            encoding="utf-8",
        )
        (module / "InstallerHttpFixture.psd1").write_text(
            "@{ RootModule='InstallerHttpFixture.psm1'; ModuleVersion='1.0'; "
            "GUID='d9b76c0c-a7f9-4e5b-a078-08ab11f7f9aa'; "
            "FunctionsToExport=@('Invoke-RestMethod','Invoke-WebRequest') }\n",
            encoding="utf-8",
        )
        gh_shim = shim_dir / "gh_shim.py"
        gh_shim.write_text(
            "import os, pathlib, subprocess, sys\n"
            "pathlib.Path(os.environ['INSTALLER_SMOKE_GH_CALLED']).write_text('called')\n"
            "if os.environ.get('INSTALLER_SMOKE_GH_FAIL') == '1': raise SystemExit(88)\n"
            "args=sys.argv[1:]\n"
            "if args[:1] == ['api']:\n"
            " release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if args[1].endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            " print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "if args[:2] == ['release','download']:\n"
            " name=args[args.index('--pattern')+1]; dest=pathlib.Path(args[args.index('--dir')+1]); dest.mkdir(parents=True,exist_ok=True)\n"
            " output=dest/name\n"
            " subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','Invoke-WebRequest -Uri $env:INSTALLER_SMOKE_ASSET_URL -OutFile $env:INSTALLER_SMOKE_GH_OUTPUT'],env=os.environ | {'INSTALLER_SMOKE_GH_OUTPUT':str(output)},check=True)\n"
            " raise SystemExit(0)\n"
            "raise SystemExit(87)\n",
            encoding="utf-8",
        )
        (shim_dir / "gh.cmd").write_text(
            "@echo off\n"
            f'"{sys.executable}" "%~dp0gh_shim.py" %*\n'
            "exit /b %errorlevel%\n",
            encoding="utf-8",
        )
    else:
        curl_shim = shim_dir / "curl"
        curl_shim.write_text(
            "#!/usr/bin/env python3\n"
            "import os, pathlib, subprocess, sys\n"
            "args=sys.argv[1:]\n"
            "url=next((arg for arg in args if arg.startswith(('http://','https://'))), '')\n"
            "if url.startswith('https://api.github.com/repos/HisQu/buildben/releases/'):\n"
            " release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if url.endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            " print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "real=os.environ['INSTALLER_SMOKE_REAL_CURL']\n"
            "raise SystemExit(subprocess.run([real,*args],check=False).returncode)\n",
            encoding="utf-8",
        )
        curl_shim.chmod(0o755)
        gh_shim = shim_dir / "gh"
        gh_shim.write_text(
            "#!/usr/bin/env python3\n"
            "import os, pathlib, subprocess, sys\n"
            "pathlib.Path(os.environ['INSTALLER_SMOKE_GH_CALLED']).write_text('called')\n"
            "if os.environ.get('INSTALLER_SMOKE_GH_FAIL') == '1': raise SystemExit(88)\n"
            "args=sys.argv[1:]\n"
            "if args[:1] == ['api']:\n"
            " release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if args[1].endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            " print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "if args[:2] == ['release','download']:\n"
            " name=args[args.index('--pattern')+1]; dest=pathlib.Path(args[args.index('--dir')+1]); dest.mkdir(parents=True,exist_ok=True)\n"
            " subprocess.run([os.environ['INSTALLER_SMOKE_REAL_CURL'],'-fsSL',os.environ['INSTALLER_SMOKE_ASSET_URL'],'-o',str(dest/name)],check=True)\n"
            " raise SystemExit(0)\n"
            "raise SystemExit(87)\n",
            encoding="utf-8",
        )
        gh_shim.chmod(0o755)

    isolated = tmp_path / "isolated home with spaces"
    config = isolated / "config"
    data = isolated / "data"
    cache = isolated / "cache"
    tool_dir = isolated / "uv tools"
    tool_bin = isolated / "uv bin"
    uv_cache = isolated / "uv cache"
    for directory in (config, data, cache, tool_dir, tool_bin, uv_cache):
        directory.mkdir(parents=True, exist_ok=True)
    config_sentinel = config / "sentinel"
    data_sentinel = data / "sentinel"
    config_sentinel.write_text("keep config", encoding="utf-8")
    data_sentinel.write_text("keep data", encoding="utf-8")
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("The source-installer tests require the runner's uv executable.")
    gh_called = tmp_path / "gh-called"
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    environment.update(
        {
            "HOME": str(isolated),
            "XDG_CONFIG_HOME": str(config),
            "XDG_DATA_HOME": str(data),
            "XDG_CACHE_HOME": str(cache),
            "UV_TOOL_DIR": str(tool_dir),
            "UV_TOOL_BIN_DIR": str(tool_bin),
            "UV_CACHE_DIR": str(uv_cache),
            "INSTALLER_SMOKE_SOURCE": str(source),
            "INSTALLER_SMOKE_CLIENT": client,
            "INSTALLER_SMOKE_RELEASE_JSON": str(tmp_path / "release.json"),
            "INSTALLER_SMOKE_LATEST_RELEASE_JSON": str(
                tmp_path / "latest-release.json"
            ),
            "INSTALLER_SMOKE_ASSET_URL": asset_url,
            "INSTALLER_SMOKE_GH_CALLED": str(gh_called),
            "INSTALLER_SMOKE_GH_FAIL": "1" if client == "curl" else "0",
        }
    )
    (tmp_path / "release.json").write_text(release_json, encoding="utf-8")
    (tmp_path / "latest-release.json").write_text(latest_release_json, encoding="utf-8")
    if os.name == "nt":
        environment["PSMODULEPATH"] = os.pathsep.join(
            [str(shim_dir), environment.get("PSMODULEPATH", "")]
        )
    else:
        real_curl = shutil.which("curl")
        if real_curl is None:
            pytest.fail(
                "The Unix source-install smoke requires curl for its loopback fixture."
            )
        environment["INSTALLER_SMOKE_REAL_CURL"] = real_curl
    environment["PATH"] = os.pathsep.join(
        [str(shim_dir), str(tool_bin), environment.get("PATH", "")]
    )
    return (
        server,
        thread,
        environment,
        uv,
        tool_dir,
        tool_bin,
        config_sentinel,
        data_sentinel,
        version,
        gh_called,
    )


def _installer_command(uv: str, *arguments: str) -> list[str]:
    if os.name == "nt":
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(INSTALLER_DIR / "install-windows.ps1"),
            "--yes",
            "--skip-config",
            "--uv",
            uv,
            *arguments,
        ]
    return [
        "bash",
        str(INSTALLER_DIR / "install-linux-macos.sh"),
        "--yes",
        "--skip-config",
        "--uv",
        uv,
        *arguments,
    ]


@pytest.mark.parametrize(
    "arguments", [["--git"], ["--dev", "."], ["--github-client", "automatic"]]
)
def test_rejected_options_do_not_run_uv(arguments: list[str], tmp_path: Path) -> None:
    if os.name == "nt":
        uv = tmp_path / "uv.cmd"
        uv.write_text("@echo off\necho invoked\n", encoding="utf-8")
        env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(INSTALLER_DIR / "install-windows.ps1"),
            *arguments,
        ]
    else:
        uv = tmp_path / "uv"
        uv.write_text("#!/bin/sh\nprintf invoked\n", encoding="utf-8")
        uv.chmod(0o755)
        env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
        command = ["bash", str(INSTALLER_DIR / "install-linux-macos.sh"), *arguments]
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, env=env
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "invoked" not in output, output


def test_source_install_smoke(tmp_path: Path) -> None:
    """Install an actual sdist through the production script and test transport shim."""
    source_value = os.environ.get("INSTALLER_SMOKE_SOURCE")
    if not source_value:
        pytest.skip("INSTALLER_SMOKE_SOURCE is unset; source-install smoke is opt-in.")
    source = Path(source_value)
    if not source.is_absolute() or not source.is_file():
        pytest.fail(
            "INSTALLER_SMOKE_SOURCE must name an absolute path to a built sdist."
        )
    client = os.environ.get("INSTALLER_SMOKE_CLIENT", "curl")
    if client not in {"curl", "gh"}:
        pytest.fail("INSTALLER_SMOKE_CLIENT must be curl or gh.")

    fixture = _install_smoke_fixture(tmp_path, source, client)
    (
        server,
        thread,
        environment,
        uv,
        tool_dir,
        tool_bin,
        config_sentinel,
        data_sentinel,
        version,
        gh_called,
    ) = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", client),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=900,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        if os.name == "nt":
            tool_python = tool_dir / "buildben" / "Scripts" / "python.exe"
            executables = [tool_bin / "buildben.exe", tool_bin / "bube.exe"]
        else:
            tool_python = tool_dir / "buildben" / "bin" / "python"
            executables = [tool_bin / "buildben", tool_bin / "bube"]
        for executable in executables:
            help_result = subprocess.run(
                [str(executable), "--help"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            assert help_result.returncode == 0, help_result.stdout + help_result.stderr
        smoke_result = subprocess.run(
            [
                str(tool_python),
                "-m",
                "buildben_dev.packaging.install_smoke",
                "--expected-version",
                version,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        assert smoke_result.returncode == 0, smoke_result.stdout + smoke_result.stderr
        assert gh_called.exists() is (client == "gh")
        origin = subprocess.run(
            [str(tool_python), "-c", "import buildben; print(buildben.__file__)"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
        assert Path(origin).resolve().is_relative_to((tool_dir / "buildben").resolve())
        assert config_sentinel.read_text(encoding="utf-8") == "keep config"
        assert data_sentinel.read_text(encoding="utf-8") == "keep data"
        uninstall = subprocess.run(
            [uv, "tool", "uninstall", "buildben"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
        assert config_sentinel.read_text(encoding="utf-8") == "keep config"
        assert data_sentinel.read_text(encoding="utf-8") == "keep data"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("release_overrides", [{"draft": True}, {"prerelease": True}])
def test_latest_release_rejects_draft_and_prerelease(
    tmp_path: Path, release_overrides: dict[str, object]
) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    source.write_bytes(b"not a source archive")
    fixture = _install_smoke_fixture(
        tmp_path, source, "curl", release_overrides=release_overrides
    )
    server, thread, environment, uv, tool_dir, _, _, _, _, _ = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "curl"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "not a published stable release" in output, output
        assert list(tool_dir.iterdir()) == []
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(
    "assets",
    [
        [],
        [
            {
                "name": "buildben-0.10.3.tar.gz",
                "browser_download_url": "http://fixture/one",
            },
            {
                "name": "buildben-0.10.3.tar.gz",
                "browser_download_url": "http://fixture/two",
            },
        ],
    ],
)
def test_release_requires_one_matching_source_archive(
    tmp_path: Path, assets: list[dict[str, str]]
) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    source.write_bytes(b"must not download")
    fixture = _install_smoke_fixture(
        tmp_path, source, "curl", release_overrides={"assets": assets}
    )
    server, thread, environment, uv, tool_dir, _, _, _, _, _ = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "curl"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Expected exactly one matching source distribution" in output, output
        assert list(tool_dir.iterdir()) == []
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(
    ("members", "error_stage"),
    [
        (
            {
                "pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.10.3"\n',
            },
            "pyproject.toml and uv.lock",
        ),
        (
            {
                "pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.10.2"\n',
                "uv.lock": b"version = 1\n",
            },
            "Source project metadata does not match",
        ),
        (
            {
                "pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.10.3"\n',
                "uv.lock": b"not a lockfile\n",
            },
            "export",
        ),
    ],
)
def test_invalid_sdist_metadata_or_lock_never_installs(
    tmp_path: Path, members: dict[str, bytes], error_stage: str
) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    _write_sdist(source, members)
    fixture = _install_smoke_fixture(tmp_path, source, "curl")
    server, thread, environment, uv, tool_dir, _, _, _, _, _ = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "curl"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert error_stage in output, output
        assert list(tool_dir.iterdir()) == []
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_source_installer_rejects_unsafe_tar_member(tmp_path: Path) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    _write_sdist(
        source,
        {
            "pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.10.3"\n',
            "uv.lock": b"version = 1\n",
            "../../outside": b"unsafe",
        },
    )
    fixture = _install_smoke_fixture(tmp_path, source, "curl")
    server, thread, environment, uv, tool_dir, _, _, _, _, _ = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "curl"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Source archive contains an unsafe path" in output, output
        assert list(tool_dir.iterdir()) == []
        assert not (tmp_path / "outside").exists()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_explicit_version_uses_tag_endpoint(tmp_path: Path) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    source.write_bytes(b"not a source archive")
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        "curl",
        latest_release_overrides={"tag_name": "v0.10.2"},
    )
    server, thread, environment, uv, tool_dir, _, _, _, _, _ = fixture
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "curl", "--version", "0.10.3"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "not a gzip file" in output, output
        assert list(tool_dir.iterdir()) == []
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_gh_transport_failure_does_not_fall_back_to_public_transport(
    tmp_path: Path,
) -> None:
    source = tmp_path / "buildben-0.10.3.tar.gz"
    source.write_bytes(b"not downloaded after API failure")
    fixture = _install_smoke_fixture(tmp_path, source, "gh")
    server, thread, environment, uv, tool_dir, _, _, _, _, gh_called = fixture
    environment["INSTALLER_SMOKE_GH_FAIL"] = "1"
    thread.start()
    try:
        result = subprocess.run(
            _installer_command(uv, "--github-client", "gh"),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        expected_error = (
            "source installation failed"
            if os.name == "nt"
            else "returned non-zero exit status 88"
        )
        assert expected_error in output, output
        assert gh_called.is_file()
        assert list(tool_dir.iterdir()) == []
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
