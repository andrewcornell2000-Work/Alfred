#Requires -Version 5.1
<#
.SYNOPSIS
    Provision MCP servers, skills, and (optionally) rules into Cursor AND Claude Code,
    machine-wide, from Alfred's single source of truth.
.DESCRIPTION
    Reads cursor/mcp.json (a template with ${env:VAR} placeholders) and:
      * deep-merges the servers into ~/.cursor/mcp.json (Cursor, global, all projects),
      * registers them with Claude Code at user scope (claude mcp add --scope user).
    Secrets are resolved from Alfred's .env (or machine environment). A server whose
    REQUIRED secret or command is missing is skipped with a clear message.

    Skills: every skills/*.md is wrapped as alfred-<name>/SKILL.md and synced into
    ~/.cursor/skills and ~/.claude/skills (global in both tools).

    Rules: pass -ProjectPath <repo> to seed cursor/rules/*.mdc into <repo>/.cursor/rules
    and a shared AGENTS.md (read by both tools). Cursor rules are per-project by design.

    Idempotent and safe to re-run. Never commits secrets.
.PARAMETER ProjectPath
    Optional project to seed Cursor rules + AGENTS.md into.
.PARAMETER SkipCursor
    Skip Cursor (~/.cursor) provisioning.
.PARAMETER SkipClaude
    Skip Claude Code (claude mcp / ~/.claude) provisioning.
#>
[CmdletBinding()]
param(
    [string]$ProjectPath,
    [switch]$SkipCursor,
    [switch]$SkipClaude
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

# ── output helpers ────────────────────────────────────────────────────────────
function Write-Step([string]$m) { Write-Host ""; Write-Host "> $m" -ForegroundColor Cyan }
function Write-OK([string]$m)   { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Write-Warn2([string]$m){ Write-Host "  [WARN]  $m" -ForegroundColor Yellow }
function Write-Skip([string]$m) { Write-Host "  [SKIP]  $m" -ForegroundColor DarkGray }
function Write-Info([string]$m) { Write-Host "          $m" -ForegroundColor DarkYellow }

function Write-TextNoBom([string]$path, [string]$text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $text, $enc)
}

# ── .env loader (KEY=VALUE; comments/blank ignored) ───────────────────────────
function Read-DotEnv([string]$path) {
    $map = @{}
    if (Test-Path $path) {
        foreach ($line in Get-Content $path) {
            $t = $line.Trim()
            if ($t -eq '' -or $t.StartsWith('#')) { continue }
            $idx = $t.IndexOf('=')
            if ($idx -lt 1) { continue }
            $k = $t.Substring(0, $idx).Trim()
            $v = $t.Substring($idx + 1).Trim()
            if ($v.Length -ge 2 -and (($v[0] -eq '"' -and $v[-1] -eq '"') -or ($v[0] -eq "'" -and $v[-1] -eq "'"))) {
                $v = $v.Substring(1, $v.Length - 2)
            }
            $map[$k] = $v
        }
    }
    return $map
}

function Resolve-Secret([string]$name, [hashtable]$envMap) {
    if ($envMap.ContainsKey($name) -and "$($envMap[$name])" -ne '') { return $envMap[$name] }
    foreach ($scope in @("Process", "User", "Machine")) {
        $val = [System.Environment]::GetEnvironmentVariable($name, $scope)
        if ($val) { return $val }
    }
    return $null
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Alfred -> Cursor + Claude Code provisioning" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# If Cursor isn't installed, skip all Cursor steps (Claude Code is still configured).
# Prevents creating stray ~/.cursor folders on machines without Cursor.
function Test-CursorInstalled {
    if (Get-Command cursor -ErrorAction SilentlyContinue) { return $true }
    if (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\cursor\Cursor.exe")) { return $true }
    if (Test-Path (Join-Path $HOME ".cursor")) { return $true }
    return $false
}
if (-not $SkipCursor -and -not (Test-CursorInstalled)) {
    Write-Info "Cursor not detected -- skipping Cursor provisioning. Claude Code will still be set up."
    $SkipCursor = $true
}

$EnvMap = Read-DotEnv (Join-Path $Root ".env")

# ── resolve machine-specific path tokens ──────────────────────────────────────
# The template uses ${repoRoot}, ${userProfile}, ${financeDir}, ${dataDir},
# ${memoryDir}, ${powerBiMcp} so no path is tied to one person's profile.
$repoRoot    = $Root
$userProfile = $env:USERPROFILE
$dataDir     = Join-Path $repoRoot "data"
$memoryDir   = Join-Path $repoRoot "memory"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

# Finance folder: .env override -> OneDrive-for-Business subfolder -> OneDrive root -> profile
$financeDir = $EnvMap["ALFRED_FINANCE_DIR"]
if (-not $financeDir -or -not (Test-Path $financeDir)) {
    $odc = $env:OneDriveCommercial; if (-not $odc) { $odc = $env:OneDrive }
    if ($odc -and (Test-Path (Join-Path $odc "MCL Finance - General"))) {
        $financeDir = Join-Path $odc "MCL Finance - General"
    } elseif ($odc -and (Test-Path $odc)) {
        $financeDir = $odc
    } else {
        $financeDir = $userProfile
    }
}

# Power BI Modeling MCP — newest installed VS Code extension build (version-specific)
$powerBiMcp = ""
$pbiExtRoot = Join-Path $userProfile ".vscode\extensions"
if (Test-Path $pbiExtRoot) {
    $pbiHit = Get-ChildItem $pbiExtRoot -Directory -Filter "analysis-services.powerbi-modeling-mcp-*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName "server\powerbi-modeling-mcp.exe" } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($pbiHit) { $powerBiMcp = $pbiHit }
}

$PathTokens = @{
    '${repoRoot}'    = $repoRoot
    '${userProfile}' = $userProfile
    '${financeDir}'  = $financeDir
    '${dataDir}'     = $dataDir
    '${memoryDir}'   = $memoryDir
    '${powerBiMcp}'  = $powerBiMcp
}

function Expand-Tokens([string]$value) {
    if ($null -eq $value) { return $value }
    foreach ($tok in $PathTokens.Keys) { $value = $value.Replace($tok, [string]$PathTokens[$tok]) }
    return $value
}

# Does this command refer to an absolute file path that is missing on this machine?
function Test-CommandMissing([string]$command) {
    if ([string]::IsNullOrWhiteSpace($command)) { return $true }   # unresolved token
    if ($command -match '^[A-Za-z]:\\') { return -not (Test-Path $command) }
    return $false   # bare commands (npx, uvx, python) resolve via PATH at runtime
}

# ── resolve MCP servers from the template ─────────────────────────────────────
$McpTemplatePath = Join-Path $Root "cursor\mcp.json"
$managed         = [ordered]@{}   # name -> ordered hashtable { command, args, env }
$managedEnvLists = @{}            # name -> array of "KEY=VALUE" (for claude --env)
$skippedServers  = @()

if (-not (Test-Path $McpTemplatePath)) {
    Write-Warn2 "cursor/mcp.json not found -- no MCP servers to provision."
} else {
    $tpl = Get-Content $McpTemplatePath -Raw | ConvertFrom-Json
    if ($tpl.mcpServers) {
        foreach ($prop in $tpl.mcpServers.PSObject.Properties) {
            $name = $prop.Name
            $def  = $prop.Value
            $defKeys = @($def.PSObject.Properties.Name)

            $requires = @(); if ($defKeys -contains '_requires') { $requires = @($def._requires) }
            $requiresCmd = $null; if ($defKeys -contains '_requiresCommand') { $requiresCmd = $def._requiresCommand }
            $aliases = @{}
            if ($defKeys -contains '_aliases') {
                foreach ($ap in $def._aliases.PSObject.Properties) { $aliases[$ap.Name] = @($ap.Value) }
            }

            if ($requiresCmd -and -not (Get-Command $requiresCmd -ErrorAction SilentlyContinue)) {
                $skippedServers += "$name (needs '$requiresCmd' on PATH)"
                continue
            }

            $resolvedEnv = [ordered]@{}
            $envList = @()
            $missingRequired = $null
            if (($defKeys -contains 'env') -and $def.env) {
                foreach ($ep in $def.env.PSObject.Properties) {
                    $val = [string]$ep.Value
                    $mch = [regex]::Match($val, '^\$\{env:(.+)\}$')
                    if ($mch.Success) {
                        $varName = $mch.Groups[1].Value
                        $lookups = @($varName); if ($aliases.ContainsKey($varName)) { $lookups += $aliases[$varName] }
                        $secret = $null
                        foreach ($ln in $lookups) { $secret = Resolve-Secret $ln $EnvMap; if ($secret) { break } }
                        if ($secret) {
                            $resolvedEnv[$ep.Name] = $secret
                            $envList += "$($ep.Name)=$secret"
                        } elseif ($requires -contains $varName) {
                            $missingRequired = $varName
                        }
                        # optional + missing -> silently drop this env key
                    } else {
                        $val = Expand-Tokens $val
                        $resolvedEnv[$ep.Name] = $val
                        $envList += "$($ep.Name)=$val"
                    }
                }
            }
            if ($missingRequired) {
                $skippedServers += "$name (missing required secret '$missingRequired' -- add it to Alfred .env)"
                continue
            }

            $expandedCommand = Expand-Tokens ([string]$def.command)
            $expandedArgs    = @($def.args | ForEach-Object { Expand-Tokens ([string]$_) })

            # Skip servers whose absolute command path isn't present on THIS machine
            # (e.g. Power BI extension not installed, venv not built yet).
            if (Test-CommandMissing $expandedCommand) {
                $skippedServers += "$name (command not found on this machine: $expandedCommand)"
                continue
            }

            $serverObj = [ordered]@{ command = $expandedCommand; args = $expandedArgs }
            if ($resolvedEnv.Count -gt 0) { $serverObj.env = $resolvedEnv }
            $managed[$name] = $serverObj
            $managedEnvLists[$name] = $envList
        }
    }
}

if ($managed.Count -gt 0) {
    Write-Step "Resolved $($managed.Count) MCP server(s): $($managed.Keys -join ', ')"
}

# ── Cursor: ~/.cursor/mcp.json (deep merge, preserve existing servers) ────────
if (-not $SkipCursor -and $managed.Count -gt 0) {
    Write-Step "Cursor: ~/.cursor/mcp.json"
    $cursorDir = Join-Path $HOME ".cursor"
    if (-not (Test-Path $cursorDir)) { New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null }
    $cursorMcpPath = Join-Path $cursorDir "mcp.json"

    $final = [ordered]@{}
    if (Test-Path $cursorMcpPath) {
        try {
            $existing = Get-Content $cursorMcpPath -Raw | ConvertFrom-Json
            if ($existing.mcpServers) {
                foreach ($p in $existing.mcpServers.PSObject.Properties) { $final[$p.Name] = $p.Value }
            }
        } catch {
            Write-Warn2 "Existing mcp.json was unreadable -- backing it up to mcp.json.bak and recreating."
            Copy-Item $cursorMcpPath "$cursorMcpPath.bak" -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($k in $managed.Keys) { $final[$k] = $managed[$k] }   # ours win

    $json = [ordered]@{ mcpServers = $final } | ConvertTo-Json -Depth 12
    Write-TextNoBom $cursorMcpPath $json
    Write-OK "Wrote $($managed.Count) managed server(s); $($final.Count) total in $cursorMcpPath"
    Write-Info "This file is machine-local and may contain tokens -- it is never committed."
}

# ── Claude Code: claude mcp add --scope user (idempotent) ─────────────────────
if (-not $SkipClaude -and $managed.Count -gt 0) {
    Write-Step "Claude Code: registering servers at user scope"
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Skip "claude CLI not found -- skipping Claude Code MCP registration."
    } else {
        foreach ($name in $managed.Keys) {
            $srv = $managed[$name]
            try { & claude mcp remove $name --scope user 2>$null | Out-Null } catch {}
            $argList = @('mcp', 'add', $name, '--scope', 'user')
            foreach ($e in $managedEnvLists[$name]) { $argList += @('--env', $e) }
            $argList += '--'
            $argList += $srv.command
            $argList += $srv.args
            try {
                & claude @argList 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { Write-OK "Registered '$name' (Claude Code, user scope)." }
                else { Write-Warn2 "claude mcp add '$name' returned exit $LASTEXITCODE." }
            } catch {
                Write-Warn2 "claude mcp add '$name' failed: $_"
            }
        }
    }
}

# ── Skills: sync skills/*.md into both tools as alfred-<name>/SKILL.md ─────────
function Sync-Skills([string]$srcDir, [string[]]$destRoots) {
    if (-not (Test-Path $srcDir)) { Write-Skip "No skills/ directory at $srcDir"; return }
    $mdFiles = @(Get-ChildItem -Path $srcDir -Filter *.md -File)
    if ($mdFiles.Count -eq 0) { Write-Skip "No skill files in $srcDir"; return }
    foreach ($root in $destRoots) {
        if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }
    }
    foreach ($f in $mdFiles) {
        $base = ($f.BaseName.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')
        if ($base -like 'alfred-*') { $slug = $base } else { $slug = "alfred-$base" }
        $content = Get-Content $f.FullName -Raw

        if ($content -match '^\s*---') {
            $skillBody = $content                      # already has frontmatter
        } else {
            $lines = $content -split "`n"
            $titleLine = $lines | Where-Object { $_ -match '^\s*#\s+\S' } | Select-Object -First 1
            if ($titleLine) { $title = ($titleLine -replace '^\s*#\s+', '').Trim() } else { $title = $f.BaseName }
            $descLine = $lines | Where-Object { $_.Trim() -ne '' -and $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*---' } | Select-Object -First 1
            if (-not $descLine) { $descLine = "Alfred skill: $title" }
            $descLine = ($descLine.Trim() -replace '"', '')
            if ($descLine.Length -gt 200) { $descLine = $descLine.Substring(0, 200) }
            $skillBody = "---`nname: $slug`ndescription: $descLine`n---`n`n" + $content
        }

        foreach ($root in $destRoots) {
            $dir = Join-Path $root $slug
            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            Write-TextNoBom (Join-Path $dir "SKILL.md") $skillBody
        }
    }
    Write-OK "Synced $($mdFiles.Count) skill(s) -> $($destRoots -join ', ')"
}

Write-Step "Skills: syncing Alfred skills into Cursor + Claude Code"
$skillDests = @()
if (-not $SkipCursor) { $skillDests += (Join-Path $HOME ".cursor\skills") }
if (-not $SkipClaude) { $skillDests += (Join-Path $HOME ".claude\skills") }
if ($skillDests.Count -gt 0) { Sync-Skills (Join-Path $Root "skills") $skillDests }

# ── Rules: per-project seeding (opt-in via -ProjectPath) ──────────────────────
if ($ProjectPath) {
    Write-Step "Rules: seeding into $ProjectPath"
    if (-not (Test-Path $ProjectPath)) {
        Write-Warn2 "ProjectPath '$ProjectPath' does not exist -- skipping rules."
    } else {
        $rulesSrc = Join-Path $Root "cursor\rules"
        if (Test-Path $rulesSrc) {
            $rulesDest = Join-Path $ProjectPath ".cursor\rules"
            if (-not (Test-Path $rulesDest)) { New-Item -ItemType Directory -Path $rulesDest -Force | Out-Null }
            Copy-Item (Join-Path $rulesSrc '*.mdc') $rulesDest -Force
            Write-OK "Copied Cursor rules -> $rulesDest"
        }
        $agentsSrc  = Join-Path $Root "cursor\AGENTS.shared.md"
        $agentsDest = Join-Path $ProjectPath "AGENTS.md"
        if (Test-Path $agentsDest) {
            Write-Skip "AGENTS.md already exists in project -- left untouched."
        } elseif (Test-Path $agentsSrc) {
            Copy-Item $agentsSrc $agentsDest
            Write-OK "Created AGENTS.md (shared rules for Cursor + Claude Code)."
        }
    }
} else {
    Write-Info "Rules are per-project. Re-run with -ProjectPath <repo> to seed Cursor rules + AGENTS.md."
}

# ── summary ───────────────────────────────────────────────────────────────────
if ($skippedServers.Count -gt 0) {
    Write-Step "Skipped servers (add the secret/prereq to Alfred .env, then re-run):"
    foreach ($s in $skippedServers) { Write-Info "- $s" }
}

Write-Host ""
Write-Host "Provisioning complete. Restart Cursor / Claude Code to pick up new MCP servers." -ForegroundColor Green
Write-Host ""
