#Requires -Version 5.1
<#
.SYNOPSIS
    Build Alfred-Install.exe and run an unattended install smoke test (-NoWizard).
#>
param(
    [string]$InstallPath = "$env:USERPROFILE\Alfred",
    [int]$TimeoutMinutes = 45
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root 'Alfred-Install.exe'
$Log = Join-Path $InstallPath 'logs\install.log'

function Test-PowerShellParse([string]$Path) {
    $errs = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$null, [ref]$errs)
    if ($errs) {
        throw ("Parse errors in {0}:{1}{2}" -f $Path, [Environment]::NewLine, ($errs | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine)
    }
}

Write-Host '=== Parse-check installer modules ===' -ForegroundColor Cyan
Test-PowerShellParse (Join-Path $Root 'Alfred-Common.ps1')
Test-PowerShellParse (Join-Path $Root 'Alfred-CoreSetup.ps1')
Get-ChildItem (Join-Path $Root 'installer\*.ps1') | ForEach-Object { Test-PowerShellParse $_.FullName }
Test-PowerShellParse (Join-Path $Root 'Alfred-Install.ps1')

Write-Host '=== Build Alfred-Install.exe ===' -ForegroundColor Cyan
& (Join-Path $Root 'build-installer.ps1') -Version '2.6.2'
if (-not (Test-Path $Exe)) { throw "Build failed - $Exe missing" }

if (Test-Path $Log) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Copy-Item $Log (Join-Path (Split-Path $Log) ("install.pre-test-$stamp.log")) -Force
    Remove-Item $Log -Force
}

Write-Host '=== Run installer (NoWizard) ===' -ForegroundColor Cyan
$proc = Start-Process -FilePath $Exe -ArgumentList @('-NoWizard') -PassThru -WindowStyle Normal
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$lastSize = 0
$stable = 0

while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-Path $Log) {
        $size = (Get-Item $Log).Length
        if ($size -eq $lastSize) { $stable++ } else { $stable = 0; $lastSize = $size }
        $tail = Get-Content $Log -Tail 12 -ErrorAction SilentlyContinue
        if ($tail -match '\[ERROR\].*installer failed') {
            Write-Host ($tail -join [Environment]::NewLine) -ForegroundColor Red
            if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
            throw 'Installer logged ERROR - see install.log'
        }
        if ($tail -match 'Completed stage: finalize|Alfred installed successfully|Installation complete') {
            if ($stable -ge 2) { break }
        }
    }
}

if (-not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw 'Installer timed out'
}

if (-not (Test-Path $Log)) { throw 'install.log not found' }
$logText = Get-Content $Log -Raw
if ($logText -match '\[ERROR\]|installer failed') {
    throw 'Install failed - see logs/install.log'
}
if ($logText -notmatch 'Completed stage: finalize|Alfred is ready|installed successfully') {
    throw 'Install did not reach success screen - see logs/install.log'
}

Write-Host '=== PASS: installer completed ===' -ForegroundColor Green
exit 0
