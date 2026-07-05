#Requires -Version 5.1
# GUI update prompt — used by check-updates.ps1 and Alfred-Install.ps1

if (-not (Get-Command Get-AlfredBrandIcon -ErrorAction SilentlyContinue)) {
function Get-AlfredBrandIcon([string]$Root) {
    foreach ($rel in @('assets\alfred.ico', 'assets\alfred.png')) {
        $path = Join-Path $Root $rel
        if (Test-Path $path) { return $path }
    }
    return $null
}
}

function Show-AlfredUpdateAlert {
    param(
        [Parameter(Mandatory = $true)]
        [int]$BehindCount,
        [Parameter(Mandatory = $true)]
        [string[]]$CommitLines,
        [string]$Root = $PSScriptRoot,
        [string]$Title = 'Alfred update available'
    )

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $Title
    $form.Size = New-Object System.Drawing.Size(520, 420)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = [System.Drawing.Color]::FromArgb(26, 35, 50)
    $form.ForeColor = [System.Drawing.Color]::White
    $form.Font = New-Object System.Drawing.Font('Segoe UI', 10)
    $iconPath = if ($Root) { Get-AlfredBrandIcon $Root } else { $null }
    if ($iconPath) {
        try { $form.Icon = New-Object System.Drawing.Icon($iconPath) } catch { }
    } else {
        $exePath = $MyInvocation.MyCommand.Path
        if ($exePath -and (Test-Path $exePath) -and $exePath -like '*.exe') {
            try { $form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath) } catch { }
        }
    }

    $y = 16

    $head = New-Object System.Windows.Forms.Label
    $head.Text = "$BehindCount new commit(s) on origin/main"
    $head.AutoSize = $true
    $head.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 12)
    $head.ForeColor = [System.Drawing.Color]::FromArgb(212, 175, 55)
    $head.Location = New-Object System.Drawing.Point(80, $y + 8)
    $form.Controls.Add($head)
    $y += 64

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = 'Pull the latest Alfred pack now? Setup will re-run if needed.'
    $sub.AutoSize = $true
    $sub.ForeColor = [System.Drawing.Color]::FromArgb(200, 206, 214)
    $sub.Location = New-Object System.Drawing.Point(20, $y)
    $form.Controls.Add($sub)
    $y += 28

    $list = New-Object System.Windows.Forms.TextBox
    $list.Multiline = $true
    $list.ReadOnly = $true
    $list.ScrollBars = 'Vertical'
    $list.BorderStyle = 'FixedSingle'
    $list.BackColor = [System.Drawing.Color]::FromArgb(36, 46, 62)
    $list.ForeColor = [System.Drawing.Color]::FromArgb(230, 233, 238)
    $list.Font = New-Object System.Drawing.Font('Consolas', 9)
    $list.Text = ($CommitLines | Select-Object -First 12) -join [Environment]::NewLine
    $list.Location = New-Object System.Drawing.Point(20, $y)
    $list.Size = New-Object System.Drawing.Size(464, 180)
    $form.Controls.Add($list)
    $y += 196

    $result = 'later'

    $btnLater = New-Object System.Windows.Forms.Button
    $btnLater.Text = 'Later'
    $btnLater.Size = New-Object System.Drawing.Size(100, 32)
    $btnLater.Location = New-Object System.Drawing.Point(280, $y)
    $btnLater.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Controls.Add($btnLater)

    $btnUpdate = New-Object System.Windows.Forms.Button
    $btnUpdate.Text = 'Update now'
    $btnUpdate.Size = New-Object System.Drawing.Size(120, 32)
    $btnUpdate.Location = New-Object System.Drawing.Point(364, $y)
    $btnUpdate.BackColor = [System.Drawing.Color]::FromArgb(212, 175, 55)
    $btnUpdate.ForeColor = [System.Drawing.Color]::FromArgb(26, 35, 50)
    $btnUpdate.FlatStyle = 'Flat'
    $btnUpdate.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Controls.Add($btnUpdate)

    $form.AcceptButton = $btnUpdate
    $form.CancelButton = $btnLater

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $result = 'update'
    }

    $form.Dispose()
    return $result
}
