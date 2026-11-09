@echo off
setlocal
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "DIRECTORY=%LOCALAPPDATA%\buildben\installation"
call "%DIRECTORY%\launch.cmd" %*
exit /b %ERRORLEVEL%
