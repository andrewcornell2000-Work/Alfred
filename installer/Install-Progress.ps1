#Requires -Version 5.1
# Staged install progress UI for Alfred-Install.ps1 (GUI / .exe path).

function Get-AlfredInstallStageDefinitions {
    @(
        @{ Id = 'prepare';    Label = 'Preparing installer'; Weight = 5 }
        @{ Id = 'requirements'; Label = 'Checking system requirements'; Weight = 12 }
        @{ Id = 'core';       Label = 'Installing core files'; Weight = 28 }
        @{ Id = 'configure';  Label = 'Configuring AI access'; Weight = 18 }
        @{ Id = 'mcps';       Label = 'Installing skills, rules & MCPs'; Weight = 17 }
        @{ Id = 'verify';     Label = 'Verifying installation'; Weight = 10 }
        @{ Id = 'finalize';   Label = 'Finalising setup'; Weight = 10 }
    )
}

function Get-AlfredInstallLogPath {
    param([string]$InstallPath)
    if (-not [string]::IsNullOrWhiteSpace($InstallPath) -and (Test-Path $InstallPath)) {
        $logsDir = Join-Path $InstallPath 'logs'
        if (-not (Test-Path $logsDir)) {
            New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
        }
        return Join-Path $logsDir 'install.log'
    }
    $fallback = Join-Path $env:LOCALAPPDATA 'Alfred\logs'
    if (-not (Test-Path $fallback)) {
        New-Item -ItemType Directory -Path $fallback -Force | Out-Null
    }
    return Join-Path $fallback 'install.log'
}

function Write-AlfredInstallLog {
    param(
        [string]$Message,
        [string]$Level = 'INFO',
        [string]$LogPath
    )
    if ([string]::IsNullOrWhiteSpace($LogPath)) { return }
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    try {
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    } catch { }
}

function New-AlfredStageRow {
    param(
        [string]$Label,
        [System.Drawing.Font]$FontPending,
        [System.Drawing.Font]$FontActive,
        [int]$ContentWidth = 250
    )

    $row = New-Object System.Windows.Forms.Panel
    $row.Width = 288
    $row.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 4)
    $row.BackColor = [System.Drawing.Color]::Transparent

    $icon = New-Object System.Windows.Forms.Label
    $icon.Text = [char]0x25CB
    $icon.AutoSize = $true
    $icon.Font = Get-AlfredUiFont 11
    $icon.ForeColor = $script:AlfredUiTheme.TextDim
    $icon.Location = New-Object System.Drawing.Point(0, 2)
    $icon.Width = 22
    $row.Controls.Add($icon)

    $text = New-AlfredWrappedLabel -Text $Label -MaxWidth $ContentWidth -Font $FontPending `
        -ForeColor $script:AlfredUiTheme.TextDim
    $text.Location = New-Object System.Drawing.Point(26, 0)
    $row.Controls.Add($text)

    $preferred = $text.PreferredSize
    $row.Height = [Math]::Max(34, $preferred.Height + 4)
    $row.AutoSize = $false

    return [PSCustomObject]@{
        Panel       = $row
        IconLabel   = $icon
        TextLabel   = $text
        FontPending = $FontPending
        FontActive  = $FontActive
        State       = 'pending'
    }
}

function Update-AlfredInstallStageVisuals {
    param($Ctx)

    if (-not $Ctx) { return }

    $completedWeight = 0
    foreach ($def in $Ctx.StageDefs) {
        $row = $Ctx.StageRows[$def.Id]
        if (-not $row) { continue }
        if ($Ctx.CompletedIds -contains $def.Id) {
            $completedWeight += $def.Weight
            $row.State = 'complete'
            $row.IconLabel.Text = [char]0x2713  # checkmark
            $row.IconLabel.ForeColor = [System.Drawing.Color]::FromArgb(22, 163, 74)
            $row.TextLabel.Font = $row.FontPending
            $row.TextLabel.ForeColor = $script:AlfredUiTheme.TextMuted
        } elseif ($def.Id -eq $Ctx.CurrentStage) {
            $row.State = 'active'
            $row.IconLabel.Text = [char]0x25CF  # bullet
            $row.IconLabel.ForeColor = $script:AlfredUiTheme.Accent
            $row.TextLabel.Font = $row.FontActive
            $row.TextLabel.ForeColor = $script:AlfredUiTheme.Text
        } elseif ($row.State -eq 'error') {
            # keep error styling
        } else {
            $row.State = 'pending'
            $row.IconLabel.Text = [char]0x25CB
            $row.IconLabel.ForeColor = $script:AlfredUiTheme.TextDim
            $row.TextLabel.Font = $row.FontPending
            $row.TextLabel.ForeColor = $script:AlfredUiTheme.TextDim
        }
    }

    $activeDef = $Ctx.StageDefs | Where-Object { $_.Id -eq $Ctx.CurrentStage } | Select-Object -First 1
    $activeWeight = if ($activeDef) { [math]::Floor($activeDef.Weight / 2) } else { 0 }
    $pct = [int][math]::Min(100, [math]::Round((($completedWeight + $activeWeight) / $Ctx.TotalWeight) * 100))
    $Ctx.ProgressBar.Value = [math]::Max($Ctx.ProgressBar.Value, $pct)
    $Ctx.PercentLabel.Text = "$pct%"
    [System.Windows.Forms.Application]::DoEvents()
}

function Start-AlfredInstallProgress {
    param(
        [string]$InstallPath,
        [string]$AssetsRoot
    )

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms

    if ([string]::IsNullOrWhiteSpace($AssetsRoot)) {
        $AssetsRoot = Get-AlfredInstallerRoot
    }

    $script:AlfredInstallLogPath = Get-AlfredInstallLogPath -InstallPath $InstallPath
    Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Message 'Installer started.'

    $stageDefs = Get-AlfredInstallStageDefinitions
    $totalWeight = ($stageDefs | ForEach-Object { $_.Weight } | Measure-Object -Sum).Sum

    $form = New-AlfredInstallShellForm 'Installing Alfred'
    $form.Size = New-Object System.Drawing.Size(920, 640)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    Set-AlfredFormIcon $form $AssetsRoot

    $script:InstallClosingNormally = $false
    $script:InstallUserCancelled = $false
    $form.Add_FormClosing({
        param($sender, $e)
        if ($script:InstallClosingNormally) { return }
        if (-not (Get-Command Show-AlfredModernDialog -ErrorAction SilentlyContinue)) { return }
        $confirm = Show-AlfredModernDialog -Title 'Cancel installation?' -Message @"
Installation is still in progress.

Close the installer now?
"@ -Mode 'confirm' -PrimaryText 'Close installer' -SecondaryText 'Keep installing'
        if (-not $confirm) {
            $e.Cancel = $true
        } else {
            $script:InstallUserCancelled = $true
            Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Level 'WARN' -Message 'User closed installer during progress.'
        }
    })
    $form.Add_FormClosed({
        if ($script:InstallUserCancelled) {
            [System.Environment]::Exit(0)
        }
    })

    $root = New-Object System.Windows.Forms.TableLayoutPanel
    $root.Dock = 'Fill'
    $root.ColumnCount = 2
    $root.RowCount = 1
    $root.Padding = [System.Windows.Forms.Padding]::Empty
    [void]$root.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Absolute, 320)))
    [void]$root.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 100)))
    $form.Controls.Add($root)

    # ── Left: brand + stage list ─────────────────────────────────────────────
    $sidebar = New-AlfredBrandPanel -Variant Plain
    $sidebar.Dock = 'Fill'
    $sidebar.Padding = New-Object System.Windows.Forms.Padding(28, 36, 24, 28)

    $sidebarStack = New-Object System.Windows.Forms.TableLayoutPanel
    $sidebarStack.Dock = 'Fill'
    $sidebarStack.ColumnCount = 1
    $sidebarStack.RowCount = 3
    $sidebarStack.BackColor = [System.Drawing.Color]::Transparent
    [void]$sidebarStack.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::AutoSize)))
    [void]$sidebarStack.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::AutoSize)))
    [void]$sidebarStack.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Percent, 100)))
    $sidebar.Controls.Add($sidebarStack)

    $logoBox = New-AlfredLogoPictureBox -Root $AssetsRoot -Width 120 -Height 120 -BackgroundVariant Plain
    $logoBox.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 8)
    $sidebarStack.Controls.Add($logoBox, 0, 0)

    $sidebarTitle = New-Object System.Windows.Forms.Label
    $sidebarTitle.Text = 'Installing Alfred'
    $sidebarTitle.AutoSize = $true
    $sidebarTitle.Font = Get-AlfredUiFont 18 'Semibold'
    $sidebarTitle.ForeColor = $script:AlfredUiTheme.Text
    $sidebarTitle.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 16)
    $sidebarStack.Controls.Add($sidebarTitle, 0, 1)

    $stagePanel = New-Object System.Windows.Forms.FlowLayoutPanel
    $stagePanel.Dock = 'Fill'
    $stagePanel.FlowDirection = 'TopDown'
    $stagePanel.WrapContents = $false
    $stagePanel.AutoScroll = $false
    $stagePanel.HorizontalScroll.Enabled = $false
    $stagePanel.HorizontalScroll.Visible = $false
    $stagePanel.BackColor = [System.Drawing.Color]::Transparent
    $sidebarStack.Controls.Add($stagePanel, 0, 2)

    $fontPending = Get-AlfredUiFont 9.5
    $fontActive = Get-AlfredUiFont 9.5 'Semibold'
    $stageRows = @{}
    foreach ($def in $stageDefs) {
        $row = New-AlfredStageRow -Label $def.Label -FontPending $fontPending -FontActive $fontActive
        $stagePanel.Controls.Add($row.Panel)
        $stageRows[$def.Id] = $row
    }

    $root.Controls.Add($sidebar, 0, 0)

    # ── Right: active stage + detail + progress ────────────────────────────
    $main = New-Object System.Windows.Forms.Panel
    $main.Dock = 'Fill'
    $main.Padding = New-Object System.Windows.Forms.Padding(36, 40, 36, 32)
    $main.BackColor = $script:AlfredUiTheme.BgDeep
    $root.Controls.Add($main, 1, 0)

    $headline = New-Object System.Windows.Forms.Label
    $headline.Text = 'Preparing installer'
    $headline.AutoSize = $false
    $headline.Size = New-Object System.Drawing.Size(520, 40)
    $headline.Font = Get-AlfredUiFont 20 'Semibold'
    $headline.ForeColor = $script:AlfredUiTheme.Text
    $headline.Location = New-Object System.Drawing.Point(36, 40)
    $main.Controls.Add($headline)

    $subtitle = New-Object System.Windows.Forms.Label
    $subtitle.Text = 'This may take several minutes. Please keep this window open.'
    $subtitle.AutoSize = $false
    $subtitle.Size = New-Object System.Drawing.Size(520, 28)
    $subtitle.Font = Get-AlfredUiFont 10
    $subtitle.ForeColor = $script:AlfredUiTheme.TextMuted
    $subtitle.Location = New-Object System.Drawing.Point(36, 78)
    $main.Controls.Add($subtitle)

    $detail = New-Object System.Windows.Forms.Label
    $detail.Text = 'Initialising...'
    $detail.AutoSize = $false
    $detail.Size = New-Object System.Drawing.Size(520, 72)
    $detail.Font = Get-AlfredUiFont 10
    $detail.ForeColor = $script:AlfredUiTheme.TextDim
    $detail.Location = New-Object System.Drawing.Point(36, 118)
    $main.Controls.Add($detail)

    $percentLabel = New-Object System.Windows.Forms.Label
    $percentLabel.Text = '0%'
    $percentLabel.AutoSize = $true
    $percentLabel.Font = Get-AlfredUiFont 10 'Semibold'
    $percentLabel.ForeColor = $script:AlfredUiTheme.Accent
    $percentLabel.Location = New-Object System.Drawing.Point(36, 188)
    $main.Controls.Add($percentLabel)

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Style = 'Continuous'
    $bar.Minimum = 0
    $bar.Maximum = 100
    $bar.Value = 0
    $bar.Size = New-Object System.Drawing.Size(520, 10)
    $bar.Location = New-Object System.Drawing.Point(36, 212)
    $main.Controls.Add($bar)

    $form.Add_Shown({ $form.Activate() })
    $form.Show()
    [System.Windows.Forms.Application]::DoEvents()

    $state = @{
        StageDefs     = $stageDefs
        TotalWeight   = $totalWeight
        StageRows     = $stageRows
        CurrentStage  = $null
        CompletedIds  = [System.Collections.Generic.List[string]]::new()
        HeadlineLabel = $headline
        DetailLabel   = $detail
        PercentLabel  = $percentLabel
        ProgressBar   = $bar
        LogoBox       = $logoBox
    }

    $progress = [PSCustomObject]@{
        Form        = $form
        State       = $state
        StatusLabel = $detail
        LogPath     = $script:AlfredInstallLogPath
    }

    $progress | Add-Member -MemberType ScriptMethod -Name SetStage -Value {
        param([string]$StageId)
        if ($this.Form.IsDisposed) { return }
        $this.State.CurrentStage = $StageId
        $def = $this.State.StageDefs | Where-Object { $_.Id -eq $StageId } | Select-Object -First 1
        if ($def) {
            $this.State.HeadlineLabel.Text = $def.Label
        }
        Update-AlfredInstallStageVisuals $this.State
        Write-AlfredInstallLog -LogPath $this.LogPath -Message "Stage: $StageId"
    } -Force

    $progress | Add-Member -MemberType ScriptMethod -Name CompleteStage -Value {
        param([string]$StageId)
        if ($this.Form.IsDisposed) { return }
        if ($this.State.CompletedIds -notcontains $StageId) {
            [void]$this.State.CompletedIds.Add($StageId)
        }
        $def = $this.State.StageDefs | Where-Object { $_.Id -eq $StageId } | Select-Object -First 1
        if ($def) {
            $completedWeight = 0
            foreach ($d in $this.State.StageDefs) {
                if ($this.State.CompletedIds -contains $d.Id) { $completedWeight += $d.Weight }
            }
            $pct = [int][math]::Min(100, [math]::Round(($completedWeight / $this.State.TotalWeight) * 100))
            $this.State.ProgressBar.Value = $pct
            $this.State.PercentLabel.Text = "$pct%"
        }
        Update-AlfredInstallStageVisuals $this.State
        Write-AlfredInstallLog -LogPath $this.LogPath -Message "Completed stage: $StageId"
    } -Force

    $progress | Add-Member -MemberType ScriptMethod -Name SetDetail -Value {
        param([string]$Message)
        if ($this.Form.IsDisposed) { return }
        if ($this.State.DetailLabel -and -not $this.State.DetailLabel.IsDisposed) {
            $this.State.DetailLabel.Text = $Message
            [System.Windows.Forms.Application]::DoEvents()
        }
        if ($Message) {
            Write-AlfredInstallLog -LogPath $this.LogPath -Message $Message
        }
    } -Force

    $progress | Add-Member -MemberType ScriptMethod -Name SetStatus -Value {
        param([string]$Message)
        $this.SetDetail($Message)
    } -Force

    $progress | Add-Member -MemberType ScriptMethod -Name FailStage -Value {
        param([string]$StageId, [string]$Message)
        if ($this.Form.IsDisposed) { return }
        $row = $this.State.StageRows[$StageId]
        if ($row) {
            $row.State = 'error'
            $row.IconLabel.Text = [char]0x2717  # ✗
            $row.IconLabel.ForeColor = [System.Drawing.Color]::FromArgb(220, 38, 38)
            $row.TextLabel.ForeColor = [System.Drawing.Color]::FromArgb(220, 38, 38)
        }
        $this.State.DetailLabel.Text = $Message
        Write-AlfredInstallLog -LogPath $this.LogPath -Level 'ERROR' -Message $Message
        [System.Windows.Forms.Application]::DoEvents()
    } -Force

    $progress | Add-Member -MemberType ScriptMethod -Name Close -Value {
        $script:InstallClosingNormally = $true
        if (-not $this.Form.IsDisposed) {
            $this.Form.Close()
            $this.Form.Dispose()
        }
        if ($this.State.LogoBox -and $this.State.LogoBox.Image) {
            $this.State.LogoBox.Image.Dispose()
        }
    } -Force

    $progress.SetStage('prepare')
    $progress.SetDetail('Initialising installer...')
    return $progress
}

function Show-AlfredInstallError {
    param(
        [string]$Message,
        [string]$LogPath,
        [string]$Suggestion = 'Try running the installer again. If the problem persists, check the log file or re-run from PowerShell: .\Alfred-Install.ps1'
    )

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms

    if ($script:InstallProgress) {
        $script:InstallClosingNormally = $true
        $script:InstallProgress.Close()
    }

    $logHint = if ($LogPath) { "`n`nLog file:`n$LogPath" } else { '' }
    Show-AlfredModernDialog -Title 'Installation failed' -Message @"
Something went wrong during installation.

$Message

$Suggestion$logHint
"@ -Mode 'info' -PrimaryText 'Close' | Out-Null
}

function Show-AlfredInstallComplete {
    param(
        [string]$InstallPath,
        [string[]]$SummaryItems
    )

    Initialize-AlfredUiTheme
    Add-Type -AssemblyName System.Windows.Forms

    if ($script:InstallProgress) {
        $script:InstallClosingNormally = $true
        $script:InstallProgress.CompleteStage('finalize')
        $script:InstallProgress.State.ProgressBar.Value = 100
        $script:InstallProgress.State.PercentLabel.Text = '100%'
        $script:InstallProgress.Close()
    }

    $items = if ($SummaryItems -and $SummaryItems.Count -gt 0) {
        ($SummaryItems | ForEach-Object { "- $_" }) -join [Environment]::NewLine
    } else {
        @(
            '- Alfred core files and Python environment'
            '- Cursor / Claude Code / Codex skills, rules and MCPs'
            '- Desktop shortcut (Alfred.lnk)'
        ) -join [Environment]::NewLine
    }

    $form = New-AlfredInstallShellForm 'Installation complete'
    $form.Size = New-Object System.Drawing.Size(560, 480)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    Set-AlfredFormIcon $form (Get-AlfredInstallerRoot)

    $body = New-Object System.Windows.Forms.Panel
    $body.Dock = 'Fill'
    $body.Padding = New-Object System.Windows.Forms.Padding(36, 32, 36, 24)
    $body.BackColor = $script:AlfredUiTheme.BgDeep
    $form.Controls.Add($body)

    $okIcon = New-Object System.Windows.Forms.Label
    $okIcon.Text = [char]0x2713
    $okIcon.Font = Get-AlfredUiFont 28 'Semibold'
    $okIcon.ForeColor = [System.Drawing.Color]::FromArgb(22, 163, 74)
    $okIcon.AutoSize = $true
    $okIcon.Location = New-Object System.Drawing.Point(36, 32)
    $body.Controls.Add($okIcon)

    $title = New-Object System.Windows.Forms.Label
    $title.Text = 'Alfred installed successfully'
    $title.AutoSize = $false
    $title.Size = New-Object System.Drawing.Size(460, 36)
    $title.Font = Get-AlfredUiFont 20 'Semibold'
    $title.ForeColor = $script:AlfredUiTheme.Text
    $title.Location = New-Object System.Drawing.Point(72, 36)
    $body.Controls.Add($title)

    $msg = New-Object System.Windows.Forms.Label
    $msg.Text = @"
Alfred is ready to use.

Installed to:
$InstallPath

$items

Launch Alfred from your desktop shortcut or run run-alfred.bat.
If browser sign-in windows opened for Claude or Codex, complete them when convenient.
Restart Cursor after install so MCP changes take effect.
"@
    $msg.AutoSize = $false
    $msg.Size = New-Object System.Drawing.Size(480, 280)
    $msg.Font = Get-AlfredUiFont 10
    $msg.ForeColor = $script:AlfredUiTheme.TextMuted
    $msg.Location = New-Object System.Drawing.Point(36, 88)
    $body.Controls.Add($msg)

    $footer = New-Object System.Windows.Forms.FlowLayoutPanel
    $footer.Dock = 'Bottom'
    $footer.Height = 56
    $footer.FlowDirection = [System.Windows.Forms.FlowDirection]::RightToLeft
    $footer.Padding = New-Object System.Windows.Forms.Padding(0, 8, 0, 0)
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $body.Controls.Add($footer)

    $btnFinish = New-AlfredModernButton -Text 'Finish' -Variant 'primary' -Width 120
    $btnFinish.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() })
    $footer.Controls.Add($btnFinish)
    $form.AcceptButton = $btnFinish

    $form.ShowDialog() | Out-Null
    $form.Dispose()
}
