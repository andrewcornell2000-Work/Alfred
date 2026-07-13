<#
.SYNOPSIS
    Cross-machine sync of Alfred subagents + skills via the GitHub repo.

.DESCRIPTION
    You use Claude Code + Cursor on different machines, and locally-created
    subagents / skill edits don't travel between them. This closes that gap by
    treating the Alfred repo as the canonical store:

      1. git pull --rebase          (get changes made on your other machines)
      2. IMPORT local subagents      (~/.claude/agents + ~/.cursor/agents) into
                                      the repo's agents/ folder, preserving each
                                      agent's bucket: frontmatter
      3. APPLY repo -> machine       (Provision-Cursor.ps1 -SyncOnly: syncs skills
                                      + subagents for the selected buckets; no MCP
                                      churn, no app-closing)
      4. git commit + push           (only agents/ changes; retries once on a
                                      non-fast-forward from a concurrent push)

    Skills are repo-canonical: edit them in Alfred/skills and they propagate on
    the next sync. Subagents sync both ways (create on any machine -> captured).

.PARAMETER InstallSchedule
    Register a Windows Scheduled Task that runs this every 3 hours and at logon.
.PARAMETER RemoveSchedule
    Remove that Scheduled Task.
.PARAMETER Quiet
    Minimal output (for scheduled runs).
.PARAMETER NoPush
    Do everything except commit/push (dry sanity check).
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Alfred-Sync.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Alfred-Sync.ps1 -InstallSchedule
#>
[CmdletBinding()]
param(
    [switch]$InstallSchedule,
    [switch]$RemoveSchedule,
    [switch]$Quiet,
    [switch]$NoPush
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$TaskName = "AlfredSync"
function Say([string]$m, [string]$c = 'Gray') { if (-not $Quiet) { Write-Host $m -ForegroundColor $c } }

# ── schedule management (all no-admin) ─────────────────────────────────────────
$startupLnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'AlfredSync.lnk'
if ($RemoveSchedule) {
    schtasks /Delete /TN $TaskName /F 2>&1 | Out-Null
    if (Test-Path $startupLnk) { Remove-Item $startupLnk -Force }
    Say "Removed scheduled task '$TaskName' and the logon shortcut." 'Yellow'; return
}
if ($InstallSchedule) {
    $ps   = (Get-Command powershell.exe).Source
    $self = Join-Path $Root "Alfred-Sync.ps1"
    $args = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$self`" -Quiet"
    # (1) every-3-hours Scheduled Task — runs in the user context (git creds resolve), no admin.
    schtasks /Create /TN $TaskName /TR "`"$ps`" $args" /SC HOURLY /MO 3 /F 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Say "Installed scheduled task '$TaskName' (every 3 hours)." 'Green' }
    else { Say "Could not create the 3-hour task (non-fatal); the logon shortcut still covers sync." 'Yellow' }
    # (2) at-logon Startup shortcut — ONLOGON tasks need admin, a Startup .lnk does not.
    try {
        $ws = New-Object -ComObject WScript.Shell
        $lnk = $ws.CreateShortcut($startupLnk)
        $lnk.TargetPath = $ps
        $lnk.Arguments  = $args
        $lnk.WorkingDirectory = $Root
        $lnk.WindowStyle = 7   # minimized
        $lnk.Description = "Alfred cross-machine subagent/skill sync"
        $lnk.Save()
        Say "Installed logon shortcut: $startupLnk" 'Green'
    } catch { Say "Could not create logon shortcut: $_" 'Yellow' }
    Say "Test now:  schtasks /Run /TN $TaskName" 'DarkGray'
    return
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Say "git not on PATH -- cannot sync." 'Red'; exit 1 }
if (-not (Test-Path (Join-Path $Root ".git"))) { Say "$Root is not a git repo." 'Red'; exit 1 }

# ── 1. pull (autostash so local uncommitted work isn't lost) ───────────────────
Say "> Pull origin (rebase)" 'Cyan'
git -C $Root pull --rebase --autostash 2>&1 | ForEach-Object { Say "  $_" 'DarkGray' }

# ── 2. import local subagents into the repo, preserving bucket: frontmatter ─────
$repoAgents = Join-Path $Root "agents"
if (-not (Test-Path $repoAgents)) { New-Item -ItemType Directory -Path $repoAgents -Force | Out-Null }

function Get-BucketLine([string[]]$lines) {
    return ($lines | Where-Object { $_ -match '^\s*bucket:\s*\S' } | Select-Object -First 1)
}
function Remove-BucketLine([string]$text) {
    return (($text -split "`r?`n") | Where-Object { $_ -notmatch '^\s*bucket:\s*\S' }) -join "`n"
}

$localAgentDirs = @((Join-Path $HOME ".claude\agents"), (Join-Path $HOME ".cursor\agents"))
$seen = @{}; $imported = 0
foreach ($dir in $localAgentDirs) {
    if (-not (Test-Path $dir)) { continue }
    foreach ($f in (Get-ChildItem $dir -Filter *.md -File -ErrorAction SilentlyContinue)) {
        if ($seen.ContainsKey($f.Name)) { continue }   # first machine dir wins (claude before cursor)
        $seen[$f.Name] = $true
        $localRaw  = Get-Content $f.FullName -Raw
        $repoFile  = Join-Path $repoAgents $f.Name
        if (Test-Path $repoFile) {
            $repoRaw = Get-Content $repoFile -Raw
            if ((Remove-BucketLine $localRaw).TrimEnd() -eq (Remove-BucketLine $repoRaw).TrimEnd()) { continue }  # same
            # local changed: keep repo's bucket if local lacks one
            $repoBucket = Get-BucketLine ($repoRaw -split "`r?`n")
            $localBucket = Get-BucketLine ($localRaw -split "`r?`n")
            $outRaw = $localRaw
            if ($repoBucket -and -not $localBucket) {
                $outRaw = [regex]::Replace($localRaw, '(?m)^(name:\s*.+)$', "`$1`n$repoBucket", 1)
            }
            Set-Content -Path $repoFile -Value $outRaw -Encoding UTF8 -NoNewline
            Say "  updated agents/$($f.Name)" 'Green'; $imported++
        } else {
            Copy-Item $f.FullName $repoFile -Force
            Say "  captured NEW agents/$($f.Name)" 'Green'; $imported++
        }
    }
}
if ($imported -eq 0) { Say "  no new/changed local subagents to capture" 'DarkGray' }

# ── 3. apply repo -> this machine (skills + subagents for selected buckets) ─────
Say "> Apply repo -> machine (skills + subagents)" 'Cyan'
$prov = Join-Path $Root "Provision-Cursor.ps1"
if (Test-Path $prov) {
    & $prov -SyncOnly 2>&1 | ForEach-Object { Say "  $_" 'DarkGray' }
} else { Say "  Provision-Cursor.ps1 missing -- skills/agents not applied." 'Yellow' }

# ── 4. commit + push (agents only) ─────────────────────────────────────────────
if ($NoPush) { Say "> -NoPush set; skipping commit/push." 'Yellow'; return }
git -C $Root add -- agents 2>&1 | Out-Null
$staged = (git -C $Root diff --cached --name-only -- agents) 2>$null
if ($staged) {
    $host_ = $env:COMPUTERNAME
    git -C $Root commit -m "chore(sync): capture subagents from $host_" 2>&1 | ForEach-Object { Say "  $_" 'DarkGray' }
    $push = git -C $Root push origin HEAD 2>&1
    if ($LASTEXITCODE -ne 0) {
        Say "  push rejected; pull --rebase and retry once" 'Yellow'
        git -C $Root pull --rebase --autostash 2>&1 | Out-Null
        git -C $Root push origin HEAD 2>&1 | ForEach-Object { Say "  $_" 'DarkGray' }
    } else { $push | ForEach-Object { Say "  $_" 'DarkGray' } }
    Say "Sync complete: pushed subagent changes." 'Green'
} else {
    Say "Sync complete: nothing to push (machine already in sync)." 'Green'
}
