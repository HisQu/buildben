@echo off
__APPRC_BASE_PYTHON__ "%~dp0uninstall.py" --directory "%~dp0" %*
exit /b %ERRORLEVEL%
