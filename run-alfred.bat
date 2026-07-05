@echo off
setlocal

:: Resolve repo root from this script's location.
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

:: Refresh PATH from Windows after setup installs tools.
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"

:: Prefer repo-local portable Node.js if present.
if exist "%REPO%\node\node.exe" (
    set "PATH=%REPO%\node;%PATH%"
)

for /d %%D in ("%REPO%\Node\node-v*-win-x64") do (
    if exist "%%~fD\node.exe" set "PATH=%%~fD;%PATH%"
)

:: Add npm global CLI shims to PATH (codex.cmd / claude.cmd on Windows).
if exist "%APPDATA%\npm" (
    set "PATH=%APPDATA%\npm;%PATH%"
)

for /f "delims=" %%I in ('npm prefix -g 2^>nul') do (
    if exist "%%I" set "PATH=%%I;%PATH%"
)

if not exist "%REPO%\.venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run Install-Alfred.bat first.
    pause
    exit /b 1
)

cd /d "%REPO%"
"%REPO%\.venv\Scripts\python.exe" -m backend.cli update
set "CLI_EXIT=%ERRORLEVEL%"

if not "%CLI_EXIT%"=="0" (
    echo.
    echo [ERROR] Alfred update/provision failed with exit code %CLI_EXIT%.
    pause
    exit /b %CLI_EXIT%
)

echo.
echo Alfred is ready. Use Cursor, Claude Code, or Codex for AI tasks.
echo.
pause >nul
endlocal
