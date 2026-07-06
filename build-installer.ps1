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

param(
    # Version stamped into the .exe metadata. CI passes the git tag (without the leading "v").
    [string]$Version = "2.6.2"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Alfred Installer Builder" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

$iconScript = Join-Path $PSScriptRoot "scripts\build-alfred-icon.ps1"
if (Test-Path $iconScript) {
    Write-Host "Building icon..." -ForegroundColor Cyan
    & $iconScript
}

$logoScript = Join-Path $PSScriptRoot "scripts\build-embedded-logo.ps1"
if (Test-Path $logoScript) {
    Write-Host "Building embedded wizard logo..." -ForegroundColor Cyan
    & $logoScript
}

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

$InputFile  = Join-Path $PSScriptRoot "Alfred-Install.ps1"
$OutputFile = Join-Path $PSScriptRoot "Alfred-Install.exe"
$IconFile   = Join-Path $PSScriptRoot "assets\alfred.ico"
$BuildFile  = Join-Path $env:TEMP "Alfred-Install.build.ps1"

if (-not (Test-Path $InputFile)) {
    Write-Host "ERROR: Alfred-Install.ps1 not found at $InputFile" -ForegroundColor Red
    exit 1
}

function Get-InstallerModuleBody([string]$Path) {
    $content = Get-Content $Path -Raw
    return ($content -replace '(?m)^#Requires[^\r\n]*\r?\n', '').Trim()
}

$commonPath = Join-Path $PSScriptRoot "Alfred-Common.ps1"
$commonBody = if (Test-Path $commonPath) { Get-InstallerModuleBody $commonPath } else { "" }

$moduleParts = @()
foreach ($rel in @("installer\alfred-logo-embedded.ps1", "installer\Alfred-UiCommon.ps1", "installer\Install-Progress.ps1", "installer\Install-Wizard.ps1", "installer\Update-Alert.ps1", "installer\Close-AgentApps.ps1", "installer\Repair-CooperativeLeanCtx.ps1", "installer\Install-RepoTools.ps1")) {
    $path = Join-Path $PSScriptRoot $rel
    if (-not (Test-Path $path)) {
        if ($rel -eq 'installer\Install-RepoTools.ps1') { continue }
        Write-Host "WARN: Missing $rel - GUI installer may not work in the .exe" -ForegroundColor Yellow
        continue
    }
    if ($rel -eq 'installer\Install-RepoTools.ps1') {
        $moduleParts += Get-InstallerModuleBody $path
        continue
    }
    $moduleParts += Get-InstallerModuleBody $path
}

$mainRaw = Get-Content $InputFile -Raw
$splitMarker = '# ALFRED_INSTALLER_WIZARD_START'
$split = $mainRaw -split [regex]::Escape($splitMarker), 2
if ($split.Count -lt 2) {
    throw "Could not locate '$splitMarker' in Alfred-Install.ps1"
}

$mainHead = $split[0].TrimEnd()
$mainTail = $split[1].TrimStart()
if ($commonBody) {
    $inlinePattern = '(?ms)# ALFRED_COMMON_INLINE[\s\S]*?(?=function Import-AlfredInstallerModules)'
    $mainHead = [regex]::Replace($mainHead, $inlinePattern, { $commonBody + "`n`n" })
}
$merged = ($mainHead + "`n`n" + ($moduleParts -join "`n`n") + "`n`n" + $mainTail)
Set-Content -Path $BuildFile -Value $merged -Encoding UTF8

$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile($BuildFile, [ref]$null, [ref]$parseErrors)
if ($parseErrors) {
    Write-Host "Merged installer script has parse errors:" -ForegroundColor Red
    $parseErrors | ForEach-Object { Write-Host $_.ToString() -ForegroundColor Red }
    exit 1
}

Write-Host "Compiling $BuildFile -> $OutputFile ..." -ForegroundColor Cyan

$ps2exeArgs = @{
    InputFile   = $BuildFile
    OutputFile  = $OutputFile
    Title       = 'Alfred Installer'
    Description = 'Alfred AI Assistant - one-click installer'
    Version     = $Version
    STA         = $true
    noConsole   = $true
    noOutput    = $true
}
if (Test-Path $IconFile) {
    $ps2exeArgs['iconFile'] = $IconFile
    Write-Host "Using icon: $IconFile" -ForegroundColor DarkGray
}

Invoke-ps2exe @ps2exeArgs

Remove-Item $BuildFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done: $OutputFile" -ForegroundColor Green
Write-Host ""
Write-Host "Releasing:" -ForegroundColor White
Write-Host "  Normally you do not run this by hand. Push a version tag and GitHub Actions" -ForegroundColor Yellow
Write-Host "  (.github/workflows/release-installer.yml) builds this .exe on a Windows runner" -ForegroundColor Yellow
Write-Host "  and attaches it to the matching release:" -ForegroundColor Yellow
Write-Host "    git tag v$Version; git push origin v$Version" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To publish a manual local build instead:" -ForegroundColor DarkGray
Write-Host "    gh release create v$Version Alfred-Install.exe --title `"Alfred v$Version`" --generate-notes" -ForegroundColor DarkGray
Write-Host ""
