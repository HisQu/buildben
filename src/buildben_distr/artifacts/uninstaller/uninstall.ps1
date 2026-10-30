$ErrorActionPreference = 'Stop'
& __APPRC_BASE_PYTHON__ (Join-Path $PSScriptRoot 'uninstall.py') --directory $PSScriptRoot @args
exit $LASTEXITCODE
