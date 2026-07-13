<#
.SYNOPSIS
    Tear down Alfred's MCP registrations on THIS machine, leaving a clean slate.

.DESCRIPTION
    Removes every Alfred-managed MCP server (the names defined in cursor/mcp.json,
    plus any _retiredServers) from all four client surfaces:
        - Cursor          ~/.cursor/mcp.json
        - Claude Code     claude mcp remove --scope user
        - Claude Desktop  %APPDATA%\Claude\claude_desktop_config.json
        - Codex           ~/.codex/config.toml   (codex mcp remove, or block strip)

    This is the reset half of "reset-and-reinstall". Pair with Provision-Cursor.ps1
    to reinstall from the canonical template (or use -AndReinstall to chain both).

    By default it PROMPTS before changing anything. Config files are backed up to
    "<file>.reset.bak" before edits. Use -KillProcesses to also terminate any
    running MCP server process trees (they respawn on next client launch).

.PARAMETER Yes
    Skip the confirmation prompt (for automation / installers).
.PARAMETER KillProcesses
    Also terminate running MCP server process trees to reclaim RAM immediately.
.PARAMETER AndReinstall
    After reset, run Provision-Cursor.ps1 to reinstall from the canonical template.
.PARAMETER IncludeOptional
    Passed through to Provision-Cursor.ps1 when -AndReinstall is set.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Alfred-Reset.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Alfred-Reset.ps1 -KillProcesses -AndReinstall -Yes
#>
[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$KillProcesses,
    [switch]$AndReinstall,
    [string]$IncludeOptional = ''
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

function Write-Step([string]$m) { Write-Host ""; Write-Host "> $m" -ForegroundColor Cyan }
function Write-OK([string]$m)   { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Write-Info([string]$m) { Write-Host "          $m" -ForegroundColor DarkYellow }
function Write-Warn2([string]$m){ Write-Host "  [WARN]  $m" -ForegroundColor Yellow }

# ── 1. Determine the set of Alfred-managed server names ────────────────────────
$tplPath = Join-Path $Root "cursor\mcp.json"
if (-not (Test-Path $tplPath)) { Write-Warn2 "cursor/mcp.json not found -- cannot determine managed servers."; exit 1 }
$tpl = Get-Content $tplPath -Raw | ConvertFrom-Json
$managedNames = @($tpl.mcpServers.PSObject.Properties.Name)
if ($tpl.PSObject.Properties.Name -contains '_retiredServers') { $managedNames += @($tpl._retiredServers) }
$managedNames = @($managedNames | Select-Object -Unique)

Write-Step "Alfred-Reset — this machine"
Write-Info "Managed MCP servers to remove from all clients:"
Write-Info ("  " + ($managedNames -join ', '))
Write-Info "Targets: Cursor, Claude Code (user), Claude Desktop, Codex."
if ($KillProcesses) { Write-Info "Will also terminate running MCP server process trees." }
if ($AndReinstall)  { Write-Info "Will re-run Provision-Cursor.ps1 after reset." }

if (-not $Yes) {
    $ans = Read-Host "`nProceed with reset? Type 'reset' to continue"
    if ($ans -ne 'reset') { Write-Warn2 "Aborted -- nothing changed."; exit 0 }
}

# ── 2. Strip managed servers from a JSON config (mcpServers map) ────────────────
function Reset-JsonConfig([string]$path, [string]$label) {
    if (-not (Test-Path $path)) { Write-Info "$label : no config file (nothing to do)"; return }
    try { $j = Get-Content $path -Raw | ConvertFrom-Json } catch { Write-Warn2 "$label : unreadable, skipped"; return }
    if (-not $j.mcpServers) { Write-Info "$label : no mcpServers key"; return }
    Copy-Item $path "$path.reset.bak" -Force -ErrorAction SilentlyContinue
    $keep = [ordered]@{}
    $removed = @()
    foreach ($p in $j.mcpServers.PSObject.Properties) {
        if ($managedNames -contains $p.Name) { $removed += $p.Name } else { $keep[$p.Name] = $p.Value }
    }
    $out = [ordered]@{ mcpServers = $keep }
    # preserve any other top-level keys the app owns (Desktop stores preferences here)
    foreach ($p in $j.PSObject.Properties) { if ($p.Name -ne 'mcpServers') { $out[$p.Name] = $p.Value } }
    ($out | ConvertTo-Json -Depth 20) | Set-Content -Path $path -Encoding UTF8
    Write-OK "$label : removed $($removed.Count) server(s); $($keep.Count) non-Alfred entr(y/ies) kept"
}

Write-Step "Cursor"
Reset-JsonConfig (Join-Path $HOME ".cursor\mcp.json") "cursor (~/.cursor/mcp.json)"

Write-Step "Claude Desktop"
Reset-JsonConfig (Join-Path $env:APPDATA "Claude\claude_desktop_config.json") "claude-desktop"

Write-Step "Claude Code (user scope)"
if (Get-Command claude -ErrorAction SilentlyContinue) {
    foreach ($n in $managedNames) { try { & claude mcp remove $n --scope user 2>$null | Out-Null } catch {} }
    Write-OK "Ran 'claude mcp remove' for all managed names"
} else { Write-Info "claude CLI not on PATH -- skipped" }

Write-Step "Codex"
$codexToml = Join-Path $HOME ".codex\config.toml"
if (Get-Command codex -ErrorAction SilentlyContinue) {
    foreach ($n in $managedNames) { try { & codex mcp remove $n 2>$null | Out-Null } catch {} }
    Write-OK "Ran 'codex mcp remove' for all managed names"
} elseif (Test-Path $codexToml) {
    Write-Info "codex CLI absent; leaving ~/.codex/config.toml untouched (edit manually if needed)"
} else { Write-Info "no Codex config" }

# ── 3. Optionally kill running MCP server process trees ─────────────────────────
if ($KillProcesses) {
    Write-Step "Terminating running MCP server process trees"
    $tokens = @('excellm','mcp-excel','markitdown','mcp-server-fetch','mcp-server-duckdb',
                'outlook-calendar','@magicuidesign','search.parallel.ai','context7-mcp','@upstash/context7',
                'server-filesystem','server-github','github-mcp-server','@playwright/mcp','playwright-mcp',
                'ms-365-mcp-server','powerbi-modeling-mcp','fal-ai-mcp','firecrawl-mcp')
    $all = Get-CimInstance Win32_Process
    $byPid = @{}; foreach ($p in $all) { $byPid[[int]$p.ProcessId] = $p }
    $chain = 'cmd.exe','node.exe','conhost.exe','uvx.exe','uv.exe','npx.exe'
    $leaves = $all | Where-Object { $cl = $_.CommandLine; $cl -and ($tokens | Where-Object { $cl -like "*$_*" }) }
    $tops = @{}
    foreach ($lf in $leaves) {
        $cur = $lf
        while ($true) {
            $par = $byPid[[int]$cur.ParentProcessId]
            if (-not $par) { break }
            if ($par.Name -in @('claude.exe','cursor.exe','explorer.exe','services.exe')) { break }
            if ($chain -notcontains $par.Name) { break }
            $cur = $par
        }
        $tops[[int]$cur.ProcessId] = $true
    }
    foreach ($k in $tops.Keys) { cmd /c "taskkill /PID $k /T /F" 2>&1 | Out-Null }
    Write-OK "Terminated $($tops.Count) process tree(s) (they respawn lean on next client launch)"
}

Write-OK "Reset complete."
Write-Info "Backups: <config>.reset.bak next to each edited file."

# ── 4. Optionally reinstall from the canonical template ────────────────────────
if ($AndReinstall) {
    Write-Step "Reinstalling from canonical template (Provision-Cursor.ps1)"
    $prov = Join-Path $Root "Provision-Cursor.ps1"
    if (Test-Path $prov) {
        $provArgs = @{}
        if ($IncludeOptional) { $provArgs['IncludeOptional'] = $IncludeOptional }
        & $prov @provArgs
    } else { Write-Warn2 "Provision-Cursor.ps1 not found -- reinstall skipped." }
}
