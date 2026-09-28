@echo off
setlocal DisableDelayedExpansion
set "PAUSE_WINDOW=1"
if not "%~1"=="" set "PAUSE_WINDOW=0"
rem -- Let Windows PowerShell use its own modules when launched from PowerShell 7.
set "PSModulePath="
if not defined <MY_PROJECT>_INSTALLER_ASSET_DIR set "<MY_PROJECT>_INSTALLER_ASSET_DIR=%~dp0"

if not exist "%~dp0prepare-powershell-windows.cmd" goto :missing_helper
set "<MY_PROJECT>_PREPARED_SCRIPT="
set "<MY_PROJECT>_STAGED_SCRIPT="
call "%~dp0prepare-powershell-windows.cmd" "%~dp0install-windows.ps1"
set "CHECK_EXIT_CODE=%ERRORLEVEL%"
if not "%CHECK_EXIT_CODE%"=="0" goto :preflight_failed

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%<MY_PROJECT>_PREPARED_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if defined <MY_PROJECT>_STAGED_SCRIPT del /f /q "%<MY_PROJECT>_STAGED_SCRIPT%" >nul 2>&1

echo.
if "%EXIT_CODE%"=="0" (
    echo <my_project> setup finished successfully.
) else (
    echo <my_project> setup failed.
    echo Installation incomplete. Re-run the installer.
)

if "%PAUSE_WINDOW%"=="1" (
    echo.
    echo Press any key to close this window.
    pause >nul
)
exit /b %EXIT_CODE%

:missing_helper
echo Cannot find prepare-powershell-windows.cmd beside this installer.
set "CHECK_EXIT_CODE=1"

:preflight_failed
if defined <MY_PROJECT>_STAGED_SCRIPT del /f /q "%<MY_PROJECT>_STAGED_SCRIPT%" >nul 2>&1
echo.
if "%CHECK_EXIT_CODE%"=="2" echo Installation cancelled.
if "%CHECK_EXIT_CODE%"=="3" echo <my_project> setup cannot continue under this PowerShell policy.
if not "%CHECK_EXIT_CODE%"=="2" if not "%CHECK_EXIT_CODE%"=="3" echo Could not prepare the PowerShell installer.
if "%PAUSE_WINDOW%"=="1" (
    echo.
    echo Press any key to close this window.
    pause >nul
)
exit /b %CHECK_EXIT_CODE%
