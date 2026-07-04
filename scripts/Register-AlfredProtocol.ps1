#Requires -Version 5.1
<#
.SYNOPSIS
    Registers alfred:// protocol to run the updater (user scope, no admin).
#>
param(
    [string]$Root = (Join-Path $env:USERPROFILE "Alfred")
)

$updateScript = Join-Path $Root "scripts\Alfred-Update.ps1"
$uiExe = Join-Path $Root "Alfred.exe"
$command = if (Test-Path $uiExe) {
    "`"$uiExe`" -Update"
} else {
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$updateScript`" -Force"
}

$base = "HKCU:\Software\Classes\alfred"
New-Item -Path $base -Force | Out-Null
Set-ItemProperty -Path $base -Name "(Default)" -Value "URL:Alfred Protocol"
Set-ItemProperty -Path $base -Name "URL Protocol" -Value ""

New-Item -Path "$base\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "$base\shell\open\command" -Name "(Default)" -Value $command

# Sub-protocol for update action
New-Item -Path "HKCU:\Software\Classes\alfred\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\alfred\shell\open\command" -Name "(Default)" -Value $command

Write-Host "Registered alfred:// protocol -> updater" -ForegroundColor DarkGray
