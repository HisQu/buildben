@echo off
call "%~dp0src\buildben_dev\distribution\uninstall.cmd" %*
exit /b %ERRORLEVEL%
