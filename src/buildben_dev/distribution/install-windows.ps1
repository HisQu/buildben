$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppDistribution = "buildben"
$AppCommand = "buildben"
$Repository = "HisQu/buildben"
$UvVersion = "0.12.18"
$ConfigureApp = "false"
$InstallerState = @{
    Version = $null
    VersionExplicit = $false
    SourceMode = "release"
    ExplicitUv = $null
    AssumeYes = $false
    SkipConfig = $false
    Uv = $null
    UvOrigin = "missing"
    UvBootstrapped = $false
    InstallPython = $null
    GithubClient = "curl"
}

function Show-Usage {
    @"
Usage: install-windows.cmd [OPTIONS]

Install the latest published stable source distribution by default.
Use --version for a published release or --main for an unreleased snapshot.

Options:
  -v, --version VERSION Select a published release (0.1.0 becomes v0.1.0).
  --main                Install the current main branch snapshot.
  --github-client CLIENT Use public curl or authenticated gh (default: curl).
  --uv PATH             Use a specific uv executable.
  -y, --yes             Skip the installer confirmation.
  --skip-config         Skip configuration setup.
  -h, --help            Show this help.
"@
}

function Invoke-Checked {
    param([Parameter(Mandatory)][string] $FilePath, [string[]] $Arguments = @(), [string] $Description = "Command", [AllowEmptyString()][string] $InputText)
    if ($PSBoundParameters.ContainsKey("InputText")) { $InputText | & $FilePath @Arguments }
    else { & $FilePath @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
}

function Invoke-Captured {
    param([Parameter(Mandatory)][string] $FilePath, [string[]] $Arguments = @(), [string] $Description = "Command", [AllowEmptyString()][string] $InputText)
    if ($PSBoundParameters.ContainsKey("InputText")) { $Output = $InputText | & $FilePath @Arguments }
    else { $Output = & $FilePath @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
    return ($Output | Out-String).Trim()
}

function Parse-Arguments {
    param([string[]] $Arguments)
    for ($Index = 0; $Index -lt $Arguments.Count; $Index++) {
        $Argument = $Arguments[$Index]
        switch ($Argument) {
            { $_ -in @("-v", "--version") } {
                if ($Index + 1 -ge $Arguments.Count) { throw "$Argument requires a version." }
                $Index++; $InstallerState.Version = $Arguments[$Index]; $InstallerState.VersionExplicit = $true; continue
            }
            "--github-client" {
                if ($Index + 1 -ge $Arguments.Count) { throw "--github-client requires curl or gh." }
                $Index++; $InstallerState.GithubClient = $Arguments[$Index]; continue
            }
            "--uv" {
                if ($Index + 1 -ge $Arguments.Count) { throw "--uv requires a path." }
                $Index++; $InstallerState.ExplicitUv = $Arguments[$Index]; continue
            }
            { $_ -in @("-y", "--yes") } { $InstallerState.AssumeYes = $true; continue }
            "--skip-config" { $InstallerState.SkipConfig = $true; continue }
            "--main" { $InstallerState.SourceMode = "main"; continue }
            { $_ -in @("-h", "--help") } { Write-Host (Show-Usage); return $false }
            default { throw "Unknown argument: $Argument" }
        }
    }
    if ($InstallerState.SourceMode -eq "main" -and $InstallerState.VersionExplicit) { throw "--main cannot be combined with --version." }
    if ($null -ne $InstallerState.Version) {
        $Normalized = $InstallerState.Version.TrimStart("v")
        if ($Normalized -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') { throw "Invalid release version: $($InstallerState.Version)" }
        $InstallerState.Version = "v$Normalized"
    }
    return $true
}

function Set-UvPath {
    param([Parameter(Mandatory)][string] $Path, [Parameter(Mandatory)][string] $Origin)
    $Command = Get-Command $Path -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { $Candidate = $Command.Source }
    else { $Resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue; if ($null -eq $Resolved) { throw "uv executable does not exist: $Path" }; $Candidate = $Resolved.Path }
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { throw "uv executable is not a file: $Candidate" }
    & $Candidate --version *> $null
    if ($LASTEXITCODE -ne 0) { throw "The supplied executable does not appear to be uv: $Candidate" }
    $InstallerState.Uv = $Candidate; $InstallerState.UvOrigin = $Origin
}

function Find-Uv {
    if (-not [string]::IsNullOrWhiteSpace($InstallerState.ExplicitUv)) { Set-UvPath -Path $InstallerState.ExplicitUv -Origin "explicit"; return }
    $Command = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { Set-UvPath -Path $Command.Source -Origin "system"; return }
    $InstallerState.Uv = $null; $InstallerState.UvOrigin = "missing"
}

function Install-PermanentUv {
    $UvDirectory = Join-Path $HOME ".local\bin"
    New-Item -ItemType Directory -Force -Path $UvDirectory | Out-Null
    Write-Host "Installing uv $UvVersion permanently in $UvDirectory..."
    Invoke-RestMethod "https://astral.sh/uv/$UvVersion/install.ps1" | Invoke-Expression
    Set-UvPath -Path (Join-Path $UvDirectory "uv.exe") -Origin "per-user"
    $InstallerState.UvBootstrapped = $true
}

function Confirm-Plan {
    $SourceDescription = if ($InstallerState.SourceMode -eq "main") { "main (unreleased snapshot)" } elseif ($null -eq $InstallerState.Version) { "latest published release" } else { "published release $($InstallerState.Version)" }
    Write-Host "Install $SourceDescription; transport: $($InstallerState.GithubClient); uv: $($InstallerState.UvOrigin)"
    if ($InstallerState.SkipConfig -or $ConfigureApp -ne "true") { Write-Host "Configuration setup will be skipped." }
    elseif ($InstallerState.AssumeYes) { }
    if ($InstallerState.AssumeYes) { return $true }
    $Answer = Read-Host "Continue? $(if ($InstallerState.UvOrigin -eq 'missing') { 'uv will be installed permanently. Enter y/yes or n/no' } else { '[y/N]' })"
    if ($Answer.Trim().ToLowerInvariant() -in @("y", "yes")) { return $true }
    Write-Host "Installation cancelled."; return $false
}

function Update-ToolPath {
    & $InstallerState.Uv tool update-shell
    if ($LASTEXITCODE -ne 0) { Write-Warning "uv could not update the tool executable PATH. Open a new shell or add the directory from 'uv tool dir --bin' to PATH." }
}

function Find-InstallationPython {
    foreach ($PythonVersion in @("3.13", "3.12")) {
        $Candidate = & $InstallerState.Uv python find --system --no-project --no-python-downloads $PythonVersion 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Candidate | Out-String))) { $InstallerState.InstallPython = ($Candidate | Out-String).Trim(); return }
    }
    Invoke-Checked -FilePath $InstallerState.Uv -Arguments @("python", "install", "3.12") -Description "Installing managed Python 3.12"
    $Candidate = & $InstallerState.Uv python find --system --no-project 3.12
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Candidate | Out-String))) { $InstallerState.InstallPython = ($Candidate | Out-String).Trim(); return }
    throw "uv could not provide its managed Python 3.12 interpreter."
}

function Install-FromSource {
    Find-InstallationPython
    $TemporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $TemporaryDirectory | Out-Null
$PythonCode = @'
import json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path, PurePosixPath
uv, client, repo, temp, distribution, source_mode, bootstrap, *requested = sys.argv[1:]
requested = requested[0] if requested else ""
root = Path(temp)
version_re = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
def normalize(value): return re.sub(r"[-_.]+", "-", value).lower()
def run_powershell(script, variables):
    environment = os.environ | variables
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], check=True, text=True, capture_output=True, env=environment).stdout
def gh_api(path):
    return run_powershell("gh api $env:BUILDBEN_INSTALLER_GH_ENDPOINT; exit $LASTEXITCODE", {"BUILDBEN_INSTALLER_GH_ENDPOINT": path})
def public_json(url):
    environment = os.environ | {"BUILDBEN_INSTALLER_HTTP_URL": url}
    script = "$ProgressPreference='SilentlyContinue'; Invoke-RestMethod -Uri $env:BUILDBEN_INSTALLER_HTTP_URL | ConvertTo-Json -Depth 100 -Compress"
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], check=True, text=True, capture_output=True, env=environment).stdout
def public_download(url, destination):
    environment = os.environ | {"BUILDBEN_INSTALLER_HTTP_URL": url, "BUILDBEN_INSTALLER_HTTP_FILE": str(destination)}
    script = "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:BUILDBEN_INSTALLER_HTTP_URL -OutFile $env:BUILDBEN_INSTALLER_HTTP_FILE"
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], check=True, env=environment)
if source_mode == "main":
    endpoint = f"/repos/{repo}/commits/main"
    response = gh_api(endpoint) if client == "gh" else public_json(f"https://api.github.com{endpoint}")
    try: commit = json.loads(response).get("sha")
    except (ValueError, TypeError, AttributeError) as exc: raise SystemExit("GitHub returned an invalid main commit SHA.") from exc
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit): raise SystemExit("GitHub returned an invalid main commit SHA.")
    print(f"Source: main ({commit})")
    archive = root / "main-source.tar.gz"
    endpoint = f"/repos/{repo}/tarball/{commit}"
    if client == "gh":
        gh = shutil.which("gh")
        if gh is None: raise SystemExit("GitHub CLI executable was not found.")
        with archive.open("wb") as output: subprocess.run([gh, "api", endpoint], stdout=output, check=True)
    else: public_download(f"https://api.github.com{endpoint}", archive)
    version = None
    source_ref = commit
else:
    if requested:
        if not re.fullmatch(r"v" + version_re.pattern[1:-1], requested): raise SystemExit("Malformed release tag")
        endpoint = f"/repos/{repo}/releases/tags/{requested}"
    else: endpoint = f"/repos/{repo}/releases/latest"
    response = gh_api(endpoint) if client == "gh" else public_json(f"https://api.github.com{endpoint}")
    try: release = json.loads(response)
    except (ValueError, TypeError) as exc: raise SystemExit("GitHub returned invalid release JSON") from exc
    if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False: raise SystemExit("Selected GitHub release is not a published stable release")
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not re.fullmatch(r"v" + version_re.pattern[1:-1], tag): raise SystemExit("GitHub release has a malformed tag")
    if requested and tag != requested: raise SystemExit("GitHub returned a different release tag")
    version = tag[1:]
    source_ref = tag
    assets = release.get("assets")
    if not isinstance(assets, list): raise SystemExit("GitHub release has no asset list")
    matching = []
    for asset in assets:
        if not isinstance(asset, dict): continue
        name, url = asset.get("name"), asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(url, str) and name.endswith(".tar.gz") and name[:-7].endswith("-" + version) and normalize(name[:-7][:-(len(version)+1)]) == normalize(distribution): matching.append((name, url))
    if len(matching) != 1: raise SystemExit(f"Expected exactly one matching source distribution, found {len(matching)}")
    name, url = matching[0]
    archive = root / name
    if client == "gh":
        run_powershell("gh release download $env:BUILDBEN_INSTALLER_GH_TAG --repo $env:BUILDBEN_INSTALLER_GH_REPO --pattern $env:BUILDBEN_INSTALLER_GH_PATTERN --dir $env:BUILDBEN_INSTALLER_GH_DIR; exit $LASTEXITCODE", {"BUILDBEN_INSTALLER_GH_TAG": tag, "BUILDBEN_INSTALLER_GH_REPO": repo, "BUILDBEN_INSTALLER_GH_PATTERN": name, "BUILDBEN_INSTALLER_GH_DIR": temp})
    else: public_download(url, archive)
if not archive.is_file() or archive.stat().st_size == 0: raise SystemExit("Source archive download is empty")
with tarfile.open(archive, "r:gz") as package:
    members = package.getmembers(); roots = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name or re.match(r"^[A-Za-z]:", member.name): raise SystemExit("Source archive contains an unsafe path")
        if member.issym() or member.islnk() or not (member.isdir() or member.isfile()): raise SystemExit("Source archive contains links or special files")
        if path.parts: roots.add(path.parts[0])
    if len(roots) != 1: raise SystemExit("Source archive must contain exactly one project root")
    (root / "source").mkdir()
    package.extractall(root / "source", filter="data")
project_root = root / "source" / next(iter(roots))
pyproject, lock = project_root / "pyproject.toml", project_root / "uv.lock"
if not pyproject.is_file() or not lock.is_file(): raise SystemExit("Source must contain pyproject.toml and uv.lock; this source is not installable")
import tomllib
with pyproject.open("rb") as stream: project = tomllib.load(stream).get("project", {})
project_version = project.get("version")
if normalize(project.get("name", "")) != normalize(distribution) or not isinstance(project_version, str) or not project_version or (source_mode == "release" and project_version != version): raise SystemExit("Source project metadata does not match selected source")
version = project_version
lifecycle = project_root / "src" / "buildben_dev" / "distribution" / "lifecycle.py"
if lifecycle.is_file():
    record = [sys.executable, str(lifecycle), "record", "--uv", uv, "--version", version, "--source-ref", source_ref]
    if bootstrap == "true": record.append("--uv-bootstrapped")
    subprocess.run([*record, "--check"], cwd=project_root, check=True)
else:
    print("WARNING: this older source has no lifecycle helper; only direct uv tool uninstall is available.")
subprocess.run([uv, "export", "--locked", "--no-dev", "--no-default-groups", "--no-emit-project", "--format", "requirements.txt", "--output-file", str(root / "runtime-requirements.txt")], cwd=project_root, check=True)
subprocess.run([uv, "tool", "install", "--force", "--refresh", "--python", sys.executable, "--with-requirements", str(root / "runtime-requirements.txt"), str(project_root)], check=True)
if lifecycle.is_file(): subprocess.run(record, cwd=project_root, check=True)
'@
    try {
        $Bootstrap = if ($InstallerState.UvBootstrapped) { "true" } else { "false" }
        $PythonArguments = @("-", $InstallerState.Uv, $InstallerState.GithubClient, $Repository, $TemporaryDirectory, $AppDistribution, $InstallerState.SourceMode, $Bootstrap)
        if ($null -ne $InstallerState.Version) { $PythonArguments += $InstallerState.Version }
        Invoke-Checked -FilePath $InstallerState.InstallPython -Arguments $PythonArguments -InputText $PythonCode -Description "$AppDistribution source installation"
        Update-ToolPath
    }
    finally { Remove-Item -LiteralPath $TemporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue }
}


function Configure-InstalledApplication {
    if ($InstallerState.SkipConfig -or $ConfigureApp -ne "true") { return }
    $ToolBin = Invoke-Captured -FilePath $InstallerState.Uv -Arguments @("tool", "dir", "--bin") -Description "Locating the installed command"
    $Executable = Join-Path $ToolBin "$AppCommand.exe"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Installed command was not found: $Executable" }
    Invoke-Checked -FilePath $Executable -Arguments @("config", "setup") -Description "Configuration setup"
}

function Invoke-Main {
    param([string[]] $Arguments)
    if (-not (Parse-Arguments -Arguments $Arguments)) { return }
    Find-Uv
    if (-not (Confirm-Plan)) { return }
    if ($InstallerState.UvOrigin -eq "missing") { Install-PermanentUv }
    Install-FromSource
    Configure-InstalledApplication
    Write-Host "`n$AppDistribution setup completed successfully."
    Write-Host "If '$AppCommand' is not available immediately, open a new shell."
}

try { Invoke-Main -Arguments $args }
catch { Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red; Write-Host "`nInstallation incomplete. Re-run the installer." -ForegroundColor Yellow; exit 1 }