@echo off
setlocal DisableDelayedExpansion

if "%~1"=="" goto :missing_script
set "<MY_PROJECT>_SCRIPT_PATH=%~1"
if not exist "%<MY_PROJECT>_SCRIPT_PATH%" goto :missing_script
set "<MY_PROJECT>_PREPARED_SCRIPT=%<MY_PROJECT>_SCRIPT_PATH%"
set "<MY_PROJECT>_STAGED_SCRIPT="

powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference = 'Stop'; try { $scriptPath = $env:<MY_PROJECT>_SCRIPT_PATH; $policy = Get-ExecutionPolicy -Scope MachinePolicy; if ($policy -eq 'Undefined') { $policy = Get-ExecutionPolicy -Scope UserPolicy }; if ($policy -in @('AllSigned', 'Restricted')) { Write-Host 'This computer requires an approved signed PowerShell script. Ask your administrator for one.' -ForegroundColor Red; exit 3 }; if ($scriptPath.StartsWith('\\wsl.localhost\', [StringComparison]::OrdinalIgnoreCase) -or $scriptPath.StartsWith('\\wsl$\', [StringComparison]::OrdinalIgnoreCase)) { if ($policy -eq 'RemoteSigned') { exit 4 }; exit 0 }; if ($policy -eq 'RemoteSigned') { $internetMark = Get-Item -LiteralPath $scriptPath -Stream Zone.Identifier -ErrorAction SilentlyContinue; if ($null -ne $internetMark) { Write-Host ''; Write-Host ('Windows marked ' + [IO.Path]::GetFileName($scriptPath) + ' as downloaded from the Internet.'); Write-Host 'This will remove that mark from this file only.'; try { $answer = Read-Host 'Allow this script to run? [y/N]' } catch { exit 2 }; if ($null -eq $answer -or $answer.Trim() -notin @('y', 'yes')) { exit 2 }; Unblock-File -LiteralPath $scriptPath; if ($null -ne (Get-Item -LiteralPath $scriptPath -Stream Zone.Identifier -ErrorAction SilentlyContinue)) { throw 'The Internet mark remains on the script.' } } }; exit 0 } catch { Write-Host ('Could not prepare the PowerShell script: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }"
set "PREPARE_EXIT_CODE=%ERRORLEVEL%"
if "%PREPARE_EXIT_CODE%"=="4" goto :stage_wsl_script
if "%PREPARE_EXIT_CODE%"=="0" goto :ready
if "%PREPARE_EXIT_CODE%"=="2" exit /b 2
if "%PREPARE_EXIT_CODE%"=="3" exit /b 3
exit /b 1

:stage_wsl_script
rem -- A WSL UNC path has no Windows alternate data stream for the Internet mark.
echo This script is in a WSL folder. Windows RemoteSigned policy blocks it there.
echo A temporary copy in your Windows Temp folder can run under that policy.
set "<MY_PROJECT>_STAGE_ANSWER="
set /p "<MY_PROJECT>_STAGE_ANSWER=Copy and run the temporary script? [y/N]: "
if /i "%<MY_PROJECT>_STAGE_ANSWER%"=="y" goto :copy_wsl_script
if /i "%<MY_PROJECT>_STAGE_ANSWER%"=="yes" goto :copy_wsl_script
exit /b 2

:copy_wsl_script
if not exist "%TEMP%\" goto :staging_failed
set "<MY_PROJECT>_STAGE_DIRECTORY=%TEMP%"
if "%<MY_PROJECT>_STAGE_DIRECTORY:~0,2%"=="\\" goto :staging_failed
:choose_staged_path
set "<MY_PROJECT>_STAGED_SCRIPT=%<MY_PROJECT>_STAGE_DIRECTORY%\<my_project>-script-%RANDOM%-%RANDOM%.ps1"
if exist "%<MY_PROJECT>_STAGED_SCRIPT%" goto :choose_staged_path
copy /b "%<MY_PROJECT>_SCRIPT_PATH%" "%<MY_PROJECT>_STAGED_SCRIPT%" >nul
if errorlevel 1 goto :staging_failed
set "<MY_PROJECT>_PREPARED_SCRIPT=%<MY_PROJECT>_STAGED_SCRIPT%"
goto :ready

:staging_failed
if defined <MY_PROJECT>_STAGED_SCRIPT if exist "%<MY_PROJECT>_STAGED_SCRIPT%" del /f /q "%<MY_PROJECT>_STAGED_SCRIPT%" >nul 2>&1
echo Could not copy the PowerShell script to the Windows Temp folder.
exit /b 1

:ready
endlocal & set "<MY_PROJECT>_PREPARED_SCRIPT=%<MY_PROJECT>_PREPARED_SCRIPT%" & set "<MY_PROJECT>_STAGED_SCRIPT=%<MY_PROJECT>_STAGED_SCRIPT%"
exit /b 0

:missing_script
echo Cannot find the PowerShell script to prepare.
exit /b 1
