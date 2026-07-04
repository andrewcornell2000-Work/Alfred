#Requires -Version 5.1
<#
.SYNOPSIS
    Silent or interactive check for Alfred pack updates on GitHub.
.OUTPUTS
    Exit 0  — up to date or check skipped
    Exit 11 — updates available (writes logs/update-available.json)
    Exit 1  — fetch failed
#>
param(
    [string]$Root = "",
    [switch]$CheckOnly,
    [switch]$Notify,
    [switch]$Quiet
)

if (-not $Root) {
    $Root = if ($env:ALFRED_HOME) { $env:ALFRED_HOME } else { Join-Path $env:USERPROFILE "Alfred" }
}

function Write-Log([string]$Msg, [string]$Color = "White") {
    if (-not $Quiet) { Write-Host $Msg -ForegroundColor $Color }
}

if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Log "Alfred repo not found at $Root" "DarkGray"
    exit 0
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { exit 0 }

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$StateFile = Join-Path $LogDir "update-available.json"

Write-Log "Checking Alfred for updates..." "Cyan"

git -C $Root fetch origin main 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "Could not reach GitHub." "DarkGray"
    exit 0
}

$localHead  = (git -C $Root rev-parse HEAD 2>&1).Trim()
$remoteHead = (git -C $Root rev-parse origin/main 2>&1).Trim()

if ($localHead -eq $remoteHead) {
    if (Test-Path $StateFile) { Remove-Item $StateFile -Force -ErrorAction SilentlyContinue }
    Write-Log "Alfred is up to date." "Green"
    exit 0
}

$behind = (git -C $Root rev-list --count "HEAD..origin/main" 2>&1).Trim()
$commits = @(git -C $Root log --oneline "HEAD..origin/main" 2>&1)

$state = @{
    available     = $true
    checked_at    = (Get-Date).ToUniversalTime().ToString("o")
    local_head    = $localHead
    remote_head   = $remoteHead
    commits_behind = [int]$behind
    commits       = $commits | Select-Object -First 8
    alfred_root   = $Root
}
$state | ConvertTo-Json -Depth 4 | Set-Content $StateFile -Encoding UTF8

Write-Log "Update available: $behind commit(s) on origin/main." "Yellow"

if ($Notify) {
    $notifyScript = Join-Path $Root "scripts\Show-AlfredUpdateNotification.ps1"
    if (Test-Path $notifyScript) {
        & $notifyScript -Root $Root
    }
}

if ($CheckOnly) { exit 11 }
exit 11
