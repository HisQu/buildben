@echo off
__APPRC_BASE_PYTHON__ "%~dp0management.py" uninstall --directory "%~dp0" %*
exit /b %ERRORLEVEL%
