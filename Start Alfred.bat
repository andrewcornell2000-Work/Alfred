@echo off
setlocal

:: Resolve repo root from this script's location (portable, no hardcoded paths)
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

:: Add npm global CLI shims to PATH (codex.cmd / claude.cmd on Windows)
if exist "%APPDATA%\npm" (
    set "PATH=%APPDATA%\npm;%PATH%"
)

call "%REPO%\run-alfred.bat"

endlocal
