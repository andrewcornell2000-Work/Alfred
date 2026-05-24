@echo off
setlocal

:: Resolve repo root from this script's location.
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

call "%REPO%\run-alfred.bat"

endlocal
