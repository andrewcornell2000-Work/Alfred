#Requires -Version 5.1
# Shared UI theme + helpers for Alfred installer dialogs.

function Initialize-AlfredUiTheme {
    if ($script:AlfredUiTheme) { return }
    Add-Type -AssemblyName System.Drawing
    $script:AlfredUiTheme = @{
        BgDeep      = [System.Drawing.Color]::FromArgb(15, 23, 42)
        BgPanel     = [System.Drawing.Color]::FromArgb(11, 17, 32)
        BgPanelEnd  = [System.Drawing.Color]::FromArgb(21, 29, 46)
        BgInput     = [System.Drawing.Color]::FromArgb(30, 41, 59)
        Border      = [System.Drawing.Color]::FromArgb(51, 65, 85)
        BorderFocus = [System.Drawing.Color]::FromArgb(212, 175, 55)
        Text        = [System.Drawing.Color]::FromArgb(248, 250, 252)
        TextMuted   = [System.Drawing.Color]::FromArgb(148, 163, 184)
        TextDim     = [System.Drawing.Color]::FromArgb(100, 116, 139)
        Accent      = [System.Drawing.Color]::FromArgb(212, 175, 55)
        AccentHover = [System.Drawing.Color]::FromArgb(228, 193, 90)
        AccentText  = [System.Drawing.Color]::FromArgb(15, 23, 42)
    }
}

function Get-AlfredInstallerRoot {
    if ($PSScriptRoot) { return $PSScriptRoot }
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath)) {
        $parent = Split-Path -Parent $cmdPath
        if ($parent) { return $parent }
    }
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe)) {
            $parent = Split-Path -Parent $exe
            if ($parent) { return $parent }
        }
    } catch { }
    return (Get-Location).Path
}

function Get-AlfredBrandIcon([string]$Root) {
    if ([string]::IsNullOrWhiteSpace($Root)) { return $null }
    foreach ($rel in @('assets\alfred.ico', 'assets\alfred-source.png', 'assets\alfred.png')) {
        $path = Join-Path $Root $rel
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Get-AlfredExePath {
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe) -and (Test-Path $exe)) { return $exe }
    } catch { }
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath) -and $cmdPath -like '*.exe' -and (Test-Path $cmdPath)) {
        return $cmdPath
    }
    return $null
}

function Get-AlfredBrandImage([string]$Root) {
    Initialize-AlfredUiTheme
    if (-not [string]::IsNullOrWhiteSpace($Root)) {
        foreach ($rel in @('assets\alfred-source.png', 'assets\alfred.png', 'assets\alfred.ico')) {
            $path = Join-Path $Root $rel
            if (-not (Test-Path $path)) { continue }
            try {
                if ($path -like '*.ico') {
                    return [System.Drawing.Icon]::ExtractAssociatedIcon($path).ToBitmap()
                }
                return [System.Drawing.Image]::FromFile($path)
            } catch { }
        }
    }
    $exePath = Get-AlfredExePath
    if ($exePath) {
        try { return [System.Drawing.Icon]::ExtractAssociatedIcon($exePath).ToBitmap() } catch { }
    }
    return $null
}

function Set-AlfredFormIcon([System.Windows.Forms.Form]$Form, [string]$Root) {
    $iconPath = Get-AlfredBrandIcon $Root
    if ($iconPath) {
        try { $Form.Icon = New-Object System.Drawing.Icon($iconPath); return } catch { }
    }
    $exePath = Get-AlfredExePath
    if ($exePath) {
        try { $Form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath); return } catch { }
    }
}

function Enable-AlfredDoubleBuffer([System.Windows.Forms.Control]$Control) {
    $flags = [System.Reflection.BindingFlags]::NonPublic -bor [System.Reflection.BindingFlags]::Instance
    [System.Windows.Forms.Control].GetProperty('DoubleBuffered', $flags).SetValue($Control, $true, $null)
}

function Get-AlfredUiFont {
    param(
        [float]$Size = 10,
        [ValidateSet('Regular', 'Semibold', 'Bold')]
        [string]$Weight = 'Regular'
    )
    if ($Weight -eq 'Semibold') {
        return New-Object System.Drawing.Font('Segoe UI Semibold', $Size, [System.Drawing.FontStyle]::Regular)
    }
    if ($Weight -eq 'Bold') {
        return New-Object System.Drawing.Font('Segoe UI', $Size, [System.Drawing.FontStyle]::Bold)
    }
    return New-Object System.Drawing.Font('Segoe UI', $Size, [System.Drawing.FontStyle]::Regular)
}

function New-AlfredBrandPanel {
    param([int]$Width = 300)

    Initialize-AlfredUiTheme
    $panel = New-Object System.Windows.Forms.Panel
    $panel.Width = $Width
    $panel.Dock = 'Left'
    $panel.BackColor = $script:AlfredUiTheme.BgPanel
    Enable-AlfredDoubleBuffer $panel

    $panel.Add_Paint({
        param($sender, $e)
        $g = $e.Graphics
        $rect = $sender.ClientRectangle
        $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $rect,
            $script:AlfredUiTheme.BgPanel,
            $script:AlfredUiTheme.BgPanelEnd,
            105
        )
        $g.FillRectangle($brush, $rect)
        $brush.Dispose()
        $accent = New-Object System.Drawing.SolidBrush $script:AlfredUiTheme.Accent
        $g.FillRectangle($accent, 0, 0, 3, $rect.Height)
        $accent.Dispose()
    })

    return $panel
}

function New-AlfredModernButton {
    param(
        [string]$Text,
        [ValidateSet('primary', 'ghost')]
        [string]$Variant = 'primary',
        [int]$Width = 132,
        [int]$Height = 40
    )

    Initialize-AlfredUiTheme
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Size = New-Object System.Drawing.Size($Width, $Height)
    $btn.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $btn.Font = Get-AlfredUiFont 10 'Semibold'
    $btn.UseVisualStyleBackColor = $false

    if ($Variant -eq 'primary') {
        $btn.BackColor = $script:AlfredUiTheme.Accent
        $btn.ForeColor = $script:AlfredUiTheme.AccentText
        $btn.FlatAppearance.BorderSize = 0
        $btn.Add_MouseEnter({ $this.BackColor = $script:AlfredUiTheme.AccentHover })
        $btn.Add_MouseLeave({ $this.BackColor = $script:AlfredUiTheme.Accent })
    } else {
        $btn.BackColor = $script:AlfredUiTheme.BgDeep
        $btn.ForeColor = $script:AlfredUiTheme.TextMuted
        $btn.FlatAppearance.BorderSize = 1
        $btn.FlatAppearance.BorderColor = $script:AlfredUiTheme.Border
        $btn.Add_MouseEnter({ $this.ForeColor = $script:AlfredUiTheme.Text })
        $btn.Add_MouseLeave({ $this.ForeColor = $script:AlfredUiTheme.TextMuted })
    }

    return $btn
}

function New-AlfredModernTextBox {
    param([string]$Text = '')

    Initialize-AlfredUiTheme
    $box = New-Object System.Windows.Forms.TextBox
    $box.Text = $Text
    $box.Height = 40
    $box.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
    $box.BackColor = $script:AlfredUiTheme.BgInput
    $box.ForeColor = $script:AlfredUiTheme.Text
    $box.Font = Get-AlfredUiFont 10
    $box | Add-Member -NotePropertyName InnerTextBox -NotePropertyValue $box -Force
    return $box
}

function New-AlfredInstallShellForm {
    param([string]$Title = 'Alfred Installer')

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $Title
    $form.Size = New-Object System.Drawing.Size(820, 540)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
    $form.BackColor = $script:AlfredUiTheme.BgDeep
    $form.ForeColor = $script:AlfredUiTheme.Text
    $form.Font = Get-AlfredUiFont 10
    return $form
}

function Show-AlfredModernDialog {
    param(
        [string]$Title,
        [string]$Message,
        [string]$PrimaryText = 'OK',
        [string]$SecondaryText,
        [ValidateSet('info', 'confirm')]
        [string]$Mode = 'info'
    )

    $form = New-AlfredInstallShellForm $Title
    $form.Size = New-Object System.Drawing.Size(480, 260)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    Set-AlfredFormIcon $form (Get-AlfredInstallerRoot)

    $body = New-Object System.Windows.Forms.Panel
    $body.Dock = 'Fill'
    $body.Padding = New-Object System.Windows.Forms.Padding(28, 24, 28, 20)
    $body.BackColor = $script:AlfredUiTheme.BgDeep
    $form.Controls.Add($body)

    $head = New-Object System.Windows.Forms.Label
    $head.Text = $Title
    $head.Dock = 'Top'
    $head.Height = 32
    $head.Font = Get-AlfredUiFont 16 'Semibold'
    $head.ForeColor = $script:AlfredUiTheme.Text
    $body.Controls.Add($head)

    $msg = New-Object System.Windows.Forms.Label
    $msg.Text = $Message
    $msg.Dock = 'Top'
    $msg.Height = 100
    $msg.Font = Get-AlfredUiFont 10
    $msg.ForeColor = $script:AlfredUiTheme.TextMuted
    $body.Controls.Add($msg)

    $footer = New-Object System.Windows.Forms.Panel
    $footer.Dock = 'Bottom'
    $footer.Height = 56
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $body.Controls.Add($footer)

    $result = $false
    if ($SecondaryText) {
        $btnSecondary = New-AlfredModernButton -Text $SecondaryText -Variant 'ghost' -Width 100
        $btnSecondary.Anchor = 'Bottom,Right'
        $btnSecondary.Location = New-Object System.Drawing.Point(($footer.Width - 250), 8)
        $btnSecondary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel; $form.Close() })
        $footer.Controls.Add($btnSecondary)
    }

    $btnPrimary = New-AlfredModernButton -Text $PrimaryText -Variant 'primary' -Width 120
    $btnPrimary.Anchor = 'Bottom,Right'
    $btnPrimary.Location = New-Object System.Drawing.Point(($footer.Width - 132), 8)
    $btnPrimary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() })
    $footer.Controls.Add($btnPrimary)

    if ($Mode -eq 'info') { $form.AcceptButton = $btnPrimary }

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $result = $true }
    $form.Dispose()
    return $result
}
