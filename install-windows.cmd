@echo off
setlocal DisableDelayedExpansion
call "%~dp0src\buildben_dev\distribution\install-windows.cmd" %*
set "INSTALL_EXIT_CODE=%ERRORLEVEL%"
exit /b %INSTALL_EXIT_CODE%
