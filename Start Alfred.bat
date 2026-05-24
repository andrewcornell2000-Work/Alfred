@echo off
cd /d "C:\Users\ACO324\OneDrive - Maersk Group\Desktop\ai-orchestrator"
call .venv\Scripts\activate.bat
python backend/main.py
echo.
echo Alfred has exited. Press any key to close this window.
pause >nul
