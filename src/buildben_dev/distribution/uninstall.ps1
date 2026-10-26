$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Helper = Join-Path $Here 'lifecycle.py'
if (-not [string]::IsNullOrWhiteSpace($env:BUILDBEN_STAGED_SCRIPT) -and
    [System.IO.Path]::GetFullPath($env:BUILDBEN_STAGED_SCRIPT) -eq [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)) {
    if ([string]::IsNullOrWhiteSpace($env:BUILDBEN_UNINSTALL_HELPER) -or
        -not [System.IO.Path]::IsPathRooted($env:BUILDBEN_UNINSTALL_HELPER)) {
        throw 'The staged uninstaller is missing its original absolute lifecycle helper path.'
    }
    $Helper = $env:BUILDBEN_UNINSTALL_HELPER
}
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA is required for lifecycle support.' }
$Saved = Join-Path $env:LOCALAPPDATA 'buildben\installation\uninstall.cmd'
if (-not [System.IO.Path]::IsPathRooted($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA must be absolute.' }
$Candidate = $Saved
while (-not [string]::IsNullOrWhiteSpace($Candidate)) {
    if (Test-Path -LiteralPath $Candidate) {
        $Item = Get-Item -Force -LiteralPath $Candidate
        if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Lifecycle support must not use a reparse point: $Candidate" }
    }
    $Parent = Split-Path -Parent $Candidate
    if ($Parent -eq $Candidate) { break }
    $Candidate = $Parent
}
if (Test-Path -LiteralPath $Saved -PathType Leaf) {
    & $Saved @args
    exit $LASTEXITCODE
}
$Uv = $null
$Forward = [System.Collections.Generic.List[string]]::new()
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq '--uv' -and $i + 1 -lt $args.Count) { $Uv = $args[++$i]; continue }
    if ($args[$i] -in @('--yes', '--dry-run')) { $Forward.Add($args[$i]); continue }
    throw 'Without a saved receipt, recovery accepts only --uv PATH and --yes/--dry-run.'
}
if (-not $Uv) { throw 'No lifecycle receipt; pass --uv PATH for package-only recovery.' }
$UvCommand = Get-Command $Uv -CommandType Application -ErrorAction Stop
$Uv = [System.IO.Path]::GetFullPath($UvCommand.Source)
$Python = (& $Uv python find --system --no-project --no-python-downloads '>=3.12' 2>$null | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or -not $Python) { throw "No base Python available; run '$Uv tool uninstall buildben' directly." }
& $Python $Helper uninstall --uv $Uv @Forward
exit $LASTEXITCODE
