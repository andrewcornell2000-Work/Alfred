@echo off
setlocal EnableExtensions

set "REPO_URL=https://github.com/andrewcornell2000-Work/Alfred.git"
set "BRANCH=main"
set "TARGET=%USERPROFILE%\Alfred"

if not "%~1"=="" set "TARGET=%~1"

echo.
echo =====================================================
echo   Alfred GitHub Bootstrap
echo =====================================================
echo.
echo Repository: %REPO_URL%
echo Target:     %TARGET%
echo.

choice /C YN /M "Install/update Alfred here and install Git if missing"
if errorlevel 2 exit /b 0

call :RefreshPath

where git >nul 2>nul
if errorlevel 1 (
    echo.
    echo Git is not installed.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] winget is not available. Install Git from https://git-scm.com/download/win, then run this again.
        pause
        exit /b 2
    )

    echo Installing Git via winget...
    winget install --id Git.Git --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Git install failed. Install Git manually, then run this again.
        pause
        exit /b 2
    )
    call :RefreshPath
)

where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git is still not on PATH. Open a new terminal or restart Windows, then run this again.
    pause
    exit /b 2
)

if exist "%TARGET%\.git" goto UpdateRepo

if exist "%TARGET%" (
    echo.
    echo [ERROR] Target folder exists but is not a Git checkout:
    echo   %TARGET%
    echo.
    echo Run this file with another target folder:
    echo   Install-From-GitHub.bat "C:\Path\To\Alfred"
    pause
    exit /b 4
)

echo.
echo Cloning Alfred...
git clone --branch "%BRANCH%" "%REPO_URL%" "%TARGET%"
if errorlevel 1 (
    echo [ERROR] Clone failed. Check GitHub access and try again.
    pause
    exit /b 5
)
goto RunInstaller

:UpdateRepo
echo.
echo Existing Alfred checkout found.

choice /C YN /M "Pull latest Alfred changes from GitHub now"
if errorlevel 2 goto RunInstaller

git -C "%TARGET%" fetch origin "%BRANCH%"
if errorlevel 1 (
    echo [WARN] Could not fetch from GitHub. Continuing with the local checkout.
    goto RunInstaller
)

git -C "%TARGET%" reset --hard "origin/%BRANCH%"
if errorlevel 1 (
    echo [ERROR] Update failed. Resolve the Git output above, then run this again.
    pause
    exit /b 5
)
goto RunInstaller

:RunInstaller
if not exist "%TARGET%\Install-Alfred.bat" (
    echo [ERROR] Install-Alfred.bat was not found in %TARGET%.
    pause
    exit /b 6
)

call "%TARGET%\Install-Alfred.bat"
exit /b %ERRORLEVEL%

:RefreshPath
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
exit /b 0
