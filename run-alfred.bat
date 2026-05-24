@echo off
setlocal

:: Resolve repo root from this script's location (portable — no hardcoded paths)
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

:: Add portable Node.js to PATH if a local copy lives under .\node\
if exist "%REPO%\node\node.exe" (
    set "PATH=%REPO%\node;%PATH%"
)

:: Refresh PATH from Windows environment in case setup.ps1 just updated it
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"

:: Add npm global CLI shims to PATH (codex.cmd / claude.cmd on Windows)
if exist "%APPDATA%\npm" (
    set "PATH=%APPDATA%\npm;%PATH%"
)

for /f "delims=" %%I in ('npm prefix -g 2^>nul') do if exist "%%I" set "PATH=%%I;%PATH%"

:: Check for updates if this is a git repo (requires network; skips silently if offline)
if exist "%REPO%\.git" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\check-updates.ps1"
    set UPDATE_EXIT=%ERRORLEVEL%
    if %UPDATE_EXIT% equ 10 (
        echo.
        echo Applying updated requirements...
        powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\setup.ps1"
        echo.
    )
)

:: Activate Python virtual environment
if not exist "%REPO%\.venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run Install-Alfred.bat first.
    pause
    exit /b 1
)
call "%REPO%\.venv\Scripts\activate.bat"

:: Launch Alfred
cd /d "%REPO%"
python .\backend\main.py

echo.
echo Alfred has exited. Press any key to close.
pause >nul
endlocal
