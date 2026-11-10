$ErrorActionPreference = 'Stop'
& __APPRC_BASE_PYTHON__ (Join-Path $PSScriptRoot 'management.py') uninstall --directory $PSScriptRoot @args
exit $LASTEXITCODE
