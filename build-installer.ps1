#Requires -Version 5.1
<#
.SYNOPSIS
    Compiles Alfred-Install.ps1 into Alfred-Install.exe using ps2exe.
.DESCRIPTION
    Installs ps2exe if not present, then compiles the installer.
    Upload Alfred-Install.exe to a GitHub Release so users can download and
    double-click it without needing PowerShell execution policy changes.
.EXAMPLE
    .\build-installer.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Alfred Installer Builder" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Install ps2exe if needed
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "Installing ps2exe module..." -ForegroundColor Cyan
    Install-Module -Name ps2exe -Scope CurrentUser -Force -AllowClobber
    Write-Host "ps2exe installed." -ForegroundColor Green
} else {
    Write-Host "ps2exe already installed." -ForegroundColor Green
}

Import-Module ps2exe -Force

# Build
$InputFile  = Join-Path $PSScriptRoot "Alfred-Install.ps1"
$OutputFile = Join-Path $PSScriptRoot "Alfred-Install.exe"

if (-not (Test-Path $InputFile)) {
    Write-Host "ERROR: Alfred-Install.ps1 not found at $InputFile" -ForegroundColor Red
    exit 1
}

Write-Host "Compiling $InputFile -> $OutputFile ..." -ForegroundColor Cyan

Invoke-ps2exe `
    -InputFile  $InputFile `
    -OutputFile $OutputFile `
    -Title       "Alfred Installer" `
    -Description "Alfred AI Assistant - one-click installer" `
    -Version     "1.6.3"

Write-Host ""
Write-Host "Done: $OutputFile" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Go to https://github.com/andrewcornell2000-Work/Alfred/releases/new" -ForegroundColor Yellow
Write-Host "  2. Create a new release (e.g. v1.6.3)" -ForegroundColor Yellow
Write-Host "  3. Drag Alfred-Install.exe into the release assets" -ForegroundColor Yellow
Write-Host "  4. Anyone can download and double-click it to install Alfred" -ForegroundColor Yellow
Write-Host ""
