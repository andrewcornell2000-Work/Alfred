@echo off
setlocal

:: Resolve repo root from this script's location (portable — no hardcoded paths)
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

:: Refresh PATH from Windows environment before checking installed tools
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"

:: Add npm global CLI shims to PATH (codex.cmd / claude.cmd on Windows)
if exist "%APPDATA%\npm" (
    set "PATH=%APPDATA%\npm;%PATH%"
)

for /f "delims=" %%I in ('npm prefix -g 2^>nul') do if exist "%%I" set "PATH=%%I;%PATH%"

echo.
echo =====================================================
echo   Alfred Installer
echo =====================================================
echo.

:: Run setup.ps1 with execution policy bypass
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\setup.ps1"
set SETUP_EXIT=%ERRORLEVEL%

echo.

if %SETUP_EXIT% equ 2 (
    echo [ERROR] Python is not installed. Alfred cannot run.
    echo.
    echo   Install Python 3.10+ from https://www.python.org/downloads/
    echo   IMPORTANT: tick "Add Python to PATH" during install.
    echo   Then double-click Install-Alfred.bat again.
    echo.
    pause
    exit /b 2
)

if %SETUP_EXIT% equ 1 (
    echo [ACTION REQUIRED] API keys are missing.
    echo.
    echo   1. In the alfred folder, copy .env.template to .env
    echo   2. Open .env in Notepad and add your keys:
    echo        OPENAI_API_KEY    ^<^^ from https://platform.openai.com/api-keys
    echo        ANTHROPIC_API_KEY ^<^^ from https://console.anthropic.com/settings/keys
    echo   3. Double-click Install-Alfred.bat again.
    echo.
    pause
    exit /b 1
)

if %SETUP_EXIT% neq 0 (
    echo [ERROR] Setup exited with code %SETUP_EXIT%. Review the output above.
    echo         Fix any issues listed, then double-click Install-Alfred.bat again.
    echo.
    pause
    exit /b %SETUP_EXIT%
)

:: All prerequisites met — launch Alfred
echo Starting Alfred...
echo.
call "%REPO%\run-alfred.bat"

endlocal
