$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest


# == Application settings =====================================================

$AppDistribution = "<my_project>"
$AppCommand = "<my_project>"
$Repository = "https://github.com/<github_username>/<my_project>.git"
$DefaultRef = "main"
$UvVersion = "0.12.18"
$AssetEnvName = "<MY_PROJECT>_INSTALLER_ASSET_DIR"


# == Installer state ==========================================================

$RequestedMode = "auto"
$Mode = $null
$Version = $null
$WheelPath = $null
$DevPath = $null
$ExplicitUv = $null
$AssumeYes = $false
$SkipConfig = $false
$ScriptDir = $null
$Uv = $null
$UvOrigin = "missing"
$OfflinePython = $null


# == Utility functions ========================================================

function Show-Usage {
    @"
Usage: install-windows.cmd [OPTIONS]

Default mode: install one matching wheel beside this installer, if present;
otherwise install from Git. A streamed script uses Git mode.

Modes (choose at most one):
  --git                 Install from the Git repository.
  -w, --wheel [PATH]    Install from a local wheelhouse. If PATH is omitted,
                        detect the application wheel beside this installer.
  -d, --dev [PATH]      Sync an existing checkout. PATH defaults to the
                        current directory.

Options:
  -v, --version VERSION Install a Git tag (0.1.0 becomes v0.1.0).
  --uv PATH             Use a specific uv executable.
  -y, --yes             Skip the installer confirmation.
  --skip-config         Skip "$AppCommand config setup".
  -h, --help            Show this help.
"@
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string] $FilePath,
        [string[]] $Arguments = @(),
        [string] $Description = "Command"
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Captured {
    param(
        [Parameter(Mandatory)][string] $FilePath,
        [string[]] $Arguments = @(),
        [string] $Description = "Command"
    )

    $Output = & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
    return ($Output | Out-String).Trim()
}


# == Argument parsing =========================================================

function Set-RequestedMode {
    param([Parameter(Mandatory)][string] $Value)
    if ($script:RequestedMode -ne "auto") {
        throw "Installation modes are mutually exclusive."
    }
    $script:RequestedMode = $Value
}

function Parse-Arguments {
    param([string[]] $Arguments)

    for ($Index = 0; $Index -lt $Arguments.Count; $Index++) {
        $Argument = $Arguments[$Index]
        switch ($Argument) {
            "--git" {
                Set-RequestedMode "git"
                continue
            }
            { $_ -in @("-w", "--wheel") } {
                Set-RequestedMode "wheel"
                if (
                    $Index + 1 -lt $Arguments.Count -and
                    -not $Arguments[$Index + 1].StartsWith("-")
                ) {
                    $Index++
                    $script:WheelPath = $Arguments[$Index]
                }
                continue
            }
            { $_ -in @("-d", "--dev") } {
                Set-RequestedMode "dev"
                if (
                    $Index + 1 -lt $Arguments.Count -and
                    -not $Arguments[$Index + 1].StartsWith("-")
                ) {
                    $Index++
                    $script:DevPath = $Arguments[$Index]
                }
                else {
                    $script:DevPath = "."
                }
                continue
            }
            { $_ -in @("-v", "--version") } {
                if ($Index + 1 -ge $Arguments.Count) {
                    throw "$Argument requires a version."
                }
                $Index++
                $script:Version = $Arguments[$Index]
                continue
            }
            "--uv" {
                if ($Index + 1 -ge $Arguments.Count) {
                    throw "--uv requires a path."
                }
                $Index++
                $script:ExplicitUv = $Arguments[$Index]
                continue
            }
            { $_ -in @("-y", "--yes") } {
                $script:AssumeYes = $true
                continue
            }
            "--skip-config" {
                $script:SkipConfig = $true
                continue
            }
            { $_ -in @("-h", "--help") } {
                Write-Host (Show-Usage)
                return $false
            }
            default {
                throw "Unknown argument: $Argument"
            }
        }
    }
    return $true
}


# == Installer location and mode =============================================

function Resolve-InstallerAssetDir {
    $AssetSetting = Get-Item -LiteralPath "Env:$AssetEnvName" -ErrorAction SilentlyContinue
    if ($null -ne $AssetSetting -and -not [string]::IsNullOrWhiteSpace($AssetSetting.Value)) {
        if (-not (Test-Path -LiteralPath $AssetSetting.Value -PathType Container)) {
            throw "Installer asset directory does not exist: $($AssetSetting.Value)"
        }
        $script:ScriptDir = (Resolve-Path -LiteralPath $AssetSetting.Value).Path
    }
    elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $script:ScriptDir = $PSScriptRoot
    }
}

function Get-LocalApplicationWheels {
    if ([string]::IsNullOrWhiteSpace($ScriptDir)) {
        return @()
    }

    $Prefix = $AppDistribution.ToLowerInvariant().Replace("-", "_")
    $Candidates = @(
        foreach ($Directory in @($ScriptDir, (Join-Path $ScriptDir "wheels"))) {
            if (Test-Path -LiteralPath $Directory -PathType Container) {
                Get-ChildItem `
                    -LiteralPath $Directory `
                    -Filter "$Prefix-*.whl" `
                    -File |
                    ForEach-Object { $_.FullName }
            }
        }
    )
    return @($Candidates | Sort-Object -Unique)
}

function Select-DetectedWheel {
    $Candidates = @(Get-LocalApplicationWheels)
    if ($Candidates.Count -ne 1) {
        throw "Expected exactly one $AppDistribution wheel beside this installer."
    }
    $script:WheelPath = $Candidates[0]
}

function Resolve-InstallationMode {
    switch ($RequestedMode) {
        "git" { $script:Mode = "git" }
        "dev" {
            $script:Mode = "dev"
            if ([string]::IsNullOrWhiteSpace($DevPath)) {
                $script:DevPath = "."
            }
        }
        "wheel" {
            $script:Mode = "wheel"
            if ([string]::IsNullOrWhiteSpace($WheelPath)) {
                Select-DetectedWheel
            }
        }
        "auto" {
            $Candidates = @(Get-LocalApplicationWheels)
            if ($Candidates.Count -eq 1) {
                $script:Mode = "wheel"
                $script:WheelPath = $Candidates[0]
            }
            else {
                $script:Mode = "git"
            }
        }
        default { throw "Unknown installation mode: $RequestedMode" }
    }

    if ($Mode -ne "git" -and $null -ne $Version) {
        throw "--version is only valid for Git installation."
    }
    if ($Mode -eq "wheel") {
        $ResolvedWheel = Resolve-Path -LiteralPath $WheelPath -ErrorAction SilentlyContinue
        if ($null -eq $ResolvedWheel) {
            throw "Wheel does not exist: $WheelPath"
        }
        $script:WheelPath = $ResolvedWheel.Path
    }
    if ($Mode -eq "dev") {
        $ResolvedProject = Resolve-Path -LiteralPath $DevPath -ErrorAction SilentlyContinue
        if ($null -eq $ResolvedProject) {
            throw "Development checkout does not exist: $DevPath"
        }
        $script:DevPath = $ResolvedProject.Path
        if (-not (Test-Path -LiteralPath (Join-Path $DevPath "pyproject.toml") -PathType Leaf)) {
            throw "No pyproject.toml found in development checkout: $DevPath"
        }
    }
}


# == uv discovery and bootstrap ==============================================

function Set-UvPath {
    param(
        [Parameter(Mandatory)][string] $Path,
        [Parameter(Mandatory)][string] $Origin
    )

    $Command = Get-Command $Path -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) {
        $Candidate = $Command.Source
    }
    else {
        $Resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
        if ($null -eq $Resolved) {
            throw "uv executable does not exist: $Path"
        }
        $Candidate = $Resolved.Path
    }
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        throw "uv executable is not a file: $Candidate"
    }
    & $Candidate --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The supplied executable does not appear to be uv: $Candidate"
    }
    $script:Uv = $Candidate
    $script:UvOrigin = $Origin
}

function Find-Uv {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitUv)) {
        Set-UvPath -Path $ExplicitUv -Origin "explicit"
        return
    }
    if (-not [string]::IsNullOrWhiteSpace($ScriptDir)) {
        foreach ($Candidate in @(
            (Join-Path $ScriptDir "uv.exe"),
            (Join-Path $ScriptDir "uv\uv.exe")
        )) {
            if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
                Set-UvPath -Path $Candidate -Origin "local"
                return
            }
        }
    }
    $Command = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) {
        Set-UvPath -Path $Command.Source -Origin "system"
        return
    }
    $script:Uv = $null
    $script:UvOrigin = "missing"
}

function Install-PermanentUv {
    if ($Mode -eq "wheel") {
        throw "Offline installation needs local uv. Use --uv PATH or install uv first."
    }
    $UvDirectory = Join-Path $HOME ".local\bin"
    New-Item -ItemType Directory -Force -Path $UvDirectory | Out-Null
    $InstallerUrl = "https://astral.sh/uv/$UvVersion/install.ps1"
    $PreviousInstallDir = [Environment]::GetEnvironmentVariable("UV_INSTALL_DIR", "Process")
    Write-Host ""
    Write-Host "Installing uv $UvVersion permanently in $UvDirectory..."
    try {
        $env:UV_INSTALL_DIR = $UvDirectory
        Invoke-RestMethod $InstallerUrl | Invoke-Expression
    }
    finally {
        if ($null -eq $PreviousInstallDir) {
            Remove-Item Env:UV_INSTALL_DIR -ErrorAction SilentlyContinue
        }
        else {
            $env:UV_INSTALL_DIR = $PreviousInstallDir
        }
    }
    Set-UvPath -Path (Join-Path $UvDirectory "uv.exe") -Origin "per-user"
}


# == Plan and confirmation ====================================================

function Get-GitRef {
    if ([string]::IsNullOrWhiteSpace($Version)) { return $DefaultRef }
    if ($Version.StartsWith("v")) { return $Version }
    return "v$Version"
}

function Show-Plan {
    Write-Host ""
    Write-Host "$AppDistribution installation plan"
    Write-Host ""
    if ($Mode -eq "git") {
        Write-Host "Mode:`n  Online Git installation`n"
        Write-Host "1. Use $UvOrigin uv."
        if ($UvOrigin -eq "missing") {
            Write-Host "   If you continue, uv $UvVersion will be installed permanently in $HOME\.local\bin."
        }
        else {
            Write-Host "   $Uv"
        }
        Write-Host "`n2. Install or update $AppDistribution from:`n   $Repository"
        Write-Host "   Git ref: $(Get-GitRef)`n"
    }
    elseif ($Mode -eq "wheel") {
        Write-Host "Mode:`n  Offline wheel installation`n"
        Write-Host "Application wheel:`n  $WheelPath`n"
        $UvDescription = if ($null -eq $Uv) { "not found" } else { $Uv }
        Write-Host "1. Use local $UvOrigin uv: $UvDescription"
        Write-Host "2. Install from local wheels. Network access, Python downloads, and source builds are disabled.`n"
    }
    else {
        Write-Host "Mode:`n  Development environment`n"
        Write-Host "1. Use $UvOrigin uv."
        if ($UvOrigin -eq "missing") {
            Write-Host "   If you continue, uv $UvVersion will be installed permanently in $HOME\.local\bin."
        }
        else {
            Write-Host "   $Uv"
        }
        Write-Host "`n2. Synchronize the checkout with uv sync:`n   $DevPath`n"
    }
    if ($SkipConfig) {
        Write-Host "3. Skip $AppCommand config setup.`n"
    }
    elseif ($Mode -eq "dev") {
        Write-Host "3. Run $AppCommand config setup in the checkout.`n"
    }
    else {
        Write-Host "3. Run $AppCommand config setup after installation.`n"
    }
}

function Confirm-Plan {
    if ($AssumeYes) {
        if ($UvOrigin -eq "missing" -and $Mode -eq "wheel") {
            throw "Offline installation needs local uv. Use --uv PATH or install uv first."
        }
        return $true
    }

    if ($UvOrigin -eq "missing" -and $Mode -eq "wheel") {
        $Response = Read-Host "Enter a path to local uv, or n/no to cancel"
        $Normalized = $Response.Trim().ToLowerInvariant()
        if ($Normalized -in @("", "n", "no")) {
            Write-Host "`nInstallation cancelled."
            return $false
        }
        Set-UvPath -Path $Response.Trim().Trim('"') -Origin "interactive"
        return $true
    }

    if ($UvOrigin -eq "missing") {
        $Response = Read-Host "Continue? uv will be installed permanently. Enter y/yes or n/no"
        $Normalized = $Response.Trim().ToLowerInvariant()
        if ($Normalized -in @("y", "yes")) { return $true }
        if ($Normalized -in @("", "n", "no")) {
            Write-Host "`nInstallation cancelled."
            return $false
        }
        throw "Enter y/yes or n/no."
    }

    $Response = Read-Host "Continue? [y/N]"
    if ($Response.Trim().ToLowerInvariant() -in @("y", "yes")) {
        return $true
    }
    Write-Host "`nInstallation cancelled."
    return $false
}


# == Installation ============================================================

function Update-ToolPath {
    & $Uv tool update-shell
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "uv could not update the tool executable PATH. Open a new shell or add the directory from 'uv tool dir --bin' to PATH."
    }
}

function Install-FromGit {
    $Git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $Git) {
        throw "Git is required for installation from the repository."
    }
    $Ref = Get-GitRef
    Write-Host "`nChecking access to $Repository at $Ref..."
    & $Git.Source ls-remote --exit-code $Repository $Ref *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot access Git ref '$Ref'. Check Git installation and repository access."
    }
    Write-Host "`nInstalling $AppDistribution from Git..."
    Invoke-Checked -FilePath $Uv -Arguments @(
        "tool", "install", "--force", "--refresh", "git+$Repository@$Ref"
    ) -Description "$AppDistribution Git installation"
    Update-ToolPath
}

function Install-FromWheel {
    $WheelDirectory = Split-Path -Parent $WheelPath
    $script:OfflinePython = $null
    foreach ($PythonVersion in @("3.13", "3.12")) {
        $Candidate = & $Uv python find --no-project --no-python-downloads $PythonVersion 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Candidate | Out-String))) {
            $script:OfflinePython = ($Candidate | Out-String).Trim()
            break
        }
    }
    if ([string]::IsNullOrWhiteSpace($OfflinePython)) {
        throw "Offline installation requires an existing Python 3.12 or 3.13 interpreter."
    }

    $Arguments = @(
        "tool", "install", "--force", "--offline", "--no-index",
        "--no-python-downloads", "--no-build", "--python", $OfflinePython,
        "--find-links", $WheelDirectory
    )
    if (-not [string]::IsNullOrWhiteSpace($ScriptDir)) {
        $BundledWheelDirectory = Join-Path $ScriptDir "wheels"
        if (
            (Test-Path -LiteralPath $BundledWheelDirectory -PathType Container) -and
            $BundledWheelDirectory -ne $WheelDirectory
        ) {
            $Arguments += @("--find-links", $BundledWheelDirectory)
        }
    }
    $Arguments += $WheelPath
    Write-Host "`nInstalling $AppDistribution from local wheels..."
    Invoke-Checked -FilePath $Uv -Arguments $Arguments -Description "$AppDistribution offline installation"
    Update-ToolPath
}

function Configure-InstalledApplication {
    if ($SkipConfig) { return }
    $ToolBin = Invoke-Captured `
        -FilePath $Uv `
        -Arguments @("tool", "dir", "--bin") `
        -Description "Locating the installed command"
    $Executable = Join-Path $ToolBin "$AppCommand.exe"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Installed command was not found: $Executable"
    }
    Write-Host "`nRunning configuration setup..."
    Invoke-Checked -FilePath $Executable -Arguments @("config", "setup") -Description "Configuration setup"
}

function Initialize-Development {
    $HasLock = Test-Path -LiteralPath (Join-Path $DevPath "uv.lock") -PathType Leaf
    Push-Location $DevPath
    try {
        Write-Host "`nSynchronizing development environment..."
        if ($HasLock) {
            Invoke-Checked -FilePath $Uv -Arguments @("sync", "--locked") -Description "Development synchronization"
        }
        else {
            Invoke-Checked -FilePath $Uv -Arguments @("sync") -Description "Development synchronization"
        }
        if (-not $SkipConfig) {
            if ($HasLock) {
                Invoke-Checked -FilePath $Uv -Arguments @("run", "--locked", $AppCommand, "config", "setup") -Description "Configuration setup"
            }
            else {
                Invoke-Checked -FilePath $Uv -Arguments @("run", $AppCommand, "config", "setup") -Description "Configuration setup"
            }
        }
    }
    finally {
        Pop-Location
    }
}


# == Main ====================================================================

function Invoke-Main {
    param([string[]] $Arguments)

    if (-not (Parse-Arguments -Arguments $Arguments)) { return }
    Resolve-InstallerAssetDir
    Resolve-InstallationMode
    Find-Uv
    Show-Plan
    if (-not (Confirm-Plan)) { return }
    if ($UvOrigin -eq "missing") { Install-PermanentUv }

    if ($Mode -eq "git") {
        Install-FromGit
        Configure-InstalledApplication
    }
    elseif ($Mode -eq "wheel") {
        Install-FromWheel
        Configure-InstalledApplication
    }
    else {
        Initialize-Development
    }

    Write-Host "`n$AppDistribution setup completed successfully."
    if ($Mode -ne "dev") {
        Write-Host "If '$AppCommand' is not available immediately, open a new shell."
    }
}

try {
    Invoke-Main -Arguments $args
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nInstallation incomplete. Re-run the installer." -ForegroundColor Yellow
    exit 1
}
