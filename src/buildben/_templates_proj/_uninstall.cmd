@echo off
call "%~dp0src\<my_project>_dev\distribution\uninstall.cmd" %*
exit /b %ERRORLEVEL%
