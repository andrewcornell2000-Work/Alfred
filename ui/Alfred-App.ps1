#Requires -Version 5.1
<#
.SYNOPSIS
    Alfred desktop UI — install, update, validate, notifications.
.EXAMPLE
    .\ui\Alfred-App.ps1
    Alfred.exe -Update
#>
param(
    [switch]$Update,
    [switch]$MinimizeToTray
)

$Root = Split-Path $PSScriptRoot -Parent
$env:ALFRED_HOME = $Root

function Get-AlfredVersion {
    $vf = Join-Path $Root "VERSION"
    if (Test-Path $vf) { return (Get-Content $vf -Raw).Trim() }
    return "2.0.0"
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "Alfred — AI Capability Manager"
$form.Size = New-Object System.Drawing.Size(520, 480)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(26, 26, 46)
$form.ForeColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Alfred"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 22, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(24, 20)
$title.AutoSize = $true
$title.ForeColor = [System.Drawing.Color]::FromArgb(100, 181, 246)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "Global AI capability installer & updater"
$subtitle.Location = New-Object System.Drawing.Point(26, 58)
$subtitle.AutoSize = $true
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(180, 180, 200)
$form.Controls.Add($subtitle)

$verLabel = New-Object System.Windows.Forms.Label
$verLabel.Text = "Version: v$(Get-AlfredVersion)"
$verLabel.Location = New-Object System.Drawing.Point(26, 88)
$verLabel.AutoSize = $true
$form.Controls.Add($verLabel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Checking for updates..."
$statusLabel.Location = New-Object System.Drawing.Point(26, 118)
$statusLabel.Size = New-Object System.Drawing.Size(460, 60)
$form.Controls.Add($statusLabel)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(24, 190)
$logBox.Size = New-Object System.Drawing.Size(460, 140)
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.BackColor = [System.Drawing.Color]::FromArgb(15, 15, 30)
$logBox.ForeColor = [System.Drawing.Color]::FromArgb(200, 200, 220)
$logBox.BorderStyle = "FixedSingle"
$form.Controls.Add($logBox)

function Add-Button([string]$Text, [int]$X, [scriptblock]$OnClick) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Location = New-Object System.Drawing.Point($X, 350)
    $btn.Size = New-Object System.Drawing.Size(140, 36)
    $btn.FlatStyle = "Flat"
    $btn.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
    $btn.ForeColor = [System.Drawing.Color]::White
    $btn.Add_Click($OnClick)
    $form.Controls.Add($btn)
    return $btn
}

function Append-Log([string]$Msg) {
    $logBox.AppendText("$Msg`r`n")
}

$btnUpdate = Add-Button "Install update" 24 {
    Append-Log "Running updater..."
    $updateScript = Join-Path $Root "scripts\Alfred-Update.ps1"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$updateScript`" -Force"
    $psi.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Append-Log "Updater launched — see logs folder for details."
}

$btnCheck = Add-Button "Check updates" 180 {
    Append-Log "Checking GitHub..."
    $check = Join-Path $Root "scripts\Check-AlfredUpdates.ps1"
    & $check -Root $Root -CheckOnly -Quiet
    if ($LASTEXITCODE -eq 11) {
        $statusLabel.Text = "Update available — click Install update"
        $statusLabel.ForeColor = [System.Drawing.Color]::Gold
        Append-Log "Updates found on origin/main."
    } else {
        $statusLabel.Text = "Alfred is up to date"
        $statusLabel.ForeColor = [System.Drawing.Color]::LightGreen
        Append-Log "No updates."
    }
}

$btnValidate = Add-Button "Validate install" 336 {
    Append-Log "Validating..."
    $v = Join-Path $Root "scripts\Validate-Install.ps1"
    & $v -AlfredRoot $Root 2>&1 | ForEach-Object { Append-Log $_ }
}

$btnRepair = New-Object System.Windows.Forms.Button
$btnRepair.Text = "Repair provision"
$btnRepair.Location = New-Object System.Drawing.Point(24, 400)
$btnRepair.Size = New-Object System.Drawing.Size(140, 32)
$btnRepair.FlatStyle = "Flat"
$btnRepair.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 60)
$btnRepair.ForeColor = [System.Drawing.Color]::White
$btnRepair.Add_Click({
    Append-Log "Re-provisioning MCPs + skills..."
    $prov = Join-Path $Root "Provision-Cursor.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $prov 2>&1 | ForEach-Object { Append-Log $_ }
})
$form.Controls.Add($btnRepair)

$btnOpenLogs = New-Object System.Windows.Forms.Button
$btnOpenLogs.Text = "Open logs"
$btnOpenLogs.Location = New-Object System.Drawing.Point(180, 400)
$btnOpenLogs.Size = New-Object System.Drawing.Size(140, 32)
$btnOpenLogs.FlatStyle = "Flat"
$btnOpenLogs.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 60)
$btnOpenLogs.ForeColor = [System.Drawing.Color]::White
$btnOpenLogs.Add_Click({
    $ld = Join-Path $Root "logs"
    if (-not (Test-Path $ld)) { New-Item -ItemType Directory -Path $ld | Out-Null }
    Start-Process explorer.exe $ld
})
$form.Controls.Add($btnOpenLogs)

# Tray icon
$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Icon = [System.Drawing.SystemIcons]::Application
$tray.Text = "Alfred AI Capability Manager"
$tray.Visible = $true
$tray.Add_DoubleClick({ $form.Show(); $form.WindowState = "Normal" })

$menu = New-Object System.Windows.Forms.ContextMenuStrip
[void]$menu.Items.Add("Open Alfred", $null, { $form.Show() })
[void]$menu.Items.Add("Check for updates", $null, { & $btnCheck.PerformClick() })
[void]$menu.Items.Add("Install update", $null, { & $btnUpdate.PerformClick() })
[void]$menu.Items.Add("Exit", $null, { $form.Close() })
$tray.ContextMenuStrip = $menu

$form.Add_FormClosing({
    param($sender, $e)
    if ($MinimizeToTray) {
        $e.Cancel = $true
        $form.Hide()
    } else {
        $tray.Visible = $false
        $tray.Dispose()
    }
})

# Initial update check
$checkScript = Join-Path $Root "scripts\Check-AlfredUpdates.ps1"
if (Test-Path $checkScript) {
    & $checkScript -Root $Root -CheckOnly -Quiet
    if ($LASTEXITCODE -eq 11) {
        $statusLabel.Text = "Update available — new skills, rules, or MCPs ready"
        $statusLabel.ForeColor = [System.Drawing.Color]::Gold
        $btnUpdate.BackColor = [System.Drawing.Color]::FromArgb(46, 125, 50)
    } else {
        $statusLabel.Text = "Capabilities installed — Cursor, Claude, Codex configured"
        $statusLabel.ForeColor = [System.Drawing.Color]::LightGreen
    }
} else {
    $statusLabel.Text = "Run Alfred-Install.exe for first-time setup"
}

if ($Update) {
    & $btnUpdate.PerformClick()
}

[void]$form.ShowDialog()
