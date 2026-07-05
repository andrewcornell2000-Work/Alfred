#Requires -Version 5.1
# Shared UI theme + helpers for Alfred installer dialogs.

function Initialize-AlfredUiTheme {
    if ($script:AlfredUiTheme) { return }
    Add-Type -AssemblyName System.Drawing
    $script:AlfredUiTheme = @{
        BgDeep      = [System.Drawing.Color]::FromArgb(255, 255, 255)
        BgPanel     = [System.Drawing.Color]::FromArgb(248, 250, 252)
        BgPanelEnd  = [System.Drawing.Color]::FromArgb(241, 245, 249)
        BgInput     = [System.Drawing.Color]::FromArgb(255, 255, 255)
        Border      = [System.Drawing.Color]::FromArgb(226, 232, 240)
        BorderFocus = [System.Drawing.Color]::FromArgb(180, 141, 45)
        Text        = [System.Drawing.Color]::FromArgb(15, 23, 42)
        TextMuted   = [System.Drawing.Color]::FromArgb(71, 85, 105)
        TextDim     = [System.Drawing.Color]::FromArgb(100, 116, 139)
        Accent      = [System.Drawing.Color]::FromArgb(180, 141, 45)
        AccentHover = [System.Drawing.Color]::FromArgb(196, 158, 62)
        AccentText  = [System.Drawing.Color]::FromArgb(255, 255, 255)
        Primary     = [System.Drawing.Color]::FromArgb(15, 23, 42)
        PrimaryHover = [System.Drawing.Color]::FromArgb(30, 41, 59)
    }
}

function Get-AlfredInstallerRoot {
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe) -and $exe -like '*.exe') {
            $parent = Split-Path -Parent $exe
            if ($parent) { return $parent }
        }
    } catch { }
    if ($PSScriptRoot) { return $PSScriptRoot }
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath)) {
        $parent = Split-Path -Parent $cmdPath
        if ($parent) { return $parent }
    }
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

function Get-AlfredLogoSource {
    param([string]$Root)

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Drawing
    if (Get-Command Initialize-AlfredEmbeddedLogo -ErrorAction SilentlyContinue) {
        Initialize-AlfredEmbeddedLogo
    }

    if ($script:AlfredEmbeddedLogoBase64) {
        try {
            $bytes = [Convert]::FromBase64String($script:AlfredEmbeddedLogoBase64)
            $ms = New-Object System.IO.MemoryStream(,$bytes)
            $img = [System.Drawing.Image]::FromStream($ms)
            $ms.Dispose()
            return New-Object System.Drawing.Bitmap($img)
        } catch { }
    }

    if (-not [string]::IsNullOrWhiteSpace($Root)) {
        foreach ($rel in @('assets\alfred-source.png', 'assets\alfred.png')) {
            $path = Join-Path $Root $rel
            if (-not (Test-Path $path)) { continue }
            try {
                return [System.Drawing.Image]::FromFile($path)
            } catch { }
        }
    }

    $exePath = Get-AlfredExePath
    if ($exePath) {
        try {
            $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath)
            $bmp = $icon.ToBitmap()
            $icon.Dispose()
            return $bmp
        } catch { }
    }

    return $null
}

function Get-AlfredLogoBitmap {
    param(
        [string]$Root,
        [int]$Size = 120
    )

    $source = Get-AlfredLogoSource -Root $Root
    if (-not $source) { return $null }

    if ($source.Width -eq $Size -and $source.Height -eq $Size) {
        return New-Object System.Drawing.Bitmap($source)
    }

    $canvas = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.Clear([System.Drawing.Color]::Transparent)
    if ($Size -lt $source.Width -or $Size -lt $source.Height) {
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    } else {
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    }
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half

    $graphics.DrawImage($source, 0, 0, $Size, $Size)
    $graphics.Dispose()
    $source.Dispose()
    return $canvas
}

function Set-AlfredLogoPaint {
    param(
        [System.Windows.Forms.Control]$Panel,
        [System.Drawing.Image]$LogoImage,
        [ValidateSet('Left', 'Center')]
        [string]$Align = 'Left',
        [float]$FillRatio = 0.96
    )

    Initialize-AlfredUiTheme
    Enable-AlfredDoubleBuffer $Panel
    $Panel.BackColor = $script:AlfredUiTheme.BgPanel

    $target = $Panel
    $img = $LogoImage
    $alignMode = $Align
    $fill = $FillRatio
    $Panel.Add_Paint({
        param($sender, $e)
        if (-not $img) { return }
        $g = $e.Graphics
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        if ($sender.Width -le 0 -or $sender.Height -le 0 -or $img.Width -le 0 -or $img.Height -le 0) { return }
        $scale = [Math]::Min($sender.Width / $img.Width, $sender.Height / $img.Height) * $fill
        $w = [int]($img.Width * $scale)
        $h = [int]($img.Height * $scale)
        $x = if ($alignMode -eq 'Left') { 0 } else { [int](($sender.Width - $w) / 2) }
        $y = [int](($sender.Height - $h) / 2)
        $g.DrawImage($img, $x, $y, $w, $h)
    })
    if ($target.IsHandleCreated) { $target.Invalidate() }
}

# Embedded transparent logo — regenerated by scripts/build-embedded-logo.ps1

function New-AlfredLogoPictureBox {
    param(
        [string]$Root,
        [int]$Width = 220,
        [int]$Height = 220
    )

    $box = New-Object System.Windows.Forms.PictureBox
    $box.Size = New-Object System.Drawing.Size($Width, $Height)
    $box.MinimumSize = $box.Size
    $box.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 12)
    $box.BackColor = $script:AlfredUiTheme.BgPanel
    $box.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::CenterImage

    $bitmap = Get-AlfredLogoBitmap -Root $Root -Size $Width
    if ($bitmap) {
        $box.Image = $bitmap
    }
    return $box
}

function Set-AlfredCrispText {
    param([System.Windows.Forms.Control]$Control)

    if ($Control -is [System.Windows.Forms.Label] -or $Control -is [System.Windows.Forms.Button]) {
        $Control.UseCompatibleTextRendering = $true
    }
    foreach ($child in $Control.Controls) {
        Set-AlfredCrispText $child
    }
}

function Get-AlfredBrandImage([string]$Root) {
    return Get-AlfredLogoBitmap -Root $Root -Size 120
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
    if (-not $Control) { return }
    $flags = [System.Reflection.BindingFlags]::NonPublic -bor [System.Reflection.BindingFlags]::Instance
    $prop = [System.Windows.Forms.Control].GetProperty('DoubleBuffered', $flags)
    if ($prop) { $prop.SetValue($Control, $true, $null) }
}

function Get-AlfredUiFont {
    param(
        [float]$Size = 10,
        [ValidateSet('Regular', 'Semibold', 'Bold')]
        [string]$Weight = 'Regular'
    )
    $Size = [Math]::Round($Size, 0, [MidpointRounding]::AwayFromZero)
    if ($Weight -eq 'Semibold') {
        return New-Object System.Drawing.Font('Segoe UI Semibold', $Size, [System.Drawing.FontStyle]::Regular)
    }
    if ($Weight -eq 'Bold') {
        return New-Object System.Drawing.Font('Segoe UI', $Size, [System.Drawing.FontStyle]::Bold)
    }
    return New-Object System.Drawing.Font('Segoe UI', $Size, [System.Drawing.FontStyle]::Regular)
}

function New-AlfredBrandPanel {
    Initialize-AlfredUiTheme
    $panel = New-Object System.Windows.Forms.Panel
    $panel.Dock = 'Fill'
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
            90
        )
        $g.FillRectangle($brush, $rect)
        $brush.Dispose()
        $border = New-Object System.Drawing.Pen $script:AlfredUiTheme.Border
        $g.DrawLine($border, $rect.Width - 1, 0, $rect.Width - 1, $rect.Height)
        $border.Dispose()
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
        $btn.BackColor = $script:AlfredUiTheme.Primary
        $btn.ForeColor = $script:AlfredUiTheme.AccentText
        $btn.FlatAppearance.BorderSize = 0
        $btn.Add_MouseEnter({ $this.BackColor = $script:AlfredUiTheme.PrimaryHover })
        $btn.Add_MouseLeave({ $this.BackColor = $script:AlfredUiTheme.Primary })
    } else {
        $btn.BackColor = $script:AlfredUiTheme.BgDeep
        $btn.ForeColor = $script:AlfredUiTheme.TextMuted
        $btn.FlatAppearance.BorderSize = 1
        $btn.FlatAppearance.BorderColor = $script:AlfredUiTheme.Border
        $btn.Add_MouseEnter({
            $this.ForeColor = $script:AlfredUiTheme.Text
            $this.BackColor = $script:AlfredUiTheme.BgPanel
        })
        $btn.Add_MouseLeave({
            $this.ForeColor = $script:AlfredUiTheme.TextMuted
            $this.BackColor = $script:AlfredUiTheme.BgDeep
        })
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
    $form.Size = New-Object System.Drawing.Size(900, 580)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
    $form.BackColor = $script:AlfredUiTheme.BgDeep
    $form.ForeColor = $script:AlfredUiTheme.Text
    $form.Font = Get-AlfredUiFont 10
    Set-AlfredCrispText $form
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
    $msg.Dock = 'Fill'
    $msg.Text = $Message
    $msg.AutoSize = $true
    $msg.MaximumSize = New-Object System.Drawing.Size(400, 0)
    $msg.Margin = New-Object System.Windows.Forms.Padding(0, 8, 0, 12)
    $msg.Font = Get-AlfredUiFont 10
    $msg.ForeColor = $script:AlfredUiTheme.TextMuted
    $body.Controls.Add($msg)

    $footer = New-Object System.Windows.Forms.FlowLayoutPanel
    $footer.Dock = 'Bottom'
    $footer.Height = 56
    $footer.FlowDirection = [System.Windows.Forms.FlowDirection]::RightToLeft
    $footer.WrapContents = $false
    $footer.Padding = New-Object System.Windows.Forms.Padding(0, 8, 0, 0)
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $body.Controls.Add($footer)

    $result = $false
    $btnPrimary = New-AlfredModernButton -Text $PrimaryText -Variant 'primary' -Width 120
    $btnPrimary.Margin = New-Object System.Windows.Forms.Padding(8, 0, 0, 0)
    $btnPrimary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() })
    $footer.Controls.Add($btnPrimary)

    if ($SecondaryText) {
        $btnSecondary = New-AlfredModernButton -Text $SecondaryText -Variant 'ghost' -Width 100
        $btnSecondary.Margin = New-Object System.Windows.Forms.Padding(8, 0, 0, 0)
        $btnSecondary.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel; $form.Close() })
        $footer.Controls.Add($btnSecondary)
    }

    if ($Mode -eq 'info') { $form.AcceptButton = $btnPrimary }

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $result = $true }
    $form.Dispose()
    return $result
}

function Hide-AlfredConsole {
    try {
        if (-not ([System.Management.Automation.PSTypeName]'AlfredConsoleWindow').Type) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class AlfredConsoleWindow {
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
        }
        $hwnd = [AlfredConsoleWindow]::GetConsoleWindow()
        if ($hwnd -ne [IntPtr]::Zero) {
            [void][AlfredConsoleWindow]::ShowWindow($hwnd, 0)
        }
    } catch { }
}

function Start-AlfredInstallProgress {
    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms

    $form = New-AlfredInstallShellForm 'Installing Alfred'
    $form.Size = New-Object System.Drawing.Size(520, 220)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    $form.ControlBox = $false
    Set-AlfredFormIcon $form (Get-AlfredInstallerRoot)

    $label = New-Object System.Windows.Forms.Label
    $label.Text = 'Installing Alfred...'
    $label.AutoSize = $true
    $label.Font = Get-AlfredUiFont 14 'Semibold'
    $label.ForeColor = $script:AlfredUiTheme.Text
    $label.Location = New-Object System.Drawing.Point(32, 28)
    $form.Controls.Add($label)

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = 'This may take several minutes. Please keep this window open.'
    $sub.AutoSize = $true
    $sub.Font = Get-AlfredUiFont 10
    $sub.ForeColor = $script:AlfredUiTheme.TextMuted
    $sub.Location = New-Object System.Drawing.Point(32, 58)
    $form.Controls.Add($sub)

    $status = New-Object System.Windows.Forms.Label
    $status.AutoSize = $false
    $status.Size = New-Object System.Drawing.Size(456, 48)
    $status.Font = Get-AlfredUiFont 9.5
    $status.ForeColor = $script:AlfredUiTheme.TextDim
    $status.Location = New-Object System.Drawing.Point(32, 92)
    $form.Controls.Add($status)

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Style = 'Marquee'
    $bar.MarqueeAnimationSpeed = 30
    $bar.Size = New-Object System.Drawing.Size(456, 8)
    $bar.Location = New-Object System.Drawing.Point(32, 156)
    $form.Controls.Add($bar)

    $form.Add_Shown({ $form.Activate() })
    $form.Show()
    [System.Windows.Forms.Application]::DoEvents()

    return [PSCustomObject]@{
        Form = $form
        SetStatus = {
            param([string]$Text)
            if ($form.IsDisposed) { return }
            $status.Text = $Text
            [System.Windows.Forms.Application]::DoEvents()
        }
        Close = {
            if (-not $form.IsDisposed) {
                $form.Close()
                $form.Dispose()
            }
        }
    }
}
