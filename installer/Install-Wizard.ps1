#Requires -Version 5.1
# Alfred install wizard — WinForms UI for Alfred-Install.ps1

function Show-AlfredInstallWizard {
    param(
        [string]$DefaultInstallPath = "$env:USERPROFILE\Alfred",
        [string]$RepoUrl = 'https://github.com/andrewcornell2000-Work/Alfred.git',
        [string]$AssetsRoot
    )

    if ([string]::IsNullOrWhiteSpace($AssetsRoot)) {
        $AssetsRoot = Get-AlfredInstallerRoot
    }

    Add-Type -AssemblyName System.Windows.Forms
    Initialize-AlfredUiTheme
    Hide-AlfredConsole

    $form = New-AlfredInstallShellForm 'Alfred Installer'
    Set-AlfredFormIcon $form $AssetsRoot

    $root = New-Object System.Windows.Forms.TableLayoutPanel
    $root.Dock = 'Fill'
    $root.ColumnCount = 2
    $root.RowCount = 1
    $root.Padding = [System.Windows.Forms.Padding]::Empty
    $root.Margin = [System.Windows.Forms.Padding]::Empty
    [void]$root.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Absolute, 348)))
    [void]$root.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 100)))
    [void]$root.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Percent, 100)))
    $form.Controls.Add($root)

    # ── Left brand column ──────────────────────────────────────────────────────
    $brand = New-AlfredBrandPanel
    $brand.Margin = [System.Windows.Forms.Padding]::Empty

    $brandStack = New-Object System.Windows.Forms.TableLayoutPanel
    $brandStack.Dock = 'Fill'
    $brandStack.ColumnCount = 1
    $brandStack.RowCount = 5
    $brandStack.Padding = New-Object System.Windows.Forms.Padding(32, 36, 28, 36)
    $brandStack.BackColor = [System.Drawing.Color]::Transparent
    $brandContentWidth = 276
    foreach ($pct in @(0, 0, 0, 100, 0)) {
        $st = if ($pct -eq 100) { [System.Windows.Forms.SizeType]::Percent } else { [System.Windows.Forms.SizeType]::AutoSize }
        [void]$brandStack.RowStyles.Add((New-Object System.Windows.Forms.RowStyle($st, [float]$pct)))
    }
    $brand.Controls.Add($brandStack)

    $logoBox = New-AlfredLogoPictureBox -Root $AssetsRoot -Width 168 -Height 168 -BackgroundVariant Plain
    $logoBox.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 16)
    $brandStack.Controls.Add($logoBox, 0, 0)

    $brandTitle = New-AlfredWrappedLabel -Text 'Alfred' -MaxWidth $brandContentWidth `
        -Font (Get-AlfredUiFont 28 'Semibold') -ForeColor $script:AlfredUiTheme.Text `
        -Margin (New-Object System.Windows.Forms.Padding(0, 0, 0, 8))
    $brandStack.Controls.Add($brandTitle, 0, 1)

    $brandTag = New-AlfredWrappedLabel -Text 'Your AI toolchain for Cursor, Claude Code, and Codex.' `
        -MaxWidth $brandContentWidth -Font (Get-AlfredUiFont 10.5) -ForeColor $script:AlfredUiTheme.TextMuted `
        -Margin (New-Object System.Windows.Forms.Padding(0, 0, 0, 20))
    $brandStack.Controls.Add($brandTag, 0, 2)

    $featurePanel = New-Object System.Windows.Forms.Panel
    $featurePanel.Dock = 'Fill'
    $featurePanel.AutoScroll = $false
    $featurePanel.BackColor = [System.Drawing.Color]::Transparent
    $featurePanel.Margin = [System.Windows.Forms.Padding]::Empty

    $featureStack = New-Object System.Windows.Forms.FlowLayoutPanel
    $featureStack.Dock = 'Fill'
    $featureStack.FlowDirection = 'TopDown'
    $featureStack.WrapContents = $false
    $featureStack.AutoSize = $true
    $featureStack.AutoSizeMode = [System.Windows.Forms.AutoSizeMode]::GrowAndShrink
    $featureStack.BackColor = [System.Drawing.Color]::Transparent
    $featureStack.Margin = [System.Windows.Forms.Padding]::Empty
    $featurePanel.Controls.Add($featureStack)

    foreach ($feature in @(
        'Power BI, Excel, and GitHub MCPs',
        'Skills, MCPs, and rules wired globally',
        'Closes Cursor, Claude, and ChatGPT during install',
        'User-scope installs - no admin'
    )) {
        $mark = New-AlfredWrappedLabel -Text ([char]0x2713 + '  ' + $feature) `
            -MaxWidth $brandContentWidth -Font (Get-AlfredUiFont 10) `
            -ForeColor $script:AlfredUiTheme.TextMuted `
            -Margin (New-Object System.Windows.Forms.Padding(0, 0, 0, 12))
        [void]$featureStack.Controls.Add($mark)
    }
    $brandStack.Controls.Add($featurePanel, 0, 3)

    $version = New-AlfredWrappedLabel -Text 'github.com/andrewcornell2000-Work/Alfred' `
        -MaxWidth $brandContentWidth -Font (Get-AlfredUiFont 8.5) `
        -ForeColor $script:AlfredUiTheme.TextDim `
        -Margin (New-Object System.Windows.Forms.Padding(0, 16, 0, 0))
    $brandStack.Controls.Add($version, 0, 4)

    [void]$root.Controls.Add($brand, 0, 0)

    # ── Right content column ───────────────────────────────────────────────────
    $contentWidth = 480
    $content = New-Object System.Windows.Forms.TableLayoutPanel
    $content.Dock = 'Fill'
    $content.ColumnCount = 1
    $content.RowCount = 7
    $content.Padding = New-Object System.Windows.Forms.Padding(48, 44, 48, 28)
    $content.BackColor = $script:AlfredUiTheme.BgDeep
    $content.Margin = [System.Windows.Forms.Padding]::Empty
    foreach ($pct in @(0, 0, 0, 0, 0, 100, 0)) {
        $st = if ($pct -eq 100) { [System.Windows.Forms.SizeType]::Percent } else { [System.Windows.Forms.SizeType]::AutoSize }
        [void]$content.RowStyles.Add((New-Object System.Windows.Forms.RowStyle($st, [float]$pct)))
    }
    [void]$root.Controls.Add($content, 1, 0)

    $heading = New-Object System.Windows.Forms.Label
    $heading.Text = 'Install or update'
    $heading.AutoSize = $true
    $heading.MaximumSize = New-Object System.Drawing.Size($contentWidth, 0)
    $heading.Font = Get-AlfredUiFont 22 'Semibold'
    $heading.ForeColor = $script:AlfredUiTheme.Text
    $heading.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 10)
    $content.Controls.Add($heading, 0, 0)

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = 'Alfred will clone or update the pack on your machine, then provision MCPs and skills.'
    $sub.AutoSize = $true
    $sub.MaximumSize = New-Object System.Drawing.Size($contentWidth, 0)
    $sub.Font = Get-AlfredUiFont 10.5
    $sub.ForeColor = $script:AlfredUiTheme.TextMuted
    $sub.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 32)
    $content.Controls.Add($sub, 0, 1)

    $pathLabel = New-Object System.Windows.Forms.Label
    $pathLabel.Text = 'INSTALL FOLDER'
    $pathLabel.AutoSize = $true
    $pathLabel.Font = Get-AlfredUiFont 8.5 'Bold'
    $pathLabel.ForeColor = $script:AlfredUiTheme.TextDim
    $pathLabel.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 8)
    $content.Controls.Add($pathLabel, 0, 2)

    $pathRow = New-Object System.Windows.Forms.TableLayoutPanel
    $pathRow.ColumnCount = 2
    $pathRow.RowCount = 1
    $pathRow.Height = 44
    $pathRow.Dock = 'Fill'
    $pathRow.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 12)
    [void]$pathRow.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 100)))
    [void]$pathRow.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Absolute, 104)))
    $content.Controls.Add($pathRow, 0, 3)

    $pathBox = New-AlfredModernTextBox $DefaultInstallPath
    $pathBox.Dock = 'Fill'
    $pathBox.Margin = New-Object System.Windows.Forms.Padding(0, 0, 10, 0)
    $pathRow.Controls.Add($pathBox, 0, 0)

    $browse = New-AlfredModernButton -Text 'Browse' -Variant 'ghost' -Width 96 -Height 40
    $browse.Anchor = 'Top,Right'
    $browse.Margin = New-Object System.Windows.Forms.Padding(0, 2, 0, 0)
    $browse.Add_Click({
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = 'Choose where Alfred should be installed'
        if ($pathBox.Text) { $dlg.SelectedPath = $pathBox.Text }
        if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $pathBox.Text = $dlg.SelectedPath
        }
    })
    $pathRow.Controls.Add($browse, 1, 0)

    $repoNote = New-Object System.Windows.Forms.Label
    $repoNote.Text = "Source: $RepoUrl"
    $repoNote.AutoSize = $true
    $repoNote.MaximumSize = New-Object System.Drawing.Size($contentWidth, 0)
    $repoNote.Font = Get-AlfredUiFont 8.5
    $repoNote.ForeColor = $script:AlfredUiTheme.TextDim
    $content.Controls.Add($repoNote, 0, 4)

    $fillSpacer = New-Object System.Windows.Forms.Panel
    $fillSpacer.Dock = 'Fill'
    $fillSpacer.BackColor = [System.Drawing.Color]::Transparent
    $content.Controls.Add($fillSpacer, 0, 5)

    $footer = New-Object System.Windows.Forms.Panel
    $footer.Dock = 'Fill'
    $footer.Height = 68
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $footer.Margin = [System.Windows.Forms.Padding]::Empty

    $footerLine = New-Object System.Windows.Forms.Panel
    $footerLine.Dock = 'Top'
    $footerLine.Height = 1
    $footerLine.BackColor = $script:AlfredUiTheme.Border
    $footer.Controls.Add($footerLine)

    $btnRow = New-Object System.Windows.Forms.FlowLayoutPanel
    $btnRow.Dock = 'Fill'
    $btnRow.FlowDirection = 'RightToLeft'
    $btnRow.WrapContents = $false
    $btnRow.Padding = New-Object System.Windows.Forms.Padding(0, 16, 0, 0)
    $btnRow.BackColor = [System.Drawing.Color]::Transparent
    $footer.Controls.Add($btnRow)

    $outcome = @{ Confirmed = $false; InstallPath = $DefaultInstallPath }

    $btnInstall = New-AlfredModernButton -Text 'Continue' -Variant 'primary' -Width 140 -Height 42
    $btnInstall.Margin = New-Object System.Windows.Forms.Padding(10, 0, 0, 0)
    $btnInstall.DialogResult = [System.Windows.Forms.DialogResult]::OK
    [void]$btnRow.Controls.Add($btnInstall)

    $btnCancel = New-AlfredModernButton -Text 'Cancel' -Variant 'ghost' -Width 110 -Height 42
    $btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    [void]$btnRow.Controls.Add($btnCancel)

    $content.Controls.Add($footer, 0, 6)

    $form.AcceptButton = $btnInstall
    $form.CancelButton = $btnCancel

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $path = $pathBox.Text.Trim()
        if (-not $path) {
            Show-AlfredModernDialog -Title 'Install folder required' -Message 'Choose a folder where Alfred should be installed.' -Mode 'info' | Out-Null
        } else {
            $outcome.Confirmed = $true
            $outcome.InstallPath = $path
        }
    }

    if ($logoBox.Image) { $logoBox.Image.Dispose() }
    $form.Dispose()
    return $outcome
}
