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
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath) -and $cmdPath -like '*.exe' -and (Test-Path $cmdPath)) {
        return $cmdPath
    }
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe) -and (Test-Path $exe)) { return $exe }
    } catch { }
    return $null
}

function Get-AlfredBrandImage([string]$Root) {
    $path = Get-AlfredBrandIcon $Root
    if ($path) {
        if ($path -like '*.ico') {
            return [System.Drawing.Icon]::ExtractAssociatedIcon($path).ToBitmap()
        }
        return [System.Drawing.Image]::FromFile($path)
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

function New-AlfredRoundedPath {
    param(
        [System.Drawing.Rectangle]$Rect,
        [int]$Radius
    )
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $Radius * 2
    $path.AddArc($Rect.X, $Rect.Y, $d, $d, 180, 90)
    $path.AddArc($Rect.Right - $d, $Rect.Y, $d, $d, 270, 90)
    $path.AddArc($Rect.Right - $d, $Rect.Bottom - $d, $d, $d, 0, 90)
    $path.AddArc($Rect.X, $Rect.Bottom - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-AlfredBrandPanel {
    param([int]$Width = 300)

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Drawing
    $panel = New-Object System.Windows.Forms.Panel
    $panel.Width = $Width
    $panel.Dock = 'Left'
    $panel.BackColor = $script:AlfredUiTheme.BgPanel
    Enable-AlfredDoubleBuffer $panel

    $panel.Add_Paint({
        param($sender, $e)
        $g = $e.Graphics
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $rect = $sender.ClientRectangle
        $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $rect,
            $script:AlfredUiTheme.BgPanel,
            $script:AlfredUiTheme.BgPanelEnd,
            105
        )
        $g.FillRectangle($brush, $rect)
        $brush.Dispose()

        $glow = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            (New-Object System.Drawing.Rectangle 0, 0, 4, $rect.Height),
            $script:AlfredUiTheme.Accent,
            [System.Drawing.Color]::FromArgb(0, 212, 175, 55),
            0
        )
        $g.FillRectangle($glow, 0, 0, 4, $rect.Height)
        $glow.Dispose()
    })

    return $panel
}

function New-AlfredModernButton {
    param(
        [string]$Text,
        [ValidateSet('primary', 'ghost')]
        [string]$Variant = 'primary',
        [System.Drawing.Size]$Size = (New-Object System.Drawing.Size(132, 42))
    )

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Drawing
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Size = $Size
    $btn.FlatStyle = 'Flat'
    $btn.FlatAppearance.BorderSize = 0
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $btn.Font = Get-AlfredUiFont 10 'Semibold'
    $btn.Tag = $Variant
    Enable-AlfredDoubleBuffer $btn

    $btn.Add_MouseEnter({
        $this.Invalidate()
    })
    $btn.Add_MouseLeave({
        $this.Invalidate()
    })

    $btn.Add_Paint({
        param($sender, $e)
        $g = $e.Graphics
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
        $rect = New-Object System.Drawing.Rectangle 0, 0, $sender.Width - 1, $sender.Height - 1
        $path = New-AlfredRoundedPath $rect 10

        if ($sender.Tag -eq 'primary') {
            $fill = if ($sender.ClientRectangle.Contains($sender.PointToClient([System.Windows.Forms.Cursor]::Position))) {
                $script:AlfredUiTheme.AccentHover
            } else {
                $script:AlfredUiTheme.Accent
            }
            $g.FillPath((New-Object System.Drawing.SolidBrush $fill), $path)
            $fg = $script:AlfredUiTheme.AccentText
        } else {
            $g.DrawPath((New-Object System.Drawing.Pen $script:AlfredUiTheme.Border, 1), $path)
            $fg = $script:AlfredUiTheme.TextMuted
        }

        $sf = New-Object System.Drawing.StringFormat
        $sf.Alignment = 'Center'
        $sf.LineAlignment = 'Center'
        $g.DrawString($sender.Text, $sender.Font, (New-Object System.Drawing.SolidBrush $fg), $rect, $sf)
        $path.Dispose()
    })

    return $btn
}

function New-AlfredModernTextBox {
    param([string]$Text = '')

    Initialize-AlfredUiTheme
    $box = New-Object System.Windows.Forms.TextBox
    $box.Text = $Text
    $box.Height = 28
    $box.BorderStyle = 'None'
    $box.BackColor = $script:AlfredUiTheme.BgInput
    $box.ForeColor = $script:AlfredUiTheme.Text
    $box.Font = Get-AlfredUiFont 10
    $box.Padding = New-Object System.Windows.Forms.Padding 12, 10, 12, 10

    $inputWrap = New-Object System.Windows.Forms.Panel
    $inputWrap.Height = 42
    $inputWrap.BackColor = $script:AlfredUiTheme.BgInput
    $inputWrap.Padding = New-Object System.Windows.Forms.Padding 12, 8, 12, 8
    $box.Dock = 'Fill'
    $inputWrap.Controls.Add($box)
    Enable-AlfredDoubleBuffer $inputWrap

    $inputWrap.Add_Paint({
        param($sender, $e)
        $g = $e.Graphics
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $rect = New-Object System.Drawing.Rectangle 0, 0, $sender.Width - 1, $sender.Height - 1
        $path = New-AlfredRoundedPath $rect 8
        $focused = $sender.Controls[0].Focused
        $border = if ($focused) { $script:AlfredUiTheme.BorderFocus } else { $script:AlfredUiTheme.Border }
        $g.FillPath((New-Object System.Drawing.SolidBrush $script:AlfredUiTheme.BgInput), $path)
        $g.DrawPath((New-Object System.Drawing.Pen $border, 1.5), $path)
        $path.Dispose()
    })

    $box.Add_GotFocus({ $this.Parent.Invalidate() })
    $box.Add_LostFocus({ $this.Parent.Invalidate() })

    $inputWrap | Add-Member -NotePropertyName InnerTextBox -NotePropertyValue $box -Force
    return $inputWrap
}

function New-AlfredInstallShellForm {
    param([string]$Title = 'Alfred Installer')

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $Title
    $form.Size = New-Object System.Drawing.Size(820, 540)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = $script:AlfredUiTheme.BgDeep
    $form.ForeColor = $script:AlfredUiTheme.Text
    $form.Font = Get-AlfredUiFont 10
    Enable-AlfredDoubleBuffer $form
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

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-AlfredInstallShellForm $Title
    $form.Size = New-Object System.Drawing.Size(480, 260)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    Set-AlfredFormIcon $form (Get-AlfredInstallerRoot)

    $body = New-Object System.Windows.Forms.Panel
    $body.Dock = 'Fill'
    $body.Padding = New-Object System.Windows.Forms.Padding 28, 24, 28, 20
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
        $btnSecondary = New-AlfredModernButton $SecondaryText 'ghost' (New-Object System.Drawing.Size 100, 42)
        $btnSecondary.Anchor = 'Bottom,Right'
        $btnSecondary.Location = New-Object System.Drawing.Point ($footer.Width - 250), 8
        $btnSecondary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel; $form.Close() })
        $footer.Controls.Add($btnSecondary)
        $footer.Add_Resize({
            $btnSecondary.Location = New-Object System.Drawing.Point ($footer.ClientSize.Width - 250), 8
        })
    }

    $btnPrimary = New-AlfredModernButton $PrimaryText 'primary' (New-Object System.Drawing.Size 120, 42)
    $btnPrimary.Anchor = 'Bottom,Right'
    $btnPrimary.Location = New-Object System.Drawing.Point ($footer.Width - 132), 8
    $btnPrimary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() })
    $footer.Controls.Add($btnPrimary)
    $footer.Add_Resize({
        $btnPrimary.Location = New-Object System.Drawing.Point ($footer.ClientSize.Width - 132), 8
    })

    if ($Mode -eq 'info') {
        $form.AcceptButton = $btnPrimary
    }

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $result = $true }
    $form.Dispose()
    return $result
}
