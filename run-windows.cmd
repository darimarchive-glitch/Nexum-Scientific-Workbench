@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\nexum.ps1" -Action Run %*
set "NEXUM_EXIT=%ERRORLEVEL%"
if not "%NEXUM_EXIT%"=="0" pause
exit /b %NEXUM_EXIT%
