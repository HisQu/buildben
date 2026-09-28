@echo off
setlocal DisableDelayedExpansion
call "%~dp0src\<my_project>_dev\distribution\install-windows.cmd" %*
set "INSTALL_EXIT_CODE=%ERRORLEVEL%"
exit /b %INSTALL_EXIT_CODE%
