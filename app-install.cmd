@echo off
setlocal
set "HERE=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HERE%src/buildben_distr\artifacts\installer\bootstrap.ps1" %*
exit /b %ERRORLEVEL%
