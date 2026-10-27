"""Consumer tests for canonical and rendered BuildBen source installers."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import quote

import pytest

from buildben.init_proj import _run as render_project

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


def _write_sdist(
    path: Path, members: dict[str, bytes], distribution: str = "buildben"
) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(f"{distribution}-0.10.3/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _archive_bytes(members: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()


def _inherit_active_venv(tmp_path: Path, environment: dict[str, str]) -> Path:
    """Run installer smokes with an active virtual environment in the parent."""
    venv = tmp_path / "active project venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True
    )
    environment["VIRTUAL_ENV"] = str(venv)
    scripts = venv / ("Scripts" if os.name == "nt" else "bin")
    environment["PATH"] = os.pathsep.join([str(scripts), environment.get("PATH", "")])
    return venv


@pytest.fixture(params=["canonical", "rendered"])
def windows_installer_target(
    request: pytest.FixtureRequest, tmp_path: Path
) -> tuple[Path, str, str]:
    """Select the canonical installer or one emitted by the real scaffolder."""
    if request.param == "canonical":
        return INSTALLER_DIR / "install-windows.ps1", "HisQu/buildben", "buildben"
    name = "scope_fixture"
    root = tmp_path / "rendered project"
    render_project(
        argparse.Namespace(
            name=name,
            target_dir=str(root),
            git_init=False,
            github_user="fixture-owner",
        )
    )
    project_root = root / name
    project_data = tomllib.loads(
        (project_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    return (
        project_root / "src" / f"{name}_dev" / "distribution" / "install-windows.ps1",
        f"fixture-owner/{name}",
        project_data["project"]["name"],
    )


def _install_smoke_fixture(
    tmp_path: Path,
    source: Path,
    client: str,
    *,
    release_overrides: dict[str, object] | None = None,
    latest_release_overrides: dict[str, object] | None = None,
    repository: str = "HisQu/buildben",
    source_mode: str = "release",
    main_commit: str | None = None,
    main_commit_response: bytes | None = None,
    main_archive_bytes: bytes | None = None,
    main_commit_status: int = 200,
    main_archive_status: int = 200,
    second_main_source: Path | None = None,
    installer_source: Path | None = None,
    installer_repository: str = "HisQu/buildben",
):
    source = source.resolve(strict=True)
    installer_source = installer_source or INSTALLER_DIR / "install-windows.ps1"
    installer_module = installer_source.parent.parent.name
    if source_mode == "main":
        if main_commit is None or not re.fullmatch(r"[0-9a-f]{40}", main_commit):
            pytest.fail("Main smoke requires a full lowercase 40-character commit SHA.")
        with tarfile.open(source, "r:gz") as archive:
            pyproject_member = next(
                member
                for member in archive.getmembers()
                if PurePosixPath(member.name).name == "pyproject.toml"
            )
            pyproject_file = archive.extractfile(pyproject_member)
            assert pyproject_file is not None
            project_data = tomllib.loads(pyproject_file.read().decode())
        version = project_data["project"]["version"]
    else:
        version = source.name.removesuffix(".tar.gz").rsplit("-", 1)[-1]
    second_commit = "b" * 40
    commit_response = (
        json.dumps({"sha": main_commit}).encode()
        if main_commit_response is None
        else main_commit_response
    )
    if second_main_source is None:
        second_main_source = tmp_path / "moving-main.tar.gz"
        _write_sdist(
            second_main_source,
            {
                "pyproject.toml": b'[project]\nname = "not-buildben"\nversion = "99.0.0"\n',
                "uv.lock": b"version = 1\n",
            },
        )

    class Handler(BaseHTTPRequestHandler):
        commit_requests = 0

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, data: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/installer":
                self._send(
                    installer_source.read_bytes(),
                    "text/plain",
                )
                return
            if self.path == f"/assets/{quote(source.name)}":
                self._send(source.read_bytes(), "application/gzip")
                return
            if self.path == f"/api/repos/{repository}/commits/main":
                type(self).commit_requests += 1
                self._send(
                    commit_response
                    if type(self).commit_requests == 1
                    else json.dumps({"sha": second_commit}).encode(),
                    "application/json",
                    main_commit_status,
                )
                return
            if self.path == f"/api/repos/{repository}/tarball/{main_commit}":
                self._send(
                    source.read_bytes()
                    if main_archive_bytes is None
                    else main_archive_bytes,
                    "application/gzip",
                    main_archive_status,
                )
                return
            if self.path == f"/api/repos/{repository}/tarball/{second_commit}":
                self._send(second_main_source.read_bytes(), "application/gzip")
                return
            self.send_error(404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    asset_url = f"http://127.0.0.1:{server.server_port}/assets/{quote(source.name)}"
    api_url = f"http://127.0.0.1:{server.server_port}/api"
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
            "if ($Uri -eq $env:INSTALLER_SMOKE_INSTALLER_PUBLIC_URL) { "
            "return Microsoft.PowerShell.Utility\\Invoke-RestMethod -Uri $env:INSTALLER_SMOKE_INSTALLER_URL }; "
            "if ($Uri -like 'https://api.github.com/repos/*/releases/*') { "
            "$releasePath = $env:INSTALLER_SMOKE_RELEASE_JSON; "
            "if ($Uri -like '*/latest') { $releasePath = $env:INSTALLER_SMOKE_LATEST_RELEASE_JSON }; "
            "return (Get-Content -Raw -LiteralPath $releasePath | ConvertFrom-Json) }; "
            "$fixtureUri = $Uri -replace '^https://api.github.com', $env:INSTALLER_SMOKE_API_URL; "
            "Microsoft.PowerShell.Utility\\Invoke-RestMethod -Uri $fixtureUri }\n"
            "function Invoke-WebRequest { param([string]$Uri, [string]$OutFile); "
            "$fixtureUri = $Uri -replace '^https://api.github.com', $env:INSTALLER_SMOKE_API_URL; "
            "Microsoft.PowerShell.Utility\\Invoke-WebRequest -UseBasicParsing -Uri $fixtureUri -OutFile $OutFile }\n"
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
            "import json, os, pathlib, subprocess, sys, urllib.request\n"
            "args=sys.argv[1:]\n"
            "with open(os.environ['INSTALLER_SMOKE_GH_CALLS'], 'a', encoding='utf-8') as log: log.write(json.dumps(args)+'\\n')\n"
            "pathlib.Path(os.environ['INSTALLER_SMOKE_GH_CALLED']).write_text('called')\n"
            "if os.environ.get('INSTALLER_SMOKE_GH_FAIL') == '1': raise SystemExit(88)\n"
            "if args[:1] == ['api']:\n"
            " endpoint=next((arg for arg in args[1:] if arg.startswith(('repos/', '/repos/'))), '')\n"
            " endpoint='/'+endpoint.lstrip('/')\n"
            " if endpoint == '/'+os.environ['INSTALLER_SMOKE_INSTALLER_ENDPOINT']:\n"
            "  sys.stdout.buffer.write(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_INSTALLER_URL']).read()); raise SystemExit(0)\n"
            " repository=os.environ['INSTALLER_SMOKE_REPOSITORY']\n"
            " if endpoint == '/repos/'+repository+'/commits/main':\n"
            "  print(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_API_URL']+endpoint).read().decode()); raise SystemExit(0)\n"
            " if endpoint in ['/repos/'+repository+'/tarball/'+sha for sha in (os.environ['INSTALLER_SMOKE_MAIN_COMMIT'], 'b'*40) if sha]:\n"
            "  sys.stdout.buffer.write(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_API_URL']+endpoint).read()); raise SystemExit(0)\n"
            " if endpoint == '/repos/'+repository+'/releases/latest' or endpoint == '/repos/'+repository+'/releases/tags/'+os.environ['INSTALLER_SMOKE_RELEASE_TAG']:\n"
            "  release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if endpoint.endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            "  print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "if args[:2] == ['release','download'] and '--repo' in args and args[args.index('--repo')+1] == os.environ['INSTALLER_SMOKE_REPOSITORY']:\n"
            " name=args[args.index('--pattern')+1]; dest=pathlib.Path(args[args.index('--dir')+1]); dest.mkdir(parents=True,exist_ok=True)\n"
            " output=dest/name\n"
            " subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','Invoke-WebRequest -Uri $env:INSTALLER_SMOKE_ASSET_URL -OutFile $env:INSTALLER_SMOKE_GH_OUTPUT'],env=os.environ | {'INSTALLER_SMOKE_GH_OUTPUT':str(output)},check=True)\n"
            " raise SystemExit(0)\n"
            "real=os.environ.get('INSTALLER_SMOKE_REAL_GH')\n"
            "if not real: raise SystemExit(87)\n"
            "raise SystemExit(subprocess.run([real,*args],check=False).returncode)\n",
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
            "pathlib.Path(os.environ['INSTALLER_SMOKE_CURL_CALLED']).write_text('called')\n"
            "url=next((arg for arg in args if arg.startswith(('http://','https://'))), '')\n"
            "if url.startswith('https://astral.sh/uv/') and os.environ.get('INSTALLER_SMOKE_BOOTSTRAP_UV'):\n"
            ' print(\'mkdir -p "$HOME/.local/bin"\\ncp "$INSTALLER_SMOKE_BOOTSTRAP_UV" "$HOME/.local/bin/uv"\\ncp "$INSTALLER_SMOKE_BOOTSTRAP_UV" "$HOME/.local/bin/uvx"\\nchmod 700 "$HOME/.local/bin/uv" "$HOME/.local/bin/uvx"\'); raise SystemExit(0)\n'
            "if '/releases/' in url:\n"
            " release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if url.endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            " print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "if url.startswith('https://api.github.com/repos/'):\n"
            " args[args.index(url)]=os.environ['INSTALLER_SMOKE_API_URL']+url.split('github.com',1)[1]\n"
            "real=os.environ['INSTALLER_SMOKE_REAL_CURL']\n"
            "raise SystemExit(subprocess.run([real,*args],check=False).returncode)\n",
            encoding="utf-8",
        )
        curl_shim.chmod(0o755)
        gh_shim = shim_dir / "gh"
        gh_shim.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, subprocess, sys, urllib.request\n"
            "args=sys.argv[1:]\n"
            "with open(os.environ['INSTALLER_SMOKE_GH_CALLS'], 'a', encoding='utf-8') as log: log.write(json.dumps(args)+'\\n')\n"
            "pathlib.Path(os.environ['INSTALLER_SMOKE_GH_CALLED']).write_text('called')\n"
            "if os.environ.get('INSTALLER_SMOKE_GH_FAIL') == '1': raise SystemExit(88)\n"
            "if args[:1] == ['api']:\n"
            " endpoint=next((arg for arg in args[1:] if arg.startswith(('repos/', '/repos/'))), '')\n"
            " endpoint='/'+endpoint.lstrip('/')\n"
            " if endpoint == '/'+os.environ['INSTALLER_SMOKE_INSTALLER_ENDPOINT']:\n"
            "  sys.stdout.buffer.write(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_INSTALLER_URL']).read()); raise SystemExit(0)\n"
            " repository=os.environ['INSTALLER_SMOKE_REPOSITORY']\n"
            " if endpoint == '/repos/'+repository+'/commits/main':\n"
            "  print(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_API_URL']+endpoint).read().decode()); raise SystemExit(0)\n"
            " if endpoint in ['/repos/'+repository+'/tarball/'+sha for sha in (os.environ['INSTALLER_SMOKE_MAIN_COMMIT'], 'b'*40) if sha]:\n"
            "  sys.stdout.buffer.write(urllib.request.urlopen(os.environ['INSTALLER_SMOKE_API_URL']+endpoint).read()); raise SystemExit(0)\n"
            " if endpoint == '/repos/'+repository+'/releases/latest' or endpoint == '/repos/'+repository+'/releases/tags/'+os.environ['INSTALLER_SMOKE_RELEASE_TAG']:\n"
            "  release_path=os.environ['INSTALLER_SMOKE_LATEST_RELEASE_JSON'] if endpoint.endswith('/latest') else os.environ['INSTALLER_SMOKE_RELEASE_JSON']\n"
            "  print(pathlib.Path(release_path).read_text()); raise SystemExit(0)\n"
            "if args[:2] == ['release','download'] and '--repo' in args and args[args.index('--repo')+1] == os.environ['INSTALLER_SMOKE_REPOSITORY']:\n"
            " name=args[args.index('--pattern')+1]; dest=pathlib.Path(args[args.index('--dir')+1]); dest.mkdir(parents=True,exist_ok=True)\n"
            " subprocess.run([os.environ['INSTALLER_SMOKE_REAL_CURL'],'-fsSL',os.environ['INSTALLER_SMOKE_ASSET_URL'],'-o',str(dest/name)],check=True)\n"
            " raise SystemExit(0)\n"
            "real=os.environ.get('INSTALLER_SMOKE_REAL_GH')\n"
            "if not real: raise SystemExit(87)\n"
            "raise SystemExit(subprocess.run([real,*args],check=False).returncode)\n",
            encoding="utf-8",
        )
        gh_shim.chmod(0o755)

    isolated = tmp_path / "isolated home with spaces"
    installer_temp = tmp_path / "installer temporary directory with spaces"
    installer_temp.mkdir()
    (installer_temp / "sentinel").write_text("keep temporary parent", encoding="utf-8")
    config = isolated / "config"
    data = isolated / "data"
    cache = isolated / "cache"
    tool_dir = isolated / "uv tools"
    tool_bin = isolated / "uv bin"
    uv_cache = isolated / "uv cache"
    state = isolated / "state"
    local_appdata = isolated / "local appdata"
    for directory in (
        config,
        data,
        cache,
        tool_dir,
        tool_bin,
        uv_cache,
        state,
        local_appdata,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    config_sentinel = config / "sentinel"
    data_sentinel = data / "sentinel"
    config_sentinel.write_text("keep config", encoding="utf-8")
    data_sentinel.write_text("keep data", encoding="utf-8")
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("The source-installer tests require the runner's uv executable.")
    real_gh = shutil.which("gh")
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
            "XDG_STATE_HOME": str(state),
            "LOCALAPPDATA": str(local_appdata),
            "XDG_CACHE_HOME": str(cache),
            "UV_TOOL_DIR": str(tool_dir),
            "UV_TOOL_BIN_DIR": str(tool_bin),
            "UV_CACHE_DIR": str(uv_cache),
            "TMPDIR": str(installer_temp),
            "TMP": str(installer_temp),
            "TEMP": str(installer_temp),
            "INSTALLER_SMOKE_SOURCE": str(source) if source_mode == "release" else "",
            "INSTALLER_SMOKE_MAIN_SOURCE": str(source) if source_mode == "main" else "",
            "INSTALLER_SMOKE_MAIN_COMMIT": main_commit or "",
            "INSTALLER_SMOKE_CLIENT": client,
            "INSTALLER_SMOKE_RELEASE_JSON": str(tmp_path / "release.json"),
            "INSTALLER_SMOKE_LATEST_RELEASE_JSON": str(
                tmp_path / "latest-release.json"
            ),
            "INSTALLER_SMOKE_REPOSITORY": repository,
            "INSTALLER_SMOKE_RELEASE_TAG": f"v{version}",
            "INSTALLER_SMOKE_ASSET_URL": asset_url,
            "INSTALLER_SMOKE_API_URL": api_url,
            "INSTALLER_SMOKE_INSTALLER_URL": f"http://127.0.0.1:{server.server_port}/installer",
            "INSTALLER_SMOKE_INSTALLER_ENDPOINT": (
                f"repos/{installer_repository}/contents/src/{installer_module}/distribution/install-windows.ps1"
            ),
            "INSTALLER_SMOKE_INSTALLER_PUBLIC_URL": (
                f"https://raw.githubusercontent.com/{installer_repository}/main/src/{installer_module}/distribution/install-windows.ps1"
            ),
            "INSTALLER_SMOKE_GH_CALLS": str(tmp_path / "gh-calls.jsonl"),
            "INSTALLER_SMOKE_GH_CALLED": str(gh_called),
            "INSTALLER_SMOKE_REAL_GH": real_gh or "",
            "INSTALLER_SMOKE_CURL_CALLED": str(tmp_path / "curl-called"),
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


def _run_installer(
    command: list[str],
    *,
    env: dict[str, str],
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Capture Windows installer diagnostics as bytes and decode with OEM.

    Both PowerShell entrypoints retain the native console encoding. Capturing
    bytes prevents the parent Python locale from losing diagnostics to a
    decoder error.
    """
    if os.name != "nt":
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    result = subprocess.run(
        command, check=False, capture_output=True, env=env, timeout=timeout
    )

    def decode_output(output: bytes) -> str:
        return output.decode("oem", errors="backslashreplace")

    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        stdout=decode_output(result.stdout),
        stderr=decode_output(result.stderr),
    )


def _installer_command(
    uv: str | None,
    *arguments: str,
    skip_config: bool = True,
    installer_path: Path | None = None,
    installer_repository: str = "HisQu/buildben",
    installer_module: str = "buildben_dev",
    invocation: Literal["file", "downloaded"] = "file",
) -> list[str]:
    """Build file or downloaded-text commands without interpolating arguments."""
    prefix = ["--yes"]
    if skip_config:
        prefix.append("--skip-config")
    if uv is not None:
        prefix.extend(["--uv", uv])
    if os.name == "nt":
        if invocation == "downloaded":
            encoded_arguments = base64.b64encode(
                json.dumps([*prefix, *arguments]).encode("utf-8")
            ).decode("ascii")
            use_gh = any(
                argument == "--github-client"
                and arguments[index + 1 : index + 2] == ("gh",)
                for index, argument in enumerate(arguments)
            )
            fetch = (
                "$installer = gh api -H 'Accept: application/vnd.github.raw+json' "
                f"'repos/{installer_repository}/contents/src/{installer_module}/distribution/install-windows.ps1'; "
                "if ($LASTEXITCODE -ne 0) { throw 'Installer download failed.' }; "
                if use_gh
                else "$installer = Invoke-RestMethod -Uri "
                f"'https://raw.githubusercontent.com/{installer_repository}/main/src/{installer_module}/distribution/install-windows.ps1'; "
            )
            driver = (
                "$ErrorActionPreference = 'Stop'; "
                + fetch
                + "if (-not $installer) { throw 'Installer download is empty.' }; "
                + "$installerArguments = [string[]](ConvertFrom-Json -InputObject "
                + "([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
                + encoded_arguments
                + "')))); "
                + '& ([scriptblock]::Create(($installer -join "`n"))) @installerArguments'
            )
            return [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                base64.b64encode(driver.encode("utf-16le")).decode("ascii"),
            ]
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(installer_path or INSTALLER_DIR / "install-windows.ps1"),
            *prefix,
            *arguments,
        ]
    return [
        "bash",
        str(installer_path or INSTALLER_DIR / "install-linux-macos.sh"),
        *prefix,
        *arguments,
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--git"],
        ["--dev", "."],
        ["--github-client", "automatic"],
        ["--main", "--version", "0.1.0"],
        ["--version", "0.1.0", "--main"],
        ["--main", "-v", ""],
        ["-v", "", "--main"],
    ],
)
def test_rejected_options_do_not_run_uv(arguments: list[str], tmp_path: Path) -> None:
    if os.name == "nt":
        uv = tmp_path / "uv.cmd"
        uv.write_text("@echo off\necho invoked\n", encoding="utf-8")
        env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
        driver = (
            "$ErrorActionPreference = 'Stop'; "
            "$installerArguments = [string[]](ConvertFrom-Json -InputObject "
            "([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
            + base64.b64encode(json.dumps(arguments).encode("utf-8")).decode("ascii")
            + "')))); "
            + "& '"
            + str(INSTALLER_DIR / "install-windows.ps1").replace("'", "''")
            + "' @installerArguments"
        )
        command = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            base64.b64encode(driver.encode("utf-16le")).decode("ascii"),
        ]
    else:
        uv = tmp_path / "uv"
        uv.write_text("#!/bin/sh\nprintf invoked\n", encoding="utf-8")
        uv.chmod(0o755)
        env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
        command = ["bash", str(INSTALLER_DIR / "install-linux-macos.sh"), *arguments]
    result = _run_installer(command, env=env)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "invoked" not in output, output


def _windows_boundary_uv(directory: Path, *, fail: bool = False) -> Path:
    """Record uv calls and reject mutation before the source-validation boundary.

    :param directory: Isolated executable directory, also containing JSON-lines logs.
    :param fail: Reject every invocation to detect an incorrectly selected PATH uv.
    :return: Path to the Windows command shim.
    """
    directory.mkdir()
    (directory / "uv-fixture.py").write_text(
        "import json, pathlib, sys\n"
        "directory = pathlib.Path(__file__).parent\n"
        "args = sys.argv[1:]\n"
        "with (directory / 'calls.jsonl').open('a', encoding='utf-8') as log:\n"
        " log.write(json.dumps(args) + '\\n')\n"
        f"if {fail!r}: raise SystemExit(92)\n"
        "if args == ['--version']:\n"
        " print('uv 0.12.18'); raise SystemExit(0)\n"
        "if args[:2] == ['python', 'find']:\n"
        " print(sys.executable); raise SystemExit(0)\n"
        "with (directory / 'mutations.jsonl').open('a', encoding='utf-8') as log:\n"
        " log.write(json.dumps(args) + '\\n')\n"
        "raise SystemExit(91)\n",
        encoding="utf-8",
    )
    uv = directory / "uv.cmd"
    uv.write_text(
        f'@echo off\r\n"{sys.executable}" "%~dp0uv-fixture.py" %*\r\n'
        "exit /b %errorlevel%\r\n",
        encoding="utf-8",
    )
    return uv


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell installer regression.")
@pytest.mark.parametrize("invocation", ["file", "downloaded"])
@pytest.mark.parametrize("client", ["curl", "gh"])
@pytest.mark.parametrize("explicit_uv", [False, True])
def test_windows_installer_main_validation_preserves_uv_selection(
    tmp_path: Path,
    invocation: Literal["file", "downloaded"],
    client: str,
    explicit_uv: bool,
    windows_installer_target: tuple[Path, str, str],
) -> None:
    installer_path, repository, distribution = windows_installer_target
    source = tmp_path / f"{distribution}-0.10.3.tar.gz"
    _write_sdist(
        source,
        {
            "pyproject.toml": f'[project]\nname = "{distribution}"\nversion = "0.10.3"\n'.encode(),
            "uv.lock": b"version = 1\n",
        },
        distribution,
    )
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        repository=repository,
        source_mode="main",
        main_commit="a" * 40,
        main_commit_response=b'{"sha":"invalid"}',
        installer_source=installer_path,
        installer_repository=repository,
    )
    server, thread, environment, _, tool_dir, _, _, _, _, gh_called = fixture
    selected_uv_dir = tmp_path / "selected uv with spaces"
    selected_uv = _windows_boundary_uv(selected_uv_dir)
    path_dir = tmp_path / "failing uv path"
    _windows_boundary_uv(path_dir, fail=True)
    environment["PATH"] = os.pathsep.join(
        part
        for part in environment["PATH"].split(os.pathsep)
        if not (Path(part) / "uv.exe").is_file()
        and not (Path(part) / "uv.cmd").is_file()
    )
    args = ["--github-client", client, "--main"]
    command = _installer_command(
        str(selected_uv) if explicit_uv else None,
        *args,
        installer_path=installer_path,
        installer_repository=repository,
        installer_module=installer_path.parent.parent.name,
        invocation=invocation,
    )
    if explicit_uv:
        environment["PATH"] = os.pathsep.join([str(path_dir), environment["PATH"]])
    else:
        environment["PATH"] = os.pathsep.join(
            [str(selected_uv_dir), environment["PATH"]]
        )
    temporary_parent = Path(environment["TEMP"])
    before = set(temporary_parent.iterdir())
    thread.start()
    try:
        result = _run_installer(command, env=environment)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "GitHub returned an invalid main commit SHA" in output, output
        assert set(temporary_parent.iterdir()) == before
        assert (temporary_parent / "sentinel").read_text(
            encoding="utf-8"
        ) == "keep temporary parent"
        assert list(tool_dir.iterdir()) == []
        assert (selected_uv_dir / "calls.jsonl").is_file()
        assert not (path_dir / "calls.jsonl").exists()
        if client == "curl":
            assert not gh_called.exists()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell installer regression.")
@pytest.mark.parametrize("invocation", ["file", "downloaded"])
@pytest.mark.parametrize("client", ["curl", "gh"])
def test_windows_installer_default_release_rejects_draft(
    tmp_path: Path,
    invocation: Literal["file", "downloaded"],
    client: str,
    windows_installer_target: tuple[Path, str, str],
) -> None:
    installer_path, repository, distribution = windows_installer_target
    source = tmp_path / f"{distribution}-0.10.3.tar.gz"
    source.write_bytes(b"fixture archive")
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        release_overrides={"draft": True},
        repository=repository,
        installer_source=installer_path,
        installer_repository=repository,
    )
    server, thread, environment, _, tool_dir, *_ = fixture
    uv = _windows_boundary_uv(tmp_path / "release uv with spaces")
    thread.start()
    try:
        result = _run_installer(
            _installer_command(
                str(uv),
                "--github-client",
                client,
                installer_path=installer_path,
                installer_repository=repository,
                installer_module=installer_path.parent.parent.name,
                invocation=invocation,
            ),
            env=environment,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "not a published stable release" in output, output
        assert list(tool_dir.iterdir()) == []
        assert not (uv.parent / "mutations.jsonl").exists()
        assert list(Path(environment["TEMP"]).iterdir()) == [
            Path(environment["TEMP"]) / "sentinel"
        ]
        assert (
            Path(environment["TEMP"]) / "sentinel"
        ).read_text() == "keep temporary parent"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell installer regression.")
@pytest.mark.parametrize("invocation", ["file", "downloaded"])
@pytest.mark.parametrize("client", ["curl", "gh"])
@pytest.mark.parametrize("version", ["0.10.3", "v0.10.3"])
def test_windows_installer_version_selects_requested_stable_tag(
    tmp_path: Path,
    invocation: Literal["file", "downloaded"],
    client: str,
    version: str,
    windows_installer_target: tuple[Path, str, str],
) -> None:
    installer_path, repository, distribution = windows_installer_target
    source = tmp_path / f"{distribution}-0.10.3.tar.gz"
    source.write_bytes(b"not a gzip archive")
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        release_overrides={"draft": False},
        latest_release_overrides={"draft": True},
        repository=repository,
        installer_source=installer_path,
        installer_repository=repository,
    )
    server, thread, environment, _, tool_dir, *_ = fixture
    uv = _windows_boundary_uv(tmp_path / "version uv with spaces")
    thread.start()
    try:
        result = _run_installer(
            _installer_command(
                str(uv),
                "--github-client",
                client,
                "--version",
                version,
                installer_path=installer_path,
                installer_repository=repository,
                installer_module=installer_path.parent.parent.name,
                invocation=invocation,
            ),
            env=environment,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "not a gzip file" in output, output
        assert "not a published stable release" not in output, output
        assert list(tool_dir.iterdir()) == []
        assert not (uv.parent / "mutations.jsonl").exists()
        assert list(Path(environment["TEMP"]).iterdir()) == [
            Path(environment["TEMP"]) / "sentinel"
        ]
        assert (
            Path(environment["TEMP"]) / "sentinel"
        ).read_text() == "keep temporary parent"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell installer regression.")
@pytest.mark.parametrize("client", ["curl", "gh"])
@pytest.mark.parametrize("invocation", ["file", "downloaded"])
@pytest.mark.parametrize(
    "arguments",
    [
        ["--main", "--version", "0.10.3"],
        ["--version", "0.10.3", "--main"],
    ],
)
def test_windows_installer_conflicts_before_uv_or_source_requests(
    tmp_path: Path,
    invocation: Literal["file", "downloaded"],
    client: str,
    arguments: list[str],
    windows_installer_target: tuple[Path, str, str],
) -> None:
    installer_path, repository, distribution = windows_installer_target
    source = tmp_path / f"{distribution}-0.10.3.tar.gz"
    source.write_bytes(b"fixture archive")
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        repository=repository,
        installer_source=installer_path,
        installer_repository=repository,
    )
    server, thread, environment, _, _, _, _, _, _, gh_called = fixture
    uv_dir = tmp_path / "conflict uv"
    _windows_boundary_uv(uv_dir, fail=True)
    uv_calls = uv_dir / "calls.jsonl"
    environment["PATH"] = os.pathsep.join([str(uv_dir), environment["PATH"]])
    command = _installer_command(
        None,
        "--github-client",
        client,
        *arguments,
        installer_path=installer_path,
        installer_repository=repository,
        installer_module=installer_path.parent.parent.name,
        invocation=invocation,
    )
    thread.start()
    try:
        result = _run_installer(command, env=environment)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "--main cannot be combined with --version" in output, output
        assert not uv_calls.exists()
        assert list(Path(environment["TEMP"]).iterdir()) == [
            Path(environment["TEMP"]) / "sentinel"
        ]
        assert (
            Path(environment["TEMP"]) / "sentinel"
        ).read_text() == "keep temporary parent"
        calls_file = Path(environment["INSTALLER_SMOKE_GH_CALLS"])
        calls = (
            [json.loads(line) for line in calls_file.read_text().splitlines()]
            if calls_file.exists()
            else []
        )
        if invocation == "downloaded" and client == "gh":
            allowed_endpoint = f"repos/{repository}/contents/src/{installer_path.parent.parent.name}/distribution/install-windows.ps1"
            assert calls, "The downloaded installer must be fetched through gh."
            assert all(
                next(
                    (
                        argument.lstrip("/")
                        for argument in call
                        if argument.startswith(("repos/", "/repos/"))
                    ),
                    None,
                )
                == allowed_endpoint
                for call in calls
            ), calls
        else:
            assert not calls
            assert not gh_called.exists()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(
    "temporary_parent_kind",
    ["physical"] if os.name == "nt" else ["physical", "symlinked"],
)
@pytest.mark.parametrize(
    "installer_origin", ["canonical"] if os.name == "nt" else ["canonical", "rendered"]
)
@pytest.mark.parametrize(
    "invocation", ["file", "downloaded"] if os.name == "nt" else ["file"]
)
@pytest.mark.parametrize("source_mode", ["release", "main"])
def test_source_install_smoke(
    tmp_path: Path,
    source_mode: str,
    invocation: Literal["file", "downloaded"],
    installer_origin: str,
    temporary_parent_kind: str,
) -> None:
    """Install an actual release or pinned main archive through the installer."""
    source_key = (
        "INSTALLER_SMOKE_SOURCE"
        if source_mode == "release"
        else "INSTALLER_SMOKE_MAIN_SOURCE"
    )
    source_value = os.environ.get(source_key)
    if not source_value:
        pytest.skip(f"{source_key} is unset; source-install smoke is opt-in.")
    source = Path(source_value)
    if not source.is_absolute() or not source.is_file():
        pytest.fail(f"{source_key} must name an absolute path to an archive.")
    main_commit = None
    if source_mode == "main":
        main_commit = os.environ.get("INSTALLER_SMOKE_MAIN_COMMIT")
        if main_commit is None or not re.fullmatch(r"[0-9a-f]{40}", main_commit):
            pytest.fail(
                "INSTALLER_SMOKE_MAIN_COMMIT must contain a full lowercase 40-character SHA."
            )
    client = os.environ.get("INSTALLER_SMOKE_CLIENT", "curl")
    with tarfile.open(source, "r:gz") as archive:
        archive_names = {
            PurePosixPath(*PurePosixPath(member.name).parts[1:]).as_posix()
            for member in archive.getmembers()
        }
    assert {
        "src/buildben_dev/distribution/lifecycle.py",
        "src/buildben_dev/distribution/uninstall.sh",
        "src/buildben_dev/distribution/uninstall.cmd",
        "src/buildben_dev/distribution/uninstall.ps1",
        "src/buildben_dev/distribution/prepare-powershell-windows.cmd",
        "uninstall.sh",
        "uninstall.cmd",
    }.issubset(archive_names)
    if client not in {"curl", "gh"}:
        pytest.fail("INSTALLER_SMOKE_CLIENT must be curl or gh.")

    installer_path = INSTALLER_DIR / (
        "install-windows.ps1" if os.name == "nt" else "install-linux-macos.sh"
    )
    if installer_origin == "rendered":
        rendered_root = tmp_path / "rendered project"
        render_project(
            argparse.Namespace(
                name="buildben",
                target_dir=str(rendered_root),
                git_init=False,
                github_user="HisQu",
            )
        )
        installer_path = (
            rendered_root
            / "buildben"
            / "src"
            / "buildben_dev"
            / "distribution"
            / "install-linux-macos.sh"
        )

    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        source_mode=source_mode,
        main_commit=main_commit,
    )
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
    if os.name != "nt":
        temporary_parent = Path(environment["TEMP"]).resolve(strict=True)
        if temporary_parent_kind == "symlinked":
            temporary_alias = tmp_path / "symlinked temporary parent with spaces"
            temporary_alias.symlink_to(temporary_parent, target_is_directory=True)
            temporary_parent = temporary_alias
        for variable in ("TMPDIR", "TMP", "TEMP"):
            environment[variable] = str(temporary_parent)
    active_venv = _inherit_active_venv(tmp_path, environment)
    base_python = subprocess.run(
        [
            uv,
            "python",
            "find",
            "--system",
            "--no-project",
            "--no-python-downloads",
            "3.12",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()
    environment["PATH"] = os.pathsep.join(
        [environment["PATH"], str(Path(base_python).parent)]
    )
    environment["UV_PYTHON_DOWNLOADS"] = "never"
    installer_arguments = ["--github-client", client]
    if source_mode == "main":
        installer_arguments.append("--main")
    installed_environment = {
        key: value
        for key, value in environment.items()
        if key
        not in {
            "INSTALLER_SMOKE_SOURCE",
            "INSTALLER_SMOKE_MAIN_SOURCE",
            "INSTALLER_SMOKE_MAIN_COMMIT",
        }
    }
    temporary_parent = Path(environment["TEMP"])
    temporary_before = {path for path in temporary_parent.iterdir() if path.is_dir()}
    thread.start()
    try:
        # > Rendered installers reuse the BuildBen package to cover staging and
        # > lifecycle behavior, not a generated application's configuration wizard.
        result = _run_installer(
            _installer_command(
                uv,
                *installer_arguments,
                skip_config=(installer_origin == "rendered"),
                installer_path=installer_path,
                invocation=invocation,
            ),
            env=environment,
            timeout=900,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert {
            path for path in temporary_parent.iterdir() if path.is_dir()
        } == temporary_before
        assert (temporary_parent / "sentinel").read_text(
            encoding="utf-8"
        ) == "keep temporary parent"
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
                env=installed_environment,
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
            env=installed_environment,
        )
        assert smoke_result.returncode == 0, smoke_result.stdout + smoke_result.stderr
        assert gh_called.exists() is (client == "gh")
        origin = subprocess.run(
            [str(tool_python), "-c", "import buildben; print(buildben.__file__)"],
            check=True,
            capture_output=True,
            text=True,
            env=installed_environment,
        ).stdout.strip()
        assert Path(origin).resolve().is_relative_to((tool_dir / "buildben").resolve())
        assert config_sentinel.read_text(encoding="utf-8") == "keep config"
        assert data_sentinel.read_text(encoding="utf-8") == "keep data"
        state = Path(environment["XDG_STATE_HOME"])
        local_appdata = Path(environment["LOCALAPPDATA"])
        lifecycle_state = local_appdata if os.name == "nt" else state
        saved_launcher = (
            local_appdata / "buildben" / "installation" / "uninstall.cmd"
            if os.name == "nt"
            else state / "buildben" / "installation" / "uninstall.sh"
        )
        assert saved_launcher.is_file()
        if os.name == "nt":
            uninstall_command = ["cmd.exe", "/d", "/c", str(saved_launcher), "--yes"]
        else:
            uninstall_command = [str(saved_launcher), "--yes"]
        misleading_environment = installed_environment | {
            "UV_TOOL_DIR": str(tmp_path / "misleading tools"),
            "UV_TOOL_BIN_DIR": str(tmp_path / "misleading bins"),
        }
        uninstall = _run_installer(
            uninstall_command,
            env=misleading_environment,
            timeout=120,
        )
        assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
        assert config_sentinel.read_text(encoding="utf-8") == "keep config"
        assert data_sentinel.read_text(encoding="utf-8") == "keep data"
        receipt = json.loads(
            (lifecycle_state / "buildben" / "installation" / "receipt.json").read_text(
                encoding="utf-8"
            )
        )
        assert receipt["uv_bootstrapped"] is False
        assert Path(receipt["uv"]).resolve() == Path(uv).resolve()
        python_path = Path(receipt["python"]).resolve()
        python_info = subprocess.run(
            [
                str(python_path),
                "-c",
                "import sys; print(sys.prefix == sys.base_prefix)",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=installed_environment,
        ).stdout.strip()
        assert python_info == "True"
        assert not python_path.is_relative_to(active_venv.resolve())
        assert not python_path.is_relative_to((tool_dir / "buildben").resolve())
        assert receipt["package_removed"] is True
        assert Path(uv).is_file()
        repeated = _run_installer(
            uninstall_command,
            env=installed_environment,
            timeout=120,
        )
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert (
            lifecycle_state / "buildben" / "installation" / "lifecycle.py"
        ).is_file()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _run_main_failure(
    tmp_path: Path,
    *,
    main_commit_response: bytes | None = None,
    main_archive_bytes: bytes | None = None,
    main_commit_status: int = 200,
    main_archive_status: int = 200,
    preserve_installed_sentinel: bool = False,
    client: str = "curl",
) -> tuple[str, Path, Path]:
    source = tmp_path / "valid-main-source.tar.gz"
    _write_sdist(
        source,
        {
            "pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.10.3"\n',
            "uv.lock": b"version = 1\n",
        },
    )
    fixture = _install_smoke_fixture(
        tmp_path,
        source,
        client,
        source_mode="main",
        main_commit="a" * 40,
        main_commit_response=main_commit_response,
        main_archive_bytes=main_archive_bytes,
        main_commit_status=main_commit_status,
        main_archive_status=main_archive_status,
    )
    server, thread, environment, uv, tool_dir, _, _, _, _, gh_called = fixture
    if client == "gh":
        environment["INSTALLER_SMOKE_GH_FAIL"] = "1"
    sentinel = None
    if preserve_installed_sentinel:
        sentinel = tool_dir / "buildben" / "install-state-sentinel"
        sentinel.parent.mkdir()
        sentinel.write_text("previous installation", encoding="utf-8")
    thread.start()
    try:
        result = _run_installer(
            _installer_command(
                uv, "--github-client", client, "--main", skip_config=True
            ),
            env=environment,
            timeout=120,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        if sentinel is None:
            assert list(tool_dir.iterdir()) == []
        else:
            assert sentinel.read_text(encoding="utf-8") == "previous installation"
        if client == "gh":
            assert not Path(environment["INSTALLER_SMOKE_CURL_CALLED"]).exists()
        return output, gh_called, tool_dir
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(
    "response",
    [
        b"not-json",
        b"[]",
        b'{"sha":42}',
        b"{}",
        json.dumps({"sha": "not-a-full-sha"}).encode(),
        json.dumps({"sha": "A" * 40}).encode(),
    ],
)
def test_main_rejects_missing_or_invalid_commit_sha(
    tmp_path: Path, response: bytes
) -> None:
    output, gh_called, _ = _run_main_failure(tmp_path, main_commit_response=response)
    assert "invalid main commit SHA" in output
    assert not gh_called.exists()


def test_main_commit_transport_failure_does_not_install(
    tmp_path: Path,
) -> None:
    output, gh_called, _ = _run_main_failure(tmp_path, main_commit_status=500)
    assert (
        "500" in output
        if os.name == "nt"
        else "returned non-zero exit status 22" in output
    )
    assert not gh_called.exists()


def test_main_archive_transport_failure_does_not_install(
    tmp_path: Path,
) -> None:
    output, gh_called, _ = _run_main_failure(tmp_path, main_archive_status=404)
    assert (
        "404" in output
        if os.name == "nt"
        else "returned non-zero exit status 22" in output
    )
    assert not gh_called.exists()


@pytest.mark.parametrize("archive_bytes", [b"", b"truncated gzip bytes"])
def test_main_rejects_empty_or_invalid_archive(
    tmp_path: Path, archive_bytes: bytes
) -> None:
    output, _, _ = _run_main_failure(tmp_path, main_archive_bytes=archive_bytes)
    lower_output = output.lower()
    assert (
        "source archive download is empty" in lower_output
        if not archive_bytes
        else "not a gzip file" in lower_output
    )


@pytest.mark.parametrize(
    ("members", "error"),
    [
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "other"\nversion = "0.1.0"\n',
                "snapshot/uv.lock": b"version = 1\n",
            },
            "Source project metadata does not match",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\n',
                "snapshot/uv.lock": b"version = 1\n",
            },
            "Source project metadata does not match",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = ""\n',
                "snapshot/uv.lock": b"version = 1\n",
            },
            "Source project metadata does not match",
        ),
        (
            {"snapshot/uv.lock": b"version = 1\n"},
            "pyproject.toml and uv.lock",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
            },
            "pyproject.toml and uv.lock",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
                "snapshot/uv.lock": b"version = 1\n",
                "../outside": b"unsafe",
            },
            "unsafe path",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
                "snapshot/uv.lock": b"version = 1\n",
                "/absolute": b"unsafe",
            },
            "unsafe path",
        ),
        (
            {
                "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
                "snapshot/uv.lock": b"version = 1\n",
                "C:/drive-qualified": b"unsafe",
            },
            "unsafe path",
        ),
        (
            {
                "one/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
                "two/uv.lock": b"version = 1\n",
            },
            "exactly one project root",
        ),
    ],
)
def test_main_rejects_invalid_archive_metadata_and_members(
    tmp_path: Path, members: dict[str, bytes], error: str
) -> None:
    output, _, _ = _run_main_failure(
        tmp_path, main_archive_bytes=_archive_bytes(members)
    )
    assert error in output


@pytest.mark.parametrize("member_type", [tarfile.SYMTYPE, tarfile.FIFOTYPE])
def test_main_rejects_links_and_special_members(
    tmp_path: Path, member_type: bytes
) -> None:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, data in {
            "snapshot/pyproject.toml": b'[project]\nname = "buildben"\nversion = "0.1.0"\n',
            "snapshot/uv.lock": b"version = 1\n",
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        special = tarfile.TarInfo("snapshot/special")
        special.type = member_type
        if member_type == tarfile.SYMTYPE:
            special.linkname = "pyproject.toml"
        archive.addfile(special)
    output, _, _ = _run_main_failure(tmp_path, main_archive_bytes=stream.getvalue())
    assert "links or special files" in output


def test_main_stale_lock_fails_before_installation(tmp_path: Path) -> None:
    stale_lock = (Path(__file__).resolve().parents[1] / "uv.lock").read_bytes()
    project = (
        b'[project]\nname = "buildben"\nversion = "0.10.3"\n'
        b'requires-python = ">=3.12"\ndependencies = []\n'
    )
    output, _, _ = _run_main_failure(
        tmp_path,
        main_archive_bytes=_archive_bytes(
            {"snapshot/pyproject.toml": project, "snapshot/uv.lock": stale_lock}
        ),
        preserve_installed_sentinel=True,
    )
    assert "lock" in output.lower()


def test_main_gh_failure_does_not_fall_back_to_public_transport(
    tmp_path: Path,
) -> None:
    output, gh_called, tool_dir = _run_main_failure(tmp_path, client="gh")
    expected_error = (
        "source installation failed"
        if os.name == "nt"
        else "returned non-zero exit status 88"
    )
    assert expected_error in output
    assert gh_called.is_file()
    assert list(tool_dir.iterdir()) == []


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
        result = _run_installer(
            _installer_command(uv, "--github-client", "curl"),
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
        result = _run_installer(
            _installer_command(uv, "--github-client", "curl"),
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
        result = _run_installer(
            _installer_command(uv, "--github-client", "curl"),
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
        result = _run_installer(
            _installer_command(uv, "--github-client", "curl"),
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
        result = _run_installer(
            _installer_command(uv, "--github-client", "curl", "--version", "0.10.3"),
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
        result = _run_installer(
            _installer_command(uv, "--github-client", "gh"),
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


@pytest.mark.skipif(
    os.name == "nt", reason="This exercises the Unix bootstrap transport."
)
def test_source_install_smoke_bootstrap_owned_uv_removal(
    tmp_path: Path,
) -> None:
    """Run the real missing-uv installer branch and saved offline uninstaller."""
    source_value = os.environ.get("INSTALLER_SMOKE_SOURCE")
    if not source_value:
        pytest.skip("INSTALLER_SMOKE_SOURCE is unset; source-install smoke is opt-in.")
    fixture = _install_smoke_fixture(tmp_path, Path(source_value), "curl")
    server, thread, environment, uv, tool_dir, _, config, data, _, _ = fixture
    shim_dir = Path(environment["PATH"].split(os.pathsep)[0])
    isolated_bin = tmp_path / "bootstrap commands"
    isolated_bin.mkdir()
    for name in (
        "bash",
        "sh",
        "env",
        "mkdir",
        "dirname",
        "basename",
        "mktemp",
        "rm",
        "cp",
        "chmod",
        "python3",
    ):
        executable = shutil.which(name)
        assert executable is not None, f"Bootstrap fixture requires {name}."
        (isolated_bin / name).symlink_to(executable)
    for version in ("3.13", "3.12"):
        discovery = subprocess.run(
            [
                uv,
                "python",
                "find",
                "--system",
                "--no-project",
                "--no-python-downloads",
                version,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if discovery.returncode == 0:
            (isolated_bin / f"python{version}").symlink_to(discovery.stdout.strip())
            break
    else:
        pytest.fail("Bootstrap fixture requires an existing base Python 3.12 or 3.13.")
    environment.update(
        {
            "PATH": os.pathsep.join((str(shim_dir), str(isolated_bin))),
            "INSTALLER_SMOKE_BOOTSTRAP_UV": uv,
            "UV_PYTHON_DOWNLOADS": "never",
        }
    )
    saved = Path(environment["XDG_STATE_HOME"]) / "buildben" / "installation"
    disposable_uv = Path(environment["HOME"]) / ".local" / "bin" / "uv"
    disposable_uvx = disposable_uv.with_name("uvx")
    cache_sentinel = Path(environment["UV_CACHE_DIR"]) / "retained-cache"
    cache_sentinel.write_text("shared cache", encoding="utf-8")
    thread.start()
    try:
        installed = subprocess.run(
            [
                str(isolated_bin / "bash"),
                str(INSTALLER_DIR / "install-linux-macos.sh"),
                "--yes",
                "--skip-config",
                "--github-client",
                "curl",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert installed.returncode == 0, installed.stdout + installed.stderr
        receipt = json.loads((saved / "receipt.json").read_text(encoding="utf-8"))
        assert receipt["uv_bootstrapped"] is True
        assert receipt["uv"] == str(disposable_uv)
        assert {item["path"] for item in receipt["uv_binaries"]} == {
            str(disposable_uv),
            str(disposable_uvx),
        }
        removed = subprocess.run(
            [str(saved / "uninstall.sh"), "--remove-uv", "--yes"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert removed.returncode == 0, removed.stdout + removed.stderr
        assert not disposable_uv.exists()
        assert not disposable_uvx.exists()
        assert not (tool_dir / "buildben").exists()
        assert Path(uv).is_file()
        assert config.read_text(encoding="utf-8") == "keep config"
        assert data.read_text(encoding="utf-8") == "keep data"
        assert cache_sentinel.read_text(encoding="utf-8") == "shared cache"
        completed = (saved / "receipt.json").read_bytes()
        assert json.loads(completed)["package_removed"] is True
        repeated = subprocess.run(
            [str(saved / "uninstall.sh"), "--yes"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert (saved / "receipt.json").read_bytes() == completed
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
