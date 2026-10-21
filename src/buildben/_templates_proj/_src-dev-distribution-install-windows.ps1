$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# == Application settings =====================================================
$AppDistribution = "<my_project>"
$AppCommand = "<my_project>"
$Repository = "https://github.com/<github_username>/<my_project>.git"
$UvVersion = "0.12.18"
$BootstrapTag = ""
$BootstrapHelperSha256 = ""
$ConfigureApp = "<configure_app>"
$AssetEnvName = "<MY_PROJECT>_INSTALLER_ASSET_DIR"

# == Installer state ==========================================================
$RequestedMode = "auto"
$Mode = $null
$Version = $null
$DevPath = $null
$ExplicitUv = $null
$AssumeYes = $false
$SkipConfig = $false
$ScriptDir = $null
$Uv = $null
$UvOrigin = "missing"
$InstallPython = $null

function Show-Usage {
    @"
Usage: install-windows.cmd [OPTIONS]

Default mode: install the latest published release. Use --version for a
specific published release, --git for a developer installation, or --dev
to synchronize an existing checkout.

Modes (choose at most one):
  --git                 Install from the Git repository.
  -d, --dev [PATH]      Sync an existing checkout. PATH defaults to the current directory.

Options:
  -v, --version VERSION Install a published release (0.1.0 becomes v0.1.0).
  --uv PATH             Use a specific uv executable.
  -y, --yes             Skip the installer confirmation.
  --skip-config         Skip configuration setup.
  -h, --help            Show this help.
"@
}

function Invoke-Checked {
    param([Parameter(Mandatory)][string] $FilePath, [string[]] $Arguments = @(), [string] $Description = "Command")
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
}

function Invoke-Captured {
    param([Parameter(Mandatory)][string] $FilePath, [string[]] $Arguments = @(), [string] $Description = "Command")
    $Output = & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
    return ($Output | Out-String).Trim()
}

function Set-RequestedMode {
    param([Parameter(Mandatory)][string] $Value)
    if ($script:RequestedMode -ne "auto") { throw "Installation modes are mutually exclusive." }
    $script:RequestedMode = $Value
}

function Parse-Arguments {
    param([string[]] $Arguments)
    for ($Index = 0; $Index -lt $Arguments.Count; $Index++) {
        $Argument = $Arguments[$Index]
        switch ($Argument) {
            "--git" { Set-RequestedMode "git"; continue }
            { $_ -in @("-d", "--dev") } {
                Set-RequestedMode "dev"
                if ($Index + 1 -lt $Arguments.Count -and -not $Arguments[$Index + 1].StartsWith("-")) { $Index++; $script:DevPath = $Arguments[$Index] }
                else { $script:DevPath = "." }
                continue
            }
            { $_ -in @("-v", "--version") } {
                if ($Index + 1 -ge $Arguments.Count) { throw "$Argument requires a version." }
                $Index++; $script:Version = $Arguments[$Index]; continue
            }
            "--uv" {
                if ($Index + 1 -ge $Arguments.Count) { throw "--uv requires a path." }
                $Index++; $script:ExplicitUv = $Arguments[$Index]; continue
            }
            { $_ -in @("-y", "--yes") } { $script:AssumeYes = $true; continue }
            "--skip-config" { $script:SkipConfig = $true; continue }
            { $_ -in @("-h", "--help") } { Write-Host (Show-Usage); return $false }
            default { throw "Unknown argument: $Argument" }
        }
    }
    return $true
}

function Resolve-InstallerAssetDir {
    $AssetSetting = Get-Item -LiteralPath "Env:$AssetEnvName" -ErrorAction SilentlyContinue
    if ($null -ne $AssetSetting -and -not [string]::IsNullOrWhiteSpace($AssetSetting.Value)) {
        if (-not (Test-Path -LiteralPath $AssetSetting.Value -PathType Container)) { throw "Installer asset directory does not exist: $($AssetSetting.Value)" }
        $script:ScriptDir = (Resolve-Path -LiteralPath $AssetSetting.Value).Path
    }
    elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) { $script:ScriptDir = $PSScriptRoot }
}

function Resolve-InstallationMode {
    switch ($RequestedMode) {
        "git" { $script:Mode = "git" }
        "dev" {
            $script:Mode = "dev"
            if ([string]::IsNullOrWhiteSpace($DevPath)) { $script:DevPath = "." }
            $Resolved = Resolve-Path -LiteralPath $DevPath -ErrorAction SilentlyContinue
            if ($null -eq $Resolved -or -not (Test-Path -LiteralPath (Join-Path $Resolved.Path "pyproject.toml") -PathType Leaf)) { throw "No pyproject.toml found in development checkout: $DevPath" }
            $script:DevPath = $Resolved.Path
        }
        "auto" { $script:Mode = "release" }
        default { throw "Unknown installation mode: $RequestedMode" }
    }
}

function Set-UvPath {
    param([Parameter(Mandatory)][string] $Path, [Parameter(Mandatory)][string] $Origin)
    $Command = Get-Command $Path -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { $Candidate = $Command.Source }
    else { $Resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue; if ($null -eq $Resolved) { throw "uv executable does not exist: $Path" }; $Candidate = $Resolved.Path }
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { throw "uv executable is not a file: $Candidate" }
    & $Candidate --version *> $null
    if ($LASTEXITCODE -ne 0) { throw "The supplied executable does not appear to be uv: $Candidate" }
    $script:Uv = $Candidate; $script:UvOrigin = $Origin
}

function Find-Uv {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitUv)) { Set-UvPath -Path $ExplicitUv -Origin "explicit"; return }
    if (-not [string]::IsNullOrWhiteSpace($ScriptDir)) {
        foreach ($Candidate in @((Join-Path $ScriptDir "uv.exe"), (Join-Path $ScriptDir "uv\uv.exe"))) {
            if (Test-Path -LiteralPath $Candidate -PathType Leaf) { Set-UvPath -Path $Candidate -Origin "local"; return }
        }
    }
    $Command = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { Set-UvPath -Path $Command.Source -Origin "system"; return }
    $script:Uv = $null; $script:UvOrigin = "missing"
}

function Install-PermanentUv {
    $UvDirectory = Join-Path $HOME ".local\bin"
    New-Item -ItemType Directory -Force -Path $UvDirectory | Out-Null
    Write-Host "Installing uv $UvVersion permanently in $UvDirectory..."
    Invoke-RestMethod "https://astral.sh/uv/$UvVersion/install.ps1" | Invoke-Expression
    Set-UvPath -Path (Join-Path $UvDirectory "uv.exe") -Origin "per-user"
}

function Confirm-Plan {
    Write-Host "`n$AppDistribution installation plan"
    Write-Host "Mode: $Mode; uv: $UvOrigin"
    if ($Mode -eq "dev") { Write-Host "Synchronize checkout: $DevPath" }
    elseif ($Mode -eq "git") { Write-Host "Install from $Repository at $(if ($Version) { "v$($Version.TrimStart('v'))" } else { "main" })" }
    else { Write-Host "Install the selected published GitHub release." }
    if ($SkipConfig -or $ConfigureApp -ne "true") { Write-Host "Configuration setup will be skipped." }
    elseif ($Mode -eq "dev") { Write-Host "Run $AppCommand config setup in the checkout." }
    else { Write-Host "Run $AppCommand config setup after installation." }
    if ($AssumeYes) { return $true }
    $Answer = Read-Host "Continue? $(if ($UvOrigin -eq 'missing') { 'uv will be installed permanently. Enter y/yes or n/no' } else { '[y/N]' })"
    if ($Answer.Trim().ToLowerInvariant() -in @("y", "yes")) { return $true }
    Write-Host "Installation cancelled."; return $false
}

function Update-ToolPath {
    & $Uv tool update-shell
    if ($LASTEXITCODE -ne 0) { Write-Warning "uv could not update the tool executable PATH. Open a new shell or add the directory from 'uv tool dir --bin' to PATH." }
}

function Find-InstallationPython {
    foreach ($PythonVersion in @("3.13", "3.12")) {
        $Candidate = & $Uv python find --no-project --no-python-downloads $PythonVersion 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Candidate | Out-String))) { $script:InstallPython = ($Candidate | Out-String).Trim(); return }
    }
    Invoke-Checked -FilePath $Uv -Arguments @("python", "install", "3.12") -Description "Installing managed Python 3.12"
    $Candidate = & $Uv python find --no-project 3.12
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Candidate | Out-String))) { $script:InstallPython = ($Candidate | Out-String).Trim(); return }
    throw "uv could not provide its managed Python 3.12 interpreter."
}

function Install-FromRelease {
    Find-InstallationPython
    $TemporaryDirectory = $null
    try {
        $Helper = $null
        if (-not [string]::IsNullOrWhiteSpace($ScriptDir)) { $Helper = Join-Path $ScriptDir "install_release.py" }
        if ($null -eq $Helper -or -not (Test-Path -LiteralPath $Helper -PathType Leaf)) {
            if ([string]::IsNullOrWhiteSpace($BootstrapTag) -or [string]::IsNullOrWhiteSpace($BootstrapHelperSha256)) { throw "No trusted adjacent helper or stamped release source is available." }
            $TemporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString("N"))
            New-Item -ItemType Directory -Path $TemporaryDirectory | Out-Null
            $Helper = Join-Path $TemporaryDirectory "install_release.py"
            $OwnerRepo = $Repository -replace '^https://github\.com/', '' -replace '\.git$', ''
            $HelperUrl = "https://raw.githubusercontent.com/$OwnerRepo/$BootstrapTag/src/$($AppDistribution.Replace('-', '_'))_dev/distribution/install_release.py"
            Invoke-WebRequest -Uri $HelperUrl -OutFile $Helper
        }
        if (-not [string]::IsNullOrWhiteSpace($BootstrapHelperSha256)) {
            $ActualDigest = (Get-FileHash -LiteralPath $Helper -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($ActualDigest -ne $BootstrapHelperSha256) { throw "Release helper digest does not match the stamped installer." }
        }
        $OwnerRepo = $Repository -replace '^https://github\.com/', '' -replace '\.git$', ''
        $HelperArguments = @($Helper, "--repository", $OwnerRepo, "--distribution", $AppDistribution, "--uv", $Uv, "--python", $InstallPython)
        if ($null -ne $Version) { $HelperArguments += @("--version", $Version) }
        elseif (-not [string]::IsNullOrWhiteSpace($BootstrapTag)) { $HelperArguments += @("--version", $BootstrapTag) }
        if (-not [string]::IsNullOrWhiteSpace($ScriptDir)) {
            $PayloadFound = $false
            foreach ($Name in @("release-manifest.json", "runtime-requirements.txt", "runtime-constraints.txt")) { if (Test-Path -LiteralPath (Join-Path $ScriptDir $Name)) { $PayloadFound = $true } }
            if ($PayloadFound) {
                foreach ($Name in @("release-manifest.json", "runtime-requirements.txt", "runtime-constraints.txt")) { if (-not (Test-Path -LiteralPath (Join-Path $ScriptDir $Name) -PathType Leaf)) { throw "Incomplete adjacent release payload: $Name is missing." } }
                $HelperArguments += @("--asset-dir", $ScriptDir)
            }
        }
        if ($env:BUILDBEN_ASSET_HANDOFF_DIAGNOSTIC -eq "1") {
            Write-Host "[asset-handoff] PowerShell scriptdir=<$ScriptDir> helper=<$Helper>"
            foreach ($Name in @("release-manifest.json", "runtime-requirements.txt", "runtime-constraints.txt")) {
                $AssetPath = Join-Path $ScriptDir $Name
                $IsLeaf = Test-Path -LiteralPath $AssetPath -PathType Leaf
                Write-Host "[asset-handoff] PowerShell asset=<$AssetPath> leaf=$IsLeaf"
            }
        }
        Invoke-Checked -FilePath $InstallPython -Arguments $HelperArguments -Description "$AppDistribution release installation"
        Update-ToolPath
    }
    finally {
        if ($null -ne $TemporaryDirectory) { Remove-Item -LiteralPath $TemporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

function Install-FromGit {
    $Git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $Git) { throw "Git is required for installation from the repository." }
    $Ref = if ([string]::IsNullOrWhiteSpace($Version)) { "main" } elseif ($Version.StartsWith("v")) { $Version } else { "v$Version" }
    & $Git.Source ls-remote --exit-code $Repository $Ref *> $null
    if ($LASTEXITCODE -ne 0) { throw "Cannot access Git ref '$Ref'. Check Git installation and repository access." }
    Invoke-Checked -FilePath $Uv -Arguments @("tool", "install", "--force", "--refresh", "git+$Repository@$Ref") -Description "$AppDistribution Git installation"
    Update-ToolPath
}

function Configure-InstalledApplication {
    if ($SkipConfig -or $ConfigureApp -ne "true") { return }
    $ToolBin = Invoke-Captured -FilePath $Uv -Arguments @("tool", "dir", "--bin") -Description "Locating the installed command"
    $Executable = Join-Path $ToolBin "$AppCommand.exe"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Installed command was not found: $Executable" }
    Invoke-Checked -FilePath $Executable -Arguments @("config", "setup") -Description "Configuration setup"
}

function Initialize-Development {
    $HasLock = Test-Path -LiteralPath (Join-Path $DevPath "uv.lock") -PathType Leaf
    Push-Location $DevPath
    try {
        if ($HasLock) { Invoke-Checked -FilePath $Uv -Arguments @("sync", "--locked") -Description "Development synchronization" }
        else { Invoke-Checked -FilePath $Uv -Arguments @("sync") -Description "Development synchronization" }
        if (-not $SkipConfig -and $ConfigureApp -eq "true") {
            if ($HasLock) { Invoke-Checked -FilePath $Uv -Arguments @("run", "--locked", $AppCommand, "config", "setup") -Description "Configuration setup" }
            else { Invoke-Checked -FilePath $Uv -Arguments @("run", $AppCommand, "config", "setup") -Description "Configuration setup" }
        }
    }
    finally { Pop-Location }
}

function Invoke-Main {
    param([string[]] $Arguments)
    if (-not (Parse-Arguments -Arguments $Arguments)) { return }
    Resolve-InstallerAssetDir; Resolve-InstallationMode; Find-Uv
    if (-not (Confirm-Plan)) { return }
    if ($UvOrigin -eq "missing") { Install-PermanentUv }
    if ($Mode -eq "git") { Install-FromGit; Configure-InstalledApplication }
    elseif ($Mode -eq "release") { Install-FromRelease; Configure-InstalledApplication }
    else { Initialize-Development }
    Write-Host "`n$AppDistribution setup completed successfully."
    if ($Mode -ne "dev") { Write-Host "If '$AppCommand' is not available immediately, open a new shell." }
}

try { Invoke-Main -Arguments $args }
catch { Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red; Write-Host "`nInstallation incomplete. Re-run the installer." -ForegroundColor Yellow; exit 1 }
