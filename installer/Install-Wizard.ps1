#Requires -Version 5.1
# Alfred install wizard — WinForms UI shown by Alfred-Install.ps1

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

    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Alfred Installer'
    $form.Size = New-Object System.Drawing.Size(560, 520)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = [System.Drawing.Color]::FromArgb(26, 35, 50)
    $form.ForeColor = [System.Drawing.Color]::White
    $form.Font = New-Object System.Drawing.Font('Segoe UI', 10)

    Set-AlfredFormIcon $form $AssetsRoot

    $y = 20
    $brandImage = Get-AlfredBrandImage $AssetsRoot
    if ($brandImage) {
        $pic = New-Object System.Windows.Forms.PictureBox
        $pic.Image = $brandImage
        $pic.SizeMode = 'Zoom'
        $pic.Size = New-Object System.Drawing.Size(72, 72)
        $pic.Location = New-Object System.Drawing.Point(244, $y)
        $form.Controls.Add($pic)
        $y += 84
    }

    $title = New-Object System.Windows.Forms.Label
    $title.Text = 'Alfred Pack'
    $title.AutoSize = $true
    $title.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 18)
    $title.ForeColor = [System.Drawing.Color]::White
    $title.Location = New-Object System.Drawing.Point(220, $y)
    $form.Controls.Add($title)
    $y += 36

    $tag = New-Object System.Windows.Forms.Label
    $tag.Text = 'One-click AI toolchain for Cursor, Claude Code, and Codex'
    $tag.AutoSize = $true
    $tag.ForeColor = [System.Drawing.Color]::FromArgb(200, 206, 214)
    $tag.Location = New-Object System.Drawing.Point(92, $y)
    $form.Controls.Add($tag)
    $y += 36

    $bullets = @(
        'MCP servers for Power BI, Excel, GitHub, and more',
        'Skills + LeanCTX wired globally on your machine',
        'No admin required - user-scope installs when possible'
    )
    foreach ($line in $bullets) {
        $lbl = New-Object System.Windows.Forms.Label
        $lbl.Text = [char]0x2022 + ' ' + $line
        $lbl.AutoSize = $true
        $lbl.ForeColor = [System.Drawing.Color]::FromArgb(176, 184, 196)
        $lbl.Location = New-Object System.Drawing.Point(36, $y)
        $form.Controls.Add($lbl)
        $y += 22
    }
    $y += 8

    $pathLabel = New-Object System.Windows.Forms.Label
    $pathLabel.Text = 'Install folder'
    $pathLabel.AutoSize = $true
    $pathLabel.Location = New-Object System.Drawing.Point(36, $y)
    $form.Controls.Add($pathLabel)
    $y += 24

    $pathBox = New-Object System.Windows.Forms.TextBox
    $pathBox.Text = $DefaultInstallPath
    $pathBox.Size = New-Object System.Drawing.Size(360, 28)
    $pathBox.Location = New-Object System.Drawing.Point(36, $y)
    $form.Controls.Add($pathBox)

    $browse = New-Object System.Windows.Forms.Button
    $browse.Text = 'Browse...'
    $browse.Size = New-Object System.Drawing.Size(96, 28)
    $browse.Location = New-Object System.Drawing.Point(408, $y)
    $browse.Add_Click({
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = 'Choose where Alfred should be installed'
        if ($pathBox.Text) { $dlg.SelectedPath = $pathBox.Text }
        if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $pathBox.Text = $dlg.SelectedPath
        }
    })
    $form.Controls.Add($browse)
    $y += 44

    $repoLabel = New-Object System.Windows.Forms.Label
    $repoLabel.Text = "Repository: $RepoUrl"
    $repoLabel.AutoSize = $true
    $repoLabel.ForeColor = [System.Drawing.Color]::FromArgb(140, 148, 160)
    $repoLabel.Font = New-Object System.Drawing.Font('Segoe UI', 8.5)
    $repoLabel.Location = New-Object System.Drawing.Point(36, $y)
    $form.Controls.Add($repoLabel)
    $y += 36

    $outcome = @{ Confirmed = $false; InstallPath = $DefaultInstallPath }

    $btnCancel = New-Object System.Windows.Forms.Button
    $btnCancel.Text = 'Cancel'
    $btnCancel.Size = New-Object System.Drawing.Size(100, 34)
    $btnCancel.Location = New-Object System.Drawing.Point(320, $y)
    $btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Controls.Add($btnCancel)

    $btnInstall = New-Object System.Windows.Forms.Button
    $btnInstall.Text = 'Install / Update'
    $btnInstall.Size = New-Object System.Drawing.Size(140, 34)
    $btnInstall.Location = New-Object System.Drawing.Point(364, $y)
    $btnInstall.BackColor = [System.Drawing.Color]::FromArgb(212, 175, 55)
    $btnInstall.ForeColor = [System.Drawing.Color]::FromArgb(26, 35, 50)
    $btnInstall.FlatStyle = 'Flat'
    $btnInstall.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Controls.Add($btnInstall)

    $form.AcceptButton = $btnInstall
    $form.CancelButton = $btnCancel

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $path = $pathBox.Text.Trim()
        if (-not $path) {
            [System.Windows.Forms.MessageBox]::Show(
                'Choose an install folder.',
                'Alfred Installer',
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            ) | Out-Null
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

    Add-Type -AssemblyName System.Windows.Forms

    [System.Windows.Forms.MessageBox]::Show(
        @"
Alfred is ready.

Install folder:
$InstallPath

Launch Alfred from your desktop shortcut, or run:
run-alfred.bat
"@,
        'Alfred installation complete',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
}
