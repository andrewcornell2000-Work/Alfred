#Requires -Version 5.1
# GUI update prompt — used by check-updates.ps1 and Alfred-Install.ps1

function Show-AlfredUpdateAlert {
    param(
        [Parameter(Mandatory = $true)]
        [int]$BehindCount,
        [Parameter(Mandatory = $true)]
        [string[]]$CommitLines,
        [string]$Root,
        [string]$Title = 'Update available'
    )

    if ([string]::IsNullOrWhiteSpace($Root)) {
        $Root = Get-AlfredInstallerRoot
    }

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-AlfredInstallShellForm 'Alfred'
    $form.Size = New-Object System.Drawing.Size(640, 480)
    $form.MinimumSize = $form.Size
    $form.MaximumSize = $form.Size
    Set-AlfredFormIcon $form $Root

    $content = New-Object System.Windows.Forms.Panel
    $content.Dock = 'Fill'
    $content.Padding = New-Object System.Windows.Forms.Padding 32, 28, 32, 20
    $content.BackColor = $script:AlfredUiTheme.BgDeep
    $form.Controls.Add($content)

    $head = New-Object System.Windows.Forms.Label
    $head.Text = "$BehindCount new commit(s) on main"
    $head.Dock = 'Top'
    $head.Height = 34
    $head.Font = Get-AlfredUiFont 18 'Semibold'
    $head.ForeColor = $script:AlfredUiTheme.Text
    $content.Controls.Add($head)

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = 'Pull the latest Alfred pack now? Setup will re-run if needed.'
    $sub.Dock = 'Top'
    $sub.Height = 28
    $sub.Font = Get-AlfredUiFont 10
    $sub.ForeColor = $script:AlfredUiTheme.TextMuted
    $content.Controls.Add($sub)

    $listHost = New-Object System.Windows.Forms.Panel
    $listHost.Dock = 'Fill'
    $listHost.Padding = New-Object System.Windows.Forms.Padding 0, 12, 0, 12
    $listHost.BackColor = [System.Drawing.Color]::Transparent
    $content.Controls.Add($listHost)

    $list = New-Object System.Windows.Forms.TextBox
    $list.Multiline = $true
    $list.ReadOnly = $true
    $list.ScrollBars = 'Vertical'
    $list.BorderStyle = 'None'
    $list.BackColor = $script:AlfredUiTheme.BgInput
    $list.ForeColor = $script:AlfredUiTheme.Text
    $list.Font = Get-AlfredUiFont 9.5
    $list.Dock = 'Fill'
    $list.Text = ($CommitLines | Select-Object -First 14) -join [Environment]::NewLine
    $listHost.Controls.Add($list)

    Enable-AlfredDoubleBuffer $listHost
    $listHost.Add_Paint({
        param($sender, $e)
        $g = $e.Graphics
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $rect = New-Object System.Drawing.Rectangle 0, 0, $sender.Width - 1, $sender.Height - 1
        $path = New-AlfredRoundedPath $rect 10
        $g.FillPath((New-Object System.Drawing.SolidBrush $script:AlfredUiTheme.BgInput), $path)
        $g.DrawPath((New-Object System.Drawing.Pen $script:AlfredUiTheme.Border, 1), $path)
        $path.Dispose()
    })

    $footer = New-Object System.Windows.Forms.Panel
    $footer.Dock = 'Bottom'
    $footer.Height = 58
    $footer.BackColor = $script:AlfredUiTheme.BgDeep
    $content.Controls.Add($footer)

    $result = 'later'

    $btnLater = New-AlfredModernButton 'Later' 'ghost' (New-Object System.Drawing.Size 104, 42)
    $btnLater.Anchor = 'Top,Right'
    $btnLater.Location = New-Object System.Drawing.Point 360, 8
    $btnLater.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $footer.Controls.Add($btnLater)

    $btnUpdate = New-AlfredModernButton 'Update now' 'primary' (New-Object System.Drawing.Size 132, 42)
    $btnUpdate.Anchor = 'Top,Right'
    $btnUpdate.Location = New-Object System.Drawing.Point 472, 8
    $btnUpdate.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $footer.Controls.Add($btnUpdate)

    $footer.Add_Resize({
        $btnUpdate.Location = New-Object System.Drawing.Point ($footer.ClientSize.Width - 132), 8
        $btnLater.Location = New-Object System.Drawing.Point ($footer.ClientSize.Width - 244), 8
    })

    $form.AcceptButton = $btnUpdate
    $form.CancelButton = $btnLater

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $result = 'update'
    }

    $form.Dispose()
    return $result
}
