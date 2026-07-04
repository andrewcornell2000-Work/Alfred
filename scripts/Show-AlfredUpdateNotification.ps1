#Requires -Version 5.1
<#
.SYNOPSIS
    Windows toast notification when Alfred updates are available.
.PARAMETER Root
    Alfred repository root.
#>
param(
    [string]$Root = (Join-Path $env:USERPROFILE "Alfred")
)

$StateFile = Join-Path $Root "logs\update-available.json"
if (-not (Test-Path $StateFile)) { exit 0 }

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$count = $state.commits_behind
$title = "Alfred update available"
$body = "$count new improvement(s) ready to install. Click to update skills, rules, and MCPs."

$updateScript = Join-Path $Root "scripts\Alfred-Update.ps1"
$uiExe = Join-Path $Root "Alfred.exe"
$actionCmd = if (Test-Path $uiExe) { "`"$uiExe`" -Update" } else { "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$updateScript`" -Force" }

# Register one-shot protocol handler for toast activation
$protoScript = Join-Path $Root "scripts\Register-AlfredProtocol.ps1"
if (Test-Path $protoScript) { & $protoScript -Root $Root | Out-Null }

try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $xml = @"
<toast activationType="protocol" launch="alfred://update">
  <visual>
    <binding template="ToastGeneric">
      <text>$title</text>
      <text>$body</text>
    </binding>
  </visual>
  <actions>
    <action content="Install update" activationType="protocol" arguments="alfred://update"/>
    <action content="Later" activationType="system" arguments="dismiss"/>
  </actions>
</toast>
"@

    $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $doc.LoadXml($xml)
    $appId = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"  # Windows PowerShell
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
    $notifier.Show($toast)
} catch {
    # Fallback: balloon tip via WinForms
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.Visible = $true
    $notify.BalloonTipTitle = $title
    $notify.BalloonTipText = $body
    $notify.ShowBalloonTip(8000)
    Start-Sleep -Seconds 2
    $notify.Dispose()
}
