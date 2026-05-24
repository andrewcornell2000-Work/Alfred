@echo off
setlocal

:: Resolve repo root from this script's location (portable — no hardcoded paths)
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

:: Add portable Node.js to PATH if a local copy lives under .\node\
if exist "%REPO%\node\node.exe" (
    set "PATH=%REPO%\node;%PATH%"
)

:: Activate Python virtual environment
if not exist "%REPO%\.venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run setup.ps1 first.
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
