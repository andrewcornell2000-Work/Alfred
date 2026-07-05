#Requires -Version 5.1
# Alfred install wizard — modern WinForms UI for Alfred-Install.ps1

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
    Add-Type -AssemblyName System.Drawing

    $form = New-AlfredInstallShellForm 'Alfred Installer'
    Set-AlfredFormIcon $form $AssetsRoot

    $brand = New-AlfredBrandPanel 300
    $form.Controls.Add($brand)

    $brandInner = New-Object System.Windows.Forms.Panel
    $brandInner.Dock = 'Fill'
    $brandInner.Padding = New-Object System.Windows.Forms.Padding 36, 40, 28, 32
    $brandInner.BackColor = [System.Drawing.Color]::Transparent
    $brand.Controls.Add($brandInner)

    $logoBox = New-Object System.Windows.Forms.PictureBox
    $logoBox.Size = New-Object System.Drawing.Size 64, 64
    $logoBox.SizeMode = 'Zoom'
    $logoBox.BackColor = [System.Drawing.Color]::Transparent
    $brandImage = Get-AlfredBrandImage $AssetsRoot
    if ($brandImage) { $logoBox.Image = $brandImage }
    $brandInner.Controls.Add($logoBox)

    $brandTitle = New-Object System.Windows.Forms.Label
    $brandTitle.Text = 'Alfred'
    $brandTitle.AutoSize = $true
    $brandTitle.Font = Get-AlfredUiFont 26 'Semibold'
    $brandTitle.ForeColor = $script:AlfredUiTheme.Text
    $brandTitle.Location = New-Object System.Drawing.Point 0, 80
    $brandInner.Controls.Add($brandTitle)

    $brandTag = New-Object System.Windows.Forms.Label
    $brandTag.Text = 'AI toolchain pack for Cursor, Claude Code, and Codex.'
    $brandTag.Size = New-Object System.Drawing.Size 220, 48
    $brandTag.Font = Get-AlfredUiFont 10
    $brandTag.ForeColor = $script:AlfredUiTheme.TextMuted
    $brandTag.Location = New-Object System.Drawing.Point 0, 118
    $brandInner.Controls.Add($brandTag)

    $features = @(
        'Power BI, Excel, GitHub MCPs',
        'Skills and LeanCTX globally wired',
        'User-scope installs, no admin'
    )
    $fy = 190
    foreach ($feature in $features) {
        $row = New-Object System.Windows.Forms.Panel
        $row.Size = New-Object System.Drawing.Size 230, 28
        $row.Location = New-Object System.Drawing.Point 0, $fy
        $row.BackColor = [System.Drawing.Color]::Transparent

        $mark = New-Object System.Windows.Forms.Label
        $mark.Text = [char]0x2713
        $mark.Font = Get-AlfredUiFont 10 'Bold'
        $mark.ForeColor = $script:AlfredUiTheme.Accent
        $mark.AutoSize = $true
        $mark.Location = New-Object System.Drawing.Point 0, 2
        $row.Controls.Add($mark)

        $txt = New-Object System.Windows.Forms.Label
        $txt.Text = $feature
        $txt.Font = Get-AlfredUiFont 9.5
        $txt.ForeColor = $script:AlfredUiTheme.TextMuted
        $txt.AutoSize = $true
        $txt.Location = New-Object System.Drawing.Point 22, 2
        $row.Controls.Add($txt)

        $brandInner.Controls.Add($row)
        $fy += 30
    }

    $version = New-Object System.Windows.Forms.Label
    $version.Text = 'github.com/andrewcornell2000-Work/Alfred'
    $version.AutoSize = $true
    $version.Font = Get-AlfredUiFont 8.5
    $version.ForeColor = $script:AlfredUiTheme.TextDim
    $version.Anchor = 'Bottom,Left'
    $version.Location = New-Object System.Drawing.Point 36, 430
    $brand.Controls.Add($version)

    $content = New-Object System.Windows.Forms.Panel
    $content.Dock = 'Fill'
    $content.Padding = New-Object System.Windows.Forms.Padding 40, 36, 40, 24
    $content.BackColor = $script:AlfredUiTheme.BgDeep
    $form.Controls.Add($content)

    $heading = New-Object System.Windows.Forms.Label
    $heading.Text = 'Install or update'
    $heading.AutoSize = $true
    $heading.Font = Get-AlfredUiFont 20 'Semibold'
    $heading.ForeColor = $script:AlfredUiTheme.Text
    $heading.Dock = 'Top'
    $heading.Height = 36
    $content.Controls.Add($heading)

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = 'Alfred clones or updates the pack on your machine, then provisions MCPs and skills.'
    $sub.Size = New-Object System.Drawing.Size 420, 44
    $sub.Font = Get-AlfredUiFont 10
    $sub.ForeColor = $script:AlfredUiTheme.TextMuted
    $sub.Dock = 'Top'
    $sub.Height = 44
    $content.Controls.Add($sub)

    $spacer = New-Object System.Windows.Forms.Panel
    $spacer.Height = 20
    $spacer.Dock = 'Top'
    $spacer.BackColor = [System.Drawing.Color]::Transparent
    $content.Controls.Add($spacer)

    $pathLabel = New-Object System.Windows.Forms.Label
    $pathLabel.Text = 'INSTALL FOLDER'
    $pathLabel.AutoSize = $true
    $pathLabel.Font = Get-AlfredUiFont 8.5 'Bold'
    $pathLabel.ForeColor = $script:AlfredUiTheme.TextDim
    $pathLabel.Dock = 'Top'
    $pathLabel.Height = 20
    $content.Controls.Add($pathLabel)

    $pathRow = New-Object System.Windows.Forms.Panel
    $pathRow.Dock = 'Top'
    $pathRow.Height = 48
    $pathRow.Padding = New-Object System.Windows.Forms.Padding 0, 6, 0, 0
    $pathRow.BackColor = [System.Drawing.Color]::Transparent
    $content.Controls.Add($pathRow)

    $pathHost = New-AlfredModernTextBox $DefaultInstallPath
    $pathHost.Dock = 'Left'
    $pathHost.Width = 340
    $pathRow.Controls.Add($pathHost)
    $pathBox = $pathHost.InnerTextBox

    $browse = New-AlfredModernButton 'Browse' 'ghost' (New-Object System.Drawing.Size 96, 42)
    $browse.Location = New-Object System.Drawing.Point 352, 0
    $browse.Add_Click({
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = 'Choose where Alfred should be installed'
        if ($pathBox.Text) { $dlg.SelectedPath = $pathBox.Text }
        if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $pathBox.Text = $dlg.SelectedPath
        }
    })
    $pathRow.Controls.Add($browse)

    $repoNote = New-Object System.Windows.Forms.Label
    $repoNote.Text = "Source: $RepoUrl"
    $repoNote.Size = New-Object System.Drawing.Size 420, 36
    $repoNote.Font = Get-AlfredUiFont 8.5
    $repoNote.ForeColor = $script:AlfredUiTheme.TextDim
    $repoNote.Dock = 'Top'
    $repoNote.Height = 28
    $content.Controls.Add($repoNote)

    $footer = New-Object System.Windows.Forms.Panel
    $footer.Dock = 'Bottom'
    $footer.Height = 72
    $footer.Padding = New-Object System.Windows.Forms.Padding 0, 16, 0, 0
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $content.Controls.Add($footer)

    $footerLine = New-Object System.Windows.Forms.Panel
    $footerLine.Dock = 'Top'
    $footerLine.Height = 1
    $footerLine.BackColor = $script:AlfredUiTheme.Border
    $footer.Controls.Add($footerLine)

    $btnRow = New-Object System.Windows.Forms.Panel
    $btnRow.Dock = 'Fill'
    $btnRow.BackColor = [System.Drawing.Color]::Transparent
    $footer.Controls.Add($btnRow)

    $outcome = @{ Confirmed = $false; InstallPath = $DefaultInstallPath }

    $btnCancel = New-AlfredModernButton 'Cancel' 'ghost' (New-Object System.Drawing.Size 104, 42)
    $btnCancel.Anchor = 'Top,Right'
    $btnCancel.Location = New-Object System.Drawing.Point 250, 14
    $btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $btnRow.Controls.Add($btnCancel)

    $btnInstall = New-AlfredModernButton 'Continue' 'primary' (New-Object System.Drawing.Size 132, 42)
    $btnInstall.Anchor = 'Top,Right'
    $btnInstall.Location = New-Object System.Drawing.Point 362, 14
    $btnInstall.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $btnRow.Controls.Add($btnInstall)

    $btnRow.Add_Resize({
        $btnInstall.Location = New-Object System.Drawing.Point ($btnRow.ClientSize.Width - 132), 14
        $btnCancel.Location = New-Object System.Drawing.Point ($btnRow.ClientSize.Width - 244), 14
    })

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

    $form.Dispose()
    return $outcome
}

function Show-AlfredInstallComplete {
    param(
        [string]$InstallPath
    )

    Show-AlfredModernDialog -Title 'Alfred is ready' -Message @"
Installation finished successfully.

Folder:
$InstallPath

Launch Alfred from your desktop shortcut or run run-alfred.bat.
"@ -Mode 'info' | Out-Null
}
