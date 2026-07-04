#Requires -Version 5.1
<#
.SYNOPSIS
    Registers a logon scheduled task to check for Alfred updates and notify.
#>
param(
    [string]$Root = (Join-Path $env:USERPROFILE "Alfred")
)

$checkScript = Join-Path $Root "scripts\Check-AlfredUpdates.ps1"
if (-not (Test-Path $checkScript)) {
    Write-Host "Check-AlfredUpdates.ps1 not found — skip task registration." -ForegroundColor Yellow
    exit 0
}

$taskName = "AlfredUpdateCheck"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$checkScript`" -Notify -Quiet"

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered scheduled task: $taskName (check on logon)" -ForegroundColor Green

# Also check every 6 hours while logged in
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration ([TimeSpan]::MaxValue)
Register-ScheduledTask -TaskName "${taskName}6h" -Action $action -Trigger $trigger2 -Settings $settings -Principal $principal -Force | Out-Null

& (Join-Path $Root "scripts\Register-AlfredProtocol.ps1") -Root $Root
