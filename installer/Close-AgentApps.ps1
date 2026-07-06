#Requires -Version 5.1
# Close Cursor, Claude Desktop, and ChatGPT before Alfred provisions hooks/rules.

function Get-AlfredAgentProcesses {
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -eq 'Claude' -or
        $_.ProcessName -eq 'ChatGPT' -or
        $_.ProcessName -like 'Cursor*'
    }
}

function Write-AgentCloseMsg {
    param(
        [ValidateSet('step', 'ok', 'warn', 'info')]
        [string]$Level,
        [string]$Message
    )

    switch ($Level) {
        'step' {
            if (Get-Command Write-Step -ErrorAction SilentlyContinue) { Write-Step $Message; return }
            Write-Host ""
            Write-Host "> $Message" -ForegroundColor Cyan
        }
        'ok' {
            if (Get-Command Write-OK -ErrorAction SilentlyContinue) { Write-OK $Message; return }
            Write-Host "  [OK]    $Message" -ForegroundColor Green
        }
        'warn' {
            if (Get-Command Write-Warn2 -ErrorAction SilentlyContinue) { Write-Warn2 $Message; return }
            if (Get-Command Write-Warn -ErrorAction SilentlyContinue) { Write-Warn $Message; return }
            Write-Host "  [WARN]  $Message" -ForegroundColor Yellow
        }
        'info' {
            if (Get-Command Write-Info -ErrorAction SilentlyContinue) { Write-Info $Message; return }
            Write-Host "          $Message" -ForegroundColor DarkYellow
        }
    }
}

function Stop-AlfredAgentProcesses {
    <#
    .SYNOPSIS
        Gracefully then forcefully closes Cursor, Claude Desktop, and ChatGPT.
    .DESCRIPTION
        Ensures ~/.cursor hooks and rules are not locked or re-written by running
        agent apps during Alfred install or provision.
    #>
    param(
        [int]$GraceSec = 5,
        [int]$WaitSec = 15,
        [switch]$Quiet
    )

    $targets = @(Get-AlfredAgentProcesses)
    if ($targets.Count -eq 0) {
        if (-not $Quiet) { Write-AgentCloseMsg info 'No Cursor, Claude, or ChatGPT processes running.' }
        return @{
            Closed       = @()
            StillRunning = @()
        }
    }

    $names = ($targets | ForEach-Object { $_.ProcessName } | Sort-Object -Unique) -join ', '
    if (-not $Quiet) { Write-AgentCloseMsg step "Closing agent apps: $names" }

    foreach ($proc in $targets) {
        try {
            if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
                $null = $proc.CloseMainWindow()
            }
        } catch { }
    }

    if ($GraceSec -gt 0) { Start-Sleep -Seconds $GraceSec }

    foreach ($proc in @(Get-AlfredAgentProcesses)) {
        try {
            & taskkill /PID $proc.Id /T /F 2>&1 | Out-Null
        } catch {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop } catch { }
        }
    }

    $deadline = (Get-Date).AddSeconds($WaitSec)
    while ((Get-Date) -lt $deadline) {
        if (@(Get-AlfredAgentProcesses).Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }

    $closed = @($targets | ForEach-Object { $_.ProcessName } | Sort-Object -Unique)
    $stillRunning = @(Get-AlfredAgentProcesses | ForEach-Object { $_.ProcessName } | Sort-Object -Unique)

    if ($stillRunning.Count -gt 0) {
        Write-AgentCloseMsg warn ("Some agent apps may still be running: {0}. Close them manually, then re-run provision." -f ($stillRunning -join ', '))
    } elseif (-not $Quiet) {
        Write-AgentCloseMsg ok 'Cursor, Claude, and ChatGPT closed — ready to provision.'
    }

    return @{
        Closed       = $closed
        StillRunning = $stillRunning
    }
}
