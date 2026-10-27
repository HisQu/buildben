# Repository guidance

Follow the canonical [Windows installer verification procedure](README.md#windows-installer-verification-procedure) before continuing Windows installer work. From WSL, never launch native Windows test executables (including PowerShell, Windows Python/pytest, `cmd.exe`, or Windows `uv`), directly or through helpers.

For Unix installer changes, follow the [Unix staging verification procedure](README.md#unix-installer-staging-verification). Exercise the real consumer smoke, including staging aliases, without weakening lifecycle link checks.
