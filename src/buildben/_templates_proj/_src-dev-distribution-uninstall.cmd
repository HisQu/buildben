@echo off
setlocal DisableDelayedExpansion
set "PAUSE_WINDOW=1"
if not "%~1"=="" set "PAUSE_WINDOW=0"
set "PSModulePath="
if not exist "%~dp0prepare-powershell-windows.cmd" goto :missing_helper
set "BUILDBEN_PREPARED_SCRIPT="
set "BUILDBEN_STAGED_SCRIPT="
set "BUILDBEN_UNINSTALL_HELPER=%~dp0lifecycle.py"
call "%~dp0prepare-powershell-windows.cmd" "%~dp0uninstall.ps1"
set "CHECK_EXIT_CODE=%ERRORLEVEL%"
if not "%CHECK_EXIT_CODE%"=="0" goto :preflight_failed
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%BUILDBEN_PREPARED_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if defined BUILDBEN_STAGED_SCRIPT del /f /q "%BUILDBEN_STAGED_SCRIPT%" >nul 2>&1
if "%PAUSE_WINDOW%"=="1" (
    echo.
    echo Press any key to close this window.
    pause >nul
)
exit /b %EXIT_CODE%
:missing_helper
echo Cannot find prepare-powershell-windows.cmd beside this uninstaller.
set "CHECK_EXIT_CODE=1"
:preflight_failed
if defined BUILDBEN_STAGED_SCRIPT del /f /q "%BUILDBEN_STAGED_SCRIPT%" >nul 2>&1
if "%PAUSE_WINDOW%"=="1" (
    echo.
    echo Press any key to close this window.
    pause >nul
)
exit /b %CHECK_EXIT_CODE%
