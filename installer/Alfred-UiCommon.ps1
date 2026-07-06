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
            $bmp = [System.Drawing.Bitmap]::FromStream($ms)
            $ms.Dispose()
            return $bmp
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

    if ($Size -lt 1) { return $null }

    $source = Get-AlfredLogoSource -Root $Root
    if (-not $source) { return $null }

    try {
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

    $flattened = $false
    try {
        if ($source.Width -gt 0 -and $source.Height -gt 0) {
            $scratch = New-Object System.Drawing.Bitmap $source.Width, $source.Height, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            for ($y = 0; $y -lt $source.Height; $y++) {
                for ($x = 0; $x -lt $source.Width; $x++) {
                    $c = $source.GetPixel($x, $y)
                    if ($c.A -lt 16 -or ($c.R -gt 245 -and $c.G -gt 245 -and $c.B -gt 245)) {
                        $scratch.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
                    } else {
                        $scratch.SetPixel($x, $y, $c)
                    }
                }
            }
            $source.Dispose()
            $source = $scratch
            $flattened = $true
        }
    } catch { }

    if (-not $flattened) {
        try { $graphics.DrawImage($source, 0, 0, $Size, $Size) } catch { }
    } else {
        $graphics.DrawImage($source, 0, 0, $Size, $Size)
    }
    $graphics.Dispose()
    if ($source) { $source.Dispose() }
    return $canvas
    } catch {
        if ($source) { try { $source.Dispose() } catch { } }
        return $null
    }
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
        [int]$Height = 220,
        [ValidateSet('Default', 'Plain')]
        [string]$BackgroundVariant = 'Default'
    )

    Initialize-AlfredUiTheme
    $box = New-Object System.Windows.Forms.PictureBox
    $box.Size = New-Object System.Drawing.Size($Width, $Height)
    $box.MinimumSize = $box.Size
    $box.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 12)
    $box.BackColor = if ($BackgroundVariant -eq 'Plain') { $script:AlfredUiTheme.BgDeep } else { $script:AlfredUiTheme.BgPanel }
    $box.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::CenterImage

    try {
        $bitmap = Get-AlfredLogoBitmap -Root $Root -Size $Width
        if ($bitmap) { $box.Image = $bitmap }
    } catch { }
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
    if ($iconPath -and $iconPath -like '*.ico') {
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
    if ($Size -lt 8) { $Size = 10 }
    $emSize = [single]([Math]::Max(8, [Math]::Round($Size, 1)))
    $style = [System.Drawing.FontStyle]::Regular
    if ($Weight -eq 'Semibold' -or $Weight -eq 'Bold') { $style = [System.Drawing.FontStyle]::Bold }

    foreach ($family in @('Segoe UI', 'Tahoma', [System.Drawing.SystemFonts]::DefaultFont.FontFamily.Name)) {
        try {
            return New-Object System.Drawing.Font($family, $emSize, $style)
        } catch { }
    }
    return [System.Drawing.SystemFonts]::DefaultFont
}

function New-AlfredBrandPanel {
    param(
        [ValidateSet('Default', 'Plain')]
        [string]$Variant = 'Default'
    )

    Initialize-AlfredUiTheme
    $panel = New-Object System.Windows.Forms.Panel
    $panel.Dock = 'Fill'
    $panel.BackColor = if ($Variant -eq 'Plain') { $script:AlfredUiTheme.BgDeep } else { $script:AlfredUiTheme.BgPanel }
    Enable-AlfredDoubleBuffer $panel

    if ($Variant -eq 'Plain') {
        $panel.Add_Paint({
            param($sender, $e)
            $g = $e.Graphics
            $rect = $sender.ClientRectangle
            $g.Clear($script:AlfredUiTheme.BgDeep)
            $border = New-Object System.Drawing.Pen $script:AlfredUiTheme.Border
            $g.DrawLine($border, $rect.Width - 1, 0, $rect.Width - 1, $rect.Height)
            $border.Dispose()
        })
    } else {
        $panel.Add_Paint({
            param($sender, $e)
            $g = $e.Graphics
            $rect = $sender.ClientRectangle
            if ($rect.Width -gt 0 -and $rect.Height -gt 0) {
                try {
                    $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
                        $rect,
                        $script:AlfredUiTheme.BgPanel,
                        $script:AlfredUiTheme.BgPanelEnd,
                        90
                    )
                    $g.FillRectangle($brush, $rect)
                    $brush.Dispose()
                } catch {
                    $g.Clear($script:AlfredUiTheme.BgPanel)
                }
            }
            $border = New-Object System.Drawing.Pen $script:AlfredUiTheme.Border
            $g.DrawLine($border, $rect.Width - 1, 0, $rect.Width - 1, $rect.Height)
            $border.Dispose()
        })
    }

    return $panel
}

function Get-AlfredRoundedRectPath {
    param(
        [System.Drawing.Rectangle]$Bounds,
        [int]$Radius
    )

    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $r = [Math]::Min($Radius, [Math]::Floor([Math]::Min($Bounds.Width, $Bounds.Height) / 2))
    if ($r -le 0) {
        $path.AddRectangle($Bounds)
        return $path
    }

    $d = $r * 2
    $x = $Bounds.X
    $y = $Bounds.Y
    $w = $Bounds.Width
    $h = $Bounds.Height
    $path.AddArc($x, $y, $d, $d, 180, 90)
    $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function Update-AlfredButtonRegion {
    param(
        [System.Windows.Forms.Button]$Button,
        [int]$Radius
    )

    if ($Button.Width -le 0 -or $Button.Height -le 0) { return }
    $rect = New-Object System.Drawing.Rectangle 0, 0, $Button.Width, $Button.Height
    $path = Get-AlfredRoundedRectPath -Bounds $rect -Radius $Radius
    $region = New-Object System.Drawing.Region $path
    $old = $Button.Region
    $Button.Region = $region
    if ($old) { $old.Dispose() }
    $path.Dispose()
}

function New-AlfredWrappedLabel {
    param(
        [string]$Text,
        [int]$MaxWidth,
        [System.Drawing.Font]$Font,
        [System.Drawing.Color]$ForeColor,
        [System.Windows.Forms.Padding]$Margin = [System.Windows.Forms.Padding]::Empty
    )

    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text
    $label.Font = $Font
    $label.ForeColor = $ForeColor
    $label.MaximumSize = New-Object System.Drawing.Size($MaxWidth, 0)
    $label.AutoSize = $true
    $label.UseCompatibleTextRendering = $true
    $label.Margin = $Margin
    $label.BackColor = [System.Drawing.Color]::Transparent
    return $label
}

function Set-AlfredModernButtonColors {
    param(
        [System.Windows.Forms.Button]$Button,
        [bool]$Hover = $false
    )

    Initialize-AlfredUiTheme
    $variant = $Button.Tag.Variant
    if ($variant -eq 'primary') {
        $fill = if ($Hover) { $script:AlfredUiTheme.PrimaryHover } else { $script:AlfredUiTheme.Primary }
        $Button.BackColor = $fill
        $Button.ForeColor = $script:AlfredUiTheme.AccentText
        $Button.FlatAppearance.BorderSize = 0
        $Button.FlatAppearance.BorderColor = $fill
        $Button.FlatAppearance.MouseOverBackColor = $fill
        $Button.FlatAppearance.MouseDownBackColor = $fill
        $Button.FlatAppearance.CheckedBackColor = $fill
    } else {
        $fill = if ($Hover) { $script:AlfredUiTheme.BgPanel } else { $script:AlfredUiTheme.BgDeep }
        $Button.BackColor = $fill
        $Button.ForeColor = if ($Hover) { $script:AlfredUiTheme.Text } else { $script:AlfredUiTheme.TextMuted }
        $Button.FlatAppearance.BorderSize = 0
        $Button.FlatAppearance.BorderColor = $fill
        $Button.FlatAppearance.MouseOverBackColor = $fill
        $Button.FlatAppearance.MouseDownBackColor = $fill
        $Button.FlatAppearance.CheckedBackColor = $fill
    }
}

function New-AlfredModernButton {
    param(
        [string]$Text,
        [ValidateSet('primary', 'ghost')]
        [string]$Variant = 'primary',
        [int]$Width = 132,
        [int]$Height = 40,
        [int]$CornerRadius = 8
    )

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Drawing

    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Size = New-Object System.Drawing.Size($Width, $Height)
    $btn.MinimumSize = $btn.Size
    $btn.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $btn.Font = Get-AlfredUiFont 10 'Semibold'
    $btn.UseVisualStyleBackColor = $false
    $btn.UseCompatibleTextRendering = $true
    $btn.Tag = @{ Variant = $Variant; Radius = $CornerRadius; Hover = $false }

    Set-AlfredModernButtonColors -Button $btn -Hover $false

    $applyRegion = {
        param($Button)
        if ($Button.Width -le 0 -or $Button.Height -le 0) { return }
        Update-AlfredButtonRegion -Button $Button -Radius $Button.Tag.Radius
    }

    if ($Variant -eq 'ghost') {
        $btn.Add_Paint({
            param($sender, $e)
            $g = $e.Graphics
            $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
            $rect = New-Object System.Drawing.Rectangle 0, 0, ($sender.Width - 1), ($sender.Height - 1)
            $path = Get-AlfredRoundedRectPath -Bounds $rect -Radius $sender.Tag.Radius
            $hover = [bool]$sender.Tag.Hover
            $fillColor = if ($hover) { $script:AlfredUiTheme.BgPanel } else { $script:AlfredUiTheme.BgDeep }
            $textColor = if ($hover) { $script:AlfredUiTheme.Text } else { $script:AlfredUiTheme.TextMuted }
            $fill = New-Object System.Drawing.SolidBrush $fillColor
            $g.FillPath($fill, $path)
            $fill.Dispose()
            $pen = New-Object System.Drawing.Pen $script:AlfredUiTheme.Border
            $g.DrawPath($pen, $path)
            $pen.Dispose()
            $flags = [System.Windows.Forms.TextFormatFlags]::HorizontalCenter `
                -bor [System.Windows.Forms.TextFormatFlags]::VerticalCenter `
                -bor [System.Windows.Forms.TextFormatFlags]::EndEllipsis
            [System.Windows.Forms.TextRenderer]::DrawText($g, $sender.Text, $sender.Font, $rect, $textColor, $flags)
            $path.Dispose()
        })
    }

    $btn.Add_MouseEnter({
        $this.Tag.Hover = $true
        Set-AlfredModernButtonColors -Button $this -Hover $true
        $this.Invalidate()
    })
    $btn.Add_MouseLeave({
        $this.Tag.Hover = $false
        Set-AlfredModernButtonColors -Button $this -Hover $false
        $this.Invalidate()
    })
    $btn.Add_Resize({ & $applyRegion $this })
    & $applyRegion $btn

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
    $form.Size = New-Object System.Drawing.Size(920, 640)
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

function Initialize-AlfredConsoleWindowType {
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
}

function Hide-AlfredConsole {
    try {
        Initialize-AlfredConsoleWindowType
        $hwnd = [AlfredConsoleWindow]::GetConsoleWindow()
        if ($hwnd -ne [IntPtr]::Zero) {
            [void][AlfredConsoleWindow]::ShowWindow($hwnd, 0)
        }
    } catch { }
}

function Show-AlfredConsole {
    try {
        Initialize-AlfredConsoleWindowType
        $hwnd = [AlfredConsoleWindow]::GetConsoleWindow()
        if ($hwnd -ne [IntPtr]::Zero) {
            [void][AlfredConsoleWindow]::ShowWindow($hwnd, 5)
        }
    } catch { }
}

function Enable-AlfredGuiInstallOutput {
    param([Parameter(Mandatory = $true)]$Progress)

    $script:InstallProgress = $Progress
    $script:AlfredGuiInstallMode = $true

    function script:Write-Host {
        param(
            [Parameter(ValueFromPipeline = $true, Position = 0)]
            [object]$Object,
            [switch]$NoNewline,
            [System.ConsoleColor]$ForegroundColor,
            [System.ConsoleColor]$BackgroundColor
        )
        begin { $parts = [System.Collections.Generic.List[string]]::new() }
        process {
            if ($null -ne $Object) {
                $parts.Add("$Object")
            }
        }
        end {
            $text = ($parts -join ' ').Trim()
            if (-not $text) { return }
            # Log only — never pop up a dialog or flood the status label per line.
            if ($script:AlfredInstallLogPath -and (Get-Command Write-AlfredInstallLog -ErrorAction SilentlyContinue)) {
                Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Message $text
            }
        }
    }
}
