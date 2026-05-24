@echo off
setlocal

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

start powershell.exe -NoExit -NoProfile -Command "Set-Location -LiteralPath '%REPO%'; Write-Host 'Alfred dev terminal - project root ready.' -ForegroundColor Cyan"

endlocal
