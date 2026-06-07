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

if exist "%REPO%\.git" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\check-updates.ps1"
    set "UPDATE_EXIT=%ERRORLEVEL%"
    if "%UPDATE_EXIT%"=="10" (
        echo.
        echo Applying updated requirements...
        powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\setup.ps1"
        set "SETUP_EXIT=%ERRORLEVEL%"
        if not "%SETUP_EXIT%"=="0" (
            echo.
            echo [ERROR] Setup after update exited with code %SETUP_EXIT%.
            pause
            exit /b %SETUP_EXIT%
        )
        echo.
    )
)

if not exist "%REPO%\.venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run Install-Alfred.bat first.
    pause
    exit /b 1
)

call "%REPO%\.venv\Scripts\activate.bat"

cd /d "%REPO%"
"%REPO%\.venv\Scripts\python.exe" .\backend\main.py

echo.
echo Alfred has exited. Press any key to close.
pause >nul
endlocal
