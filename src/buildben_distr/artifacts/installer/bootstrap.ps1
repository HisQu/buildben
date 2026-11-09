$ErrorActionPreference = 'Stop'
$script:SavedPolicy = Get-ExecutionPolicy -Scope Process
$script:ChangedPolicy = $false
$script:ExitCode = 0
try {
    if ($script:SavedPolicy -eq 'Restricted' -or $script:SavedPolicy -eq 'AllSigned') {
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
        $script:ChangedPolicy = $true
    }
    $main = $null
    $selection = ''
    $selectorCount = 0
    $clientCount = 0
    $argumentIndex = 0
    while ($argumentIndex -lt $args.Count) {
        $argument = $args[$argumentIndex]
        if ($argument -eq '--') { break }
        if ($argument -in @('--main-ref', '--main-commit', '--release-version')) {
            throw "$argument is not a supported public selector."
        }
        if ($argument -eq '--github-client') {
            $clientCount++
            if ($clientCount -gt 1) { throw 'Specify --github-client only once.' }
            if ($argumentIndex + 1 -ge $args.Count -or $args[$argumentIndex + 1] -ne 'gh') {
                throw '--github-client requires gh.'
            }
            $argumentIndex += 2
            continue
        }
        if ($argument -eq '--main') {
            $selection = 'main'
            $selectorCount++
        } elseif ($argument -eq '--version') {
            $selection = 'release'
            $selectorCount++
            if ($argumentIndex + 1 -ge $args.Count -or
                $args[$argumentIndex + 1] -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
                throw '--version requires an exact X.Y.Z version.'
            }
            $argumentIndex++
        }
        $argumentIndex++
    }
    if ($selectorCount -gt 1) {
        throw 'Specify only one of --version or --main.'
    }
    if ([string]::IsNullOrEmpty($selection)) {
        $selection = 'local'
    }
    if ($selection -eq 'local') {
        $main = Join-Path $PSScriptRoot 'main-installer.py'
        if (-not (Test-Path -LiteralPath $main -PathType Leaf)) {
            throw 'Generated installer is missing. Run `just make-artifacts` in the checkout.'
        }
    }

    $uvPath = $env:UV
    if ([string]::IsNullOrWhiteSpace($uvPath)) {
        foreach ($entry in ($env:PATH -split ';')) {
            if ([string]::IsNullOrEmpty($entry)) { $entry = (Get-Location).Path }
            if (-not [System.IO.Path]::IsPathRooted($entry)) {
                $entry = Join-Path (Get-Location).Path $entry
            }
            $candidate = [System.IO.Path]::GetFullPath((Join-Path $entry 'uv.exe'))
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                $uvPath = $candidate
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($uvPath)) {
        $candidate = Join-Path $HOME '.local\bin\uv.exe'
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $uvPath = $candidate }
    }
    if ([string]::IsNullOrWhiteSpace($uvPath)) {
        $installer = Join-Path $env:TEMP ('uv-install-' + [guid]::NewGuid().ToString('N') + '.ps1')
        try {
            Invoke-WebRequest https://astral.sh/uv/install.ps1 -OutFile $installer
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
            if ($LASTEXITCODE -ne 0) { throw 'Official uv installer failed.' }
        } finally { Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue }
        $uvPath = Join-Path $HOME '.local\bin\uv.exe'
    }
    if (-not [System.IO.Path]::IsPathRooted($uvPath) -or
        -not (Test-Path -LiteralPath $uvPath -PathType Leaf)) {
        throw 'Selected uv executable must be an available absolute application path.'
    }
    if ($selection -eq 'main' -or $selection -eq 'release') {
        $fetcher = Join-Path $env:TEMP ('apprc-bootstrap-' + [guid]::NewGuid().ToString('N') + '.py')
        $previousBootstrapUv = $env:APPRC_UV_PATH
        try {
            if ($selection -eq 'main') {
                $fetcherContents = @'
"""Resolve one remote-main ref and use its full commit for every input."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

REPOSITORY_URL = "https://github.com/HisQu/buildben"
INSTALLER_PATH = "src/buildben_distr/artifacts/installer/main-installer.py"
PAYLOAD_FORMAT = "script"


def _repository() -> tuple[str, str]:
    address = urllib.parse.urlsplit(REPOSITORY_URL)
    parts = [part for part in address.path.split("/") if part]
    if (address.scheme != "https" or address.hostname != "github.com"
            or address.username is not None or address.password is not None
            or address.query or address.fragment or len(parts) != 2):
        raise RuntimeError("Remote-main requires a credential-free GitHub repository URL.")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    if not owner or not repository:
        raise RuntimeError("Remote-main repository identity is incomplete.")
    return owner, repository


def _read_url(address: str, *, client: str, limit: int = 4 * 1024 * 1024) -> bytes:
    parsed = urllib.parse.urlsplit(address)
    if client == "gh":
        endpoint = parsed.path.lstrip("/") + (("?" + parsed.query) if parsed.query else "")
        result = subprocess.run(
            ["gh", "api", endpoint], check=True, capture_output=True
        )
        data = result.stdout
    else:
        request = urllib.request.Request(
            address, headers={"Accept": "application/vnd.github+json", "User-Agent": "AppRC distribution"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError("Remote-main response exceeds its supported size limit.")
    return data


def _arguments() -> tuple[str, list[str]]:
    selected = False
    client = "public"
    forwarded: list[str] = []
    arguments = iter(sys.argv[1:])
    for argument in arguments:
        if argument == "--":
            forwarded.extend([argument, *arguments])
            break
        if argument == "--main":
            if selected:
                raise RuntimeError("Specify --main only once.")
            selected = True
        elif argument == "--github-client":
            if client != "public":
                raise RuntimeError("Specify --github-client only once.")
            client = next(arguments, "")
            if client != "gh":
                raise RuntimeError("--github-client only supports gh.")
        elif argument in {"--main-ref", "--main-commit", "--release-version"}:
            raise RuntimeError(f"{argument} is not a supported public selector.")
        elif argument in {"--source-mode", "--source-repository", "--source-commit", "--source-package"}:
            raise RuntimeError("Source identity arguments are reserved for the remote-main transport.")
        else:
            forwarded.append(argument)
    return client, forwarded


def _resolve_commit(owner: str, repository: str, reference: str, client: str) -> str:
    endpoint = (
        f"https://api.github.com/repos/{owner}/{repository}/commits/"
        f"{urllib.parse.quote(reference, safe='')}"
    )
    value = json.loads(_read_url(endpoint, client=client))
    commit = value.get("sha") if isinstance(value, dict) else None
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("Remote-main ref did not resolve to a full immutable Git commit.")
    return commit


def _download(address: str, destination: Path, client: str) -> None:
    if client == "gh":
        parsed = urllib.parse.urlsplit(address)
        if parsed.hostname == "raw.githubusercontent.com":
            owner, repository, reference, *path = parsed.path.strip("/").split("/")
            endpoint = (
                f"repos/{owner}/{repository}/contents/"
                + "/".join(
                    urllib.parse.quote(
                        urllib.parse.unquote(part), safe=""
                    )
                    for part in path
                )
                + "?ref=" + urllib.parse.quote(reference, safe="")
            )
            command = [
                "gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"
            ]
        else:
            endpoint = parsed.path.lstrip("/")
            if parsed.query:
                endpoint += "?" + parsed.query
            command = ["gh", "api", endpoint]
        with destination.open("xb") as output:
            subprocess.run(command, check=True, stdout=output)
    else:
        request = urllib.request.Request(
            address, headers={"User-Agent": "AppRC distribution"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with destination.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("Remote-main download is empty.")
    if destination.stat().st_size > 256 * 1024 * 1024:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Remote-main download exceeds its supported size limit.")


def main() -> int:
    try:
        client, forwarded = _arguments()
        owner, repository = _repository()
        commit = _resolve_commit(owner, repository, "main", client)
        relative = PurePosixPath(INSTALLER_PATH)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in INSTALLER_PATH
                or not relative.parts):
            raise RuntimeError("Remote-main installer path is unsafe.")
        raw = f"https://raw.githubusercontent.com/{owner}/{repository}/{commit}"
        address = raw + "/" + "/".join(urllib.parse.quote(part, safe="") for part in relative.parts)
        with tempfile.TemporaryDirectory(prefix="apprc-main-") as temporary:
            root = Path(temporary)
            os.chmod(root, 0o700)
            payload = root / ("main-installer.pyz" if PAYLOAD_FORMAT == "zipapp" else "main-installer.py")
            _download(address, payload, client)
            package = root / "source.tar.gz"
            _download(
                f"https://api.github.com/repos/{owner}/{repository}/tarball/{commit}",
                package,
                client,
            )
            uv = Path(os.environ.get("APPRC_UV_PATH", ""))
            if not uv.is_absolute() or not uv.is_file():
                raise RuntimeError("The bootstrap's absolute uv executable is unavailable.")
            transport = [
                "--source-mode", "main", "--source-repository", REPOSITORY_URL,
                "--source-commit", commit, "--source-package", str(package),
            ]
            if client == "gh":
                transport.extend(["--github-client", "gh"])
            environment = dict(os.environ)
            environment["APPRC_UV_PATH"] = str(uv)
            if PAYLOAD_FORMAT == "script":
                command = [str(uv), "run", "--no-project", "--python", ">=3.12",
                           "--script", str(payload), *transport, *forwarded]
            else:
                requirements = root / "main-installer-requirements.txt"
                requirements_path = relative.parent / "main-installer-requirements.txt"
                requirements_url = raw + "/" + "/".join(
                    urllib.parse.quote(part, safe="") for part in requirements_path.parts
                )
                _download(requirements_url, requirements, client)
                command = [str(uv), "run", "--no-project", "--python", ">=3.12",
                           "--with-requirements", str(requirements), "python", str(payload),
                           *transport, *forwarded]
            return subprocess.run(command, env=environment, check=False).returncode
    except (
        OSError,
        ValueError,
        RuntimeError,
        urllib.error.URLError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"AppRC remote-main bootstrap failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

'@
            } else {
                $fetcherContents = @'
"""Resolve one GitHub release and execute only its matching installer payload."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

APP_ID = "buildben"
DISTRIBUTION = "buildben"
REPOSITORY_URL = "https://github.com/HisQu/buildben"
DEFAULT_VERSION = "latest"
GITHUB_CLIENT = "public"
RELEASE_TAG = ""

def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"Duplicate JSON object key: {key}.")
        result[key] = value
    return result

def _json_loads(value: bytes) -> object:
    return json.loads(value, object_pairs_hook=_json_object)

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_url(url: str, *, limit: int | None = None) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if GITHUB_CLIENT == "gh" and parsed.hostname == "api.github.com":
        endpoint = parsed.path.lstrip("/") + (("?" + parsed.query) if parsed.query else "")
        result = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True)
        data = result.stdout if limit is None else result.stdout[:limit + 1]
    else:
        request = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AppRC distribution"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read() if limit is None else response.read(limit + 1)
    if limit is not None and len(data) > limit:
        raise RuntimeError("Release metadata exceeds the supported size limit.")
    return data


def _repository_api() -> str:
    address = urllib.parse.urlsplit(REPOSITORY_URL)
    parts = [part for part in address.path.split("/") if part]
    if (address.scheme != "https" or address.hostname != "github.com"
            or address.username is not None or address.password is not None
            or address.query or address.fragment or len(parts) != 2):
        raise RuntimeError("Release selection requires a credential-free GitHub repository URL.")
    repository = parts[1].removesuffix(".git")
    if not parts[0] or not repository:
        raise RuntimeError("GitHub owner and repository names are required.")
    return f"https://api.github.com/repos/{parts[0]}/{repository}"


def _asset_url(address: object) -> str:
    if not isinstance(address, str):
        raise RuntimeError("Release asset URL is invalid.")
    parsed = urllib.parse.urlsplit(address)
    repository = urllib.parse.urlsplit(REPOSITORY_URL)
    parts = [part for part in repository.path.split("/") if part]
    if len(parts) != 2 or not parts[0] or not parts[1].removesuffix(".git"):
        raise RuntimeError("Release bootstrap has an invalid repository identity.")
    expected_prefix = f"/{parts[0]}/{parts[1].removesuffix('.git')}/releases/download/"
    if (parsed.scheme != "https" or parsed.hostname != "github.com"
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or not parsed.path.startswith(expected_prefix)):
        raise RuntimeError("Release asset URL is outside the selected GitHub repository.")
    return address


def _select_release(api: str, selector: str) -> dict[str, object]:
    path = (
        "/releases/latest"
        if selector == "latest"
        else "/releases/tags/v" + urllib.parse.quote(selector, safe="")
    )
    try:
        release = _json_loads(_read_url(api + path, limit=4 * 1024 * 1024))
    except urllib.error.HTTPError as error:
        if error.code == 404 and selector != "latest":
            raise RuntimeError(
                f"No published release matches version {selector!r}."
            ) from error
        raise
    if (
        not isinstance(release, dict)
        or release.get("draft") is not False
        or not isinstance(release.get("tag_name"), str)
        or not release["tag_name"]
    ):
        raise RuntimeError("Selected GitHub release is unavailable or unpublished.")
    if selector != "latest" and release["tag_name"] != f"v{selector}":
        raise RuntimeError("Selected GitHub release tag differs from the requested version.")
    return release


def _release_assets(release: dict[str, object]) -> dict[str, dict[str, object]]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("Selected GitHub release has no asset inventory.")
    result: dict[str, dict[str, object]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise RuntimeError("Selected GitHub release contains an invalid asset entry.")
        name, size = asset.get("name"), asset.get("size")
        address = _asset_url(asset.get("browser_download_url"))
        if (not isinstance(name, str) or not name or "/" in name or "\\" in name
                or name in result or not isinstance(size, int) or isinstance(size, bool) or size < 0):
            raise RuntimeError("Selected GitHub release contains an unsafe or duplicate asset.")
        result[name] = {**asset, "browser_download_url": address}
    return result


def _validate_manifest(
    manifest: object, release_assets: dict[str, dict[str, object]], selector: str,
) -> tuple[str, dict[str, dict[str, object]]]:
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "app_id", "distribution", "version", "commit", "payload_format", "assets",
    }:
        raise RuntimeError("Release manifest does not match the supported schema.")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["app_id"] != APP_ID
        or manifest["distribution"] != DISTRIBUTION
        or not isinstance(manifest["version"], str)
        or re.fullmatch(
            r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
            manifest["version"],
        ) is None
        or not isinstance(manifest["commit"], str)
        or re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]) is None
        or not isinstance(manifest["payload_format"], str)
        or manifest["payload_format"] not in {"script", "zipapp"}
    ):
        raise RuntimeError("Release manifest identity differs from the requested application.")
    if selector != "latest" and manifest["version"] != selector.removeprefix("v"):
        raise RuntimeError("Selected release version differs from its manifest identity.")
    assets = manifest["assets"]
    if not isinstance(assets, list):
        raise RuntimeError("Release manifest has no asset inventory.")
    by_name: dict[str, dict[str, object]] = {}
    for asset in assets:
        if (
            not isinstance(asset, dict)
            or set(asset) != {"filename", "size", "sha256"}
            or not isinstance(asset["filename"], str)
            or asset["filename"] in {"", ".", ".."}
            or "/" in asset["filename"]
            or "\\" in asset["filename"]
            or "\x00" in asset["filename"]
            or not isinstance(asset["size"], int)
            or isinstance(asset["size"], bool)
            or asset["size"] < 0
            or not isinstance(asset["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]) is None
            or asset["filename"] in by_name
        ):
            raise RuntimeError("Release manifest contains an invalid or duplicate asset.")
        by_name[asset["filename"]] = asset
    if set(by_name) != set(release_assets) - {"release-manifest.json"}:
        raise RuntimeError("Release manifest and selected GitHub asset inventories differ.")
    for name, asset in by_name.items():
        if release_assets[name].get("size") != asset["size"]:
            raise RuntimeError(f"Release asset size differs from the manifest: {name}.")
    payload_name = "main-installer.py" if manifest["payload_format"] == "script" else "main-installer.pyz"
    if payload_name not in by_name:
        raise RuntimeError("Selected release has no matching installer payload.")
    if manifest["payload_format"] == "zipapp" and "main-installer-requirements.txt" not in by_name:
        raise RuntimeError("Selected zipapp release has no dependency specification.")
    if sum(name.endswith(".tar.gz") for name in by_name) != 1 or sum(
        name.endswith(".whl") for name in by_name
    ) != 1:
        raise RuntimeError("Selected release must contain exactly one sdist and one wheel.")
    return payload_name, by_name


def _download_asset(
    name: str, release_assets: dict[str, dict[str, object]],
    manifest_assets: dict[str, dict[str, object]], destination: Path,
) -> None:
    asset = release_assets[name]
    expected = manifest_assets[name]
    if GITHUB_CLIENT == "gh":
        owner, repository = _repository_api().removeprefix(
            "https://api.github.com/repos/"
        ).split("/")
        subprocess.run(
            [
                "gh", "release", "download", RELEASE_TAG, "--repo",
                f"{owner}/{repository}", "--dir", str(destination.parent),
                "--pattern", name,
            ],
            check=True,
        )
        size = destination.stat().st_size
        digest = _sha256_file(destination)
    else:
        request = urllib.request.Request(
            _asset_url(asset.get("browser_download_url")),
            headers={"User-Agent": "AppRC distribution"},
        )
        digest_builder = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                digest_builder.update(chunk)
                output.write(chunk)
        digest = digest_builder.hexdigest()
    if size != expected["size"] or digest != expected["sha256"]:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded release asset differs from its manifest: {name}.")


def _arguments() -> tuple[str, str, list[str]]:
    selector = DEFAULT_VERSION
    client = "public"
    forwarded: list[str] = []
    selected = False
    arguments = iter(sys.argv[1:])
    for argument in arguments:
        if argument == "--":
            forwarded.extend([argument, *arguments])
            break
        if argument == "--version":
            if selected:
                raise RuntimeError("Specify --version only once.")
            selector = next(arguments, "")
            if not selector:
                raise RuntimeError("--version requires an exact X.Y.Z version.")
            selected = True
        elif argument == "--github-client":
            if client != "public":
                raise RuntimeError("Specify --github-client only once.")
            client = next(arguments, "")
            if client != "gh":
                raise RuntimeError("--github-client only supports gh.")
        elif argument == "--main":
            raise RuntimeError("--main conflicts with this release bootstrap.")
        elif argument in {"--release-version", "--main-ref", "--main-commit"}:
            raise RuntimeError(f"{argument} is not a supported public selector.")
        else:
            forwarded.append(argument)
    version_pattern = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    if selected and re.fullmatch(version_pattern, selector) is None:
        raise RuntimeError("--version requires an exact X.Y.Z version.")
    if not selected and selector != "latest" and re.fullmatch(
        version_pattern, selector
    ) is None:
        raise RuntimeError("Authored release version must be latest or exact X.Y.Z.")
    return selector, client, forwarded

def _download_manifest(asset: dict[str, object], destination: Path) -> bytes:
    if (
        not isinstance(asset.get("size"), int)
        or isinstance(asset["size"], bool)
        or asset["size"] > 4 * 1024 * 1024
    ):
        raise RuntimeError("Release manifest asset exceeds the supported size limit.")
    if GITHUB_CLIENT == "gh":
        owner, repository = _repository_api().removeprefix(
            "https://api.github.com/repos/"
        ).split("/")
        subprocess.run(
            [
                "gh", "release", "download", RELEASE_TAG, "--repo",
                f"{owner}/{repository}", "--dir", str(destination.parent),
                "--pattern", "release-manifest.json",
            ],
            check=True,
        )
        if destination.stat().st_size > 4 * 1024 * 1024:
            raise RuntimeError("Downloaded release manifest exceeds the supported size limit.")
        data = destination.read_bytes()
    else:
        data = _read_url(
            _asset_url(asset.get("browser_download_url")), limit=4 * 1024 * 1024
        )
        destination.write_bytes(data)
    if len(data) != asset["size"]:
        raise RuntimeError("Release manifest download size differs from the selected asset.")
    return data


def main() -> int:
    global GITHUB_CLIENT, RELEASE_TAG
    try:
        selector, client, forwarded = _arguments()
        GITHUB_CLIENT = client
        release = _select_release(_repository_api(), selector)
        release_assets = _release_assets(release)
        tag = release.get("tag_name")
        if not isinstance(tag, str):
            raise RuntimeError("Selected release has no immutable tag identity.")
        RELEASE_TAG = tag
        manifest_asset = release_assets.get("release-manifest.json")
        if manifest_asset is None:
            raise RuntimeError("Selected release has no release-manifest.json asset.")
        with tempfile.TemporaryDirectory(prefix="apprc-release-") as temporary:
            root = Path(temporary)
            manifest_bytes = _download_manifest(
                manifest_asset, root / "release-manifest.json"
            )
            manifest = _json_loads(manifest_bytes)
            if not isinstance(manifest, dict) or tag != f"v{manifest.get('version')}":
                raise RuntimeError("Selected release tag differs from its manifest version.")
            payload_name, manifest_assets = _validate_manifest(
                manifest, release_assets, selector
            )
            payload = root / payload_name
            _download_asset(payload_name, release_assets, manifest_assets, payload)
            package_name = next(
                name for name in manifest_assets if name.endswith(".tar.gz")
            )
            package = root / package_name
            _download_asset(package_name, release_assets, manifest_assets, package)
            uv = Path(os.environ.get("APPRC_UV_PATH", ""))
            if not uv.is_absolute() or not uv.is_file():
                raise RuntimeError("The bootstrap's absolute uv executable is unavailable.")
            transport = ["--source-package", str(package)]
            if client == "gh":
                transport.extend(["--github-client", "gh"])
            if manifest["payload_format"] == "script":
                command = [str(uv), "run", "--no-project", "--python", ">=3.12",
                           "--script", str(payload), *transport, *forwarded]
            else:
                requirements = root / "main-installer-requirements.txt"
                _download_asset("main-installer-requirements.txt", release_assets, manifest_assets, requirements)
                command = [str(uv), "run", "--no-project", "--python", ">=3.12",
                           "--with-requirements", str(requirements), "python", str(payload),
                           *transport, *forwarded]
            return subprocess.run(command, check=False).returncode
    except (
        OSError,
        ValueError,
        RuntimeError,
        urllib.error.URLError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"AppRC release bootstrap failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

'@
            }
            [System.IO.File]::WriteAllText(
                $fetcher, $fetcherContents, [System.Text.UTF8Encoding]::new($false)
            )
            $env:APPRC_UV_PATH = $uvPath
            & $uvPath run --no-project --python '>=3.12' --script $fetcher @args
            $script:ExitCode = $LASTEXITCODE
        } finally {
            Remove-Item -LiteralPath $fetcher -Force -ErrorAction SilentlyContinue
            if ($null -eq $previousBootstrapUv) {
                Remove-Item Env:APPRC_UV_PATH -ErrorAction SilentlyContinue
            } else {
                $env:APPRC_UV_PATH = $previousBootstrapUv
            }
        }
    } elseif ($selection -eq 'local' -and $false) {
        $requirements = Join-Path $PSScriptRoot 'main-installer-requirements.txt'
        & $uvPath run --no-project --python '>=3.12' --with-requirements $requirements python $main @args
        $script:ExitCode = $LASTEXITCODE
    } else {
        & $uvPath run --no-project --python '>=3.12' --script $main @args
        $script:ExitCode = $LASTEXITCODE
    }
} finally {
    if ($script:ChangedPolicy) {
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy $script:SavedPolicy -Force
    }
}
exit $script:ExitCode
