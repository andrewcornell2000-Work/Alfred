#Requires -Version 5.1
<#
.SYNOPSIS
    Builds Alfred-Install.exe and Alfred.exe (desktop UI) via ps2exe.
#>

param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

if (-not $Version) {
    $versionFile = Join-Path $PSScriptRoot "VERSION"
    $Version = if (Test-Path $versionFile) { (Get-Content $versionFile -Raw).Trim() } else { "2.0.0" }
}

Write-Host ""
Write-Host "Alfred Installer Builder" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Install ps2exe if needed
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "Preparing PowerShell Gallery access..." -ForegroundColor Cyan
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-Host "NuGet provider bootstrap skipped: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
    try {
        Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction Stop
    } catch {
        Write-Host "Could not mark PSGallery trusted: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }

    Write-Host "Installing ps2exe module..." -ForegroundColor Cyan
    Install-Module -Name ps2exe -Scope CurrentUser -Force -AllowClobber -Repository PSGallery
    Write-Host "ps2exe installed." -ForegroundColor Green
} else {
    Write-Host "ps2exe already installed." -ForegroundColor Green
}

Import-Module ps2exe -Force

# Build
$InputFile  = Join-Path $PSScriptRoot "Alfred-Install.ps1"
$OutputFile = Join-Path $PSScriptRoot "Alfred-Install.exe"
$IconFile   = Join-Path $PSScriptRoot "assets\alfred.ico"
$iconArg    = @{}
if (Test-Path $IconFile) { $iconArg["icon"] = $IconFile }

if (-not (Test-Path $InputFile)) {
    Write-Host "ERROR: Alfred-Install.ps1 not found at $InputFile" -ForegroundColor Red
    exit 1
}

Write-Host "Compiling $InputFile -> $OutputFile ..." -ForegroundColor Cyan

Invoke-ps2exe `
    -InputFile  $InputFile `
    -OutputFile $OutputFile `
    -Title       "Alfred Installer" `
    -Description "Alfred global AI capability installer" `
    -Version     $Version `
    @iconArg

$UiInput  = Join-Path $PSScriptRoot "ui\Alfred-App.ps1"
$UiOutput = Join-Path $PSScriptRoot "Alfred.exe"

if (Test-Path $UiInput) {
    Write-Host "Compiling $UiInput -> $UiOutput ..." -ForegroundColor Cyan
    Invoke-ps2exe `
        -InputFile  $UiInput `
        -OutputFile $UiOutput `
        -noConsole `
        -Title       "Alfred" `
        -Description "Alfred AI Capability Manager — updates, validate, repair" `
        -Version     $Version `
        @iconArg
    Write-Host "Done: $UiOutput" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done: $OutputFile" -ForegroundColor Green
Write-Host ""
Write-Host "Releasing:" -ForegroundColor White
Write-Host "  Normally you don't run this by hand. Push a version tag and GitHub Actions" -ForegroundColor Yellow
Write-Host "  (.github/workflows/release-installer.yml) builds this .exe on a Windows runner" -ForegroundColor Yellow
Write-Host "  and attaches it to the matching release:" -ForegroundColor Yellow
Write-Host "    git tag v$Version; git push origin v$Version" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To publish a manual local build instead:" -ForegroundColor DarkGray
    Write-Host "    gh release create v$Version Alfred-Install.exe Alfred.exe --title `"Alfred v$Version`" --generate-notes" -ForegroundColor DarkGray
Write-Host ""
