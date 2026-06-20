#Requires -Version 5.1
<#
.SYNOPSIS
    Provision MCP servers, skills, and (optionally) rules into Cursor, Claude Code,
    AND Codex, machine-wide, from Alfred's single source of truth.
.DESCRIPTION
    Reads cursor/mcp.json (a template with ${env:VAR} placeholders) and:
      * deep-merges the servers into ~/.cursor/mcp.json (Cursor, global, all projects),
      * registers them with Claude Code at user scope (claude mcp add --scope user),
      * merges them into Claude Desktop (%APPDATA%\Claude\claude_desktop_config.json).
    Secrets are resolved from Alfred's .env (or machine environment). A server whose
    REQUIRED secret or command is missing is skipped with a clear message.
    Tokens land in machine-local config files only — never committed to git.

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
.PARAMETER SkipClaudeDesktop
    Skip Claude Desktop app (%APPDATA%\Claude\claude_desktop_config.json).
.PARAMETER SkipCodex
    Skip Codex (codex mcp add) provisioning.
.PARAMETER SkipLeanCtx
    Skip lean-ctx onboard and Cursor lean-ctx repair.
.PARAMETER SkipThirdPartySkills
    Skip npx install of third-party agent skills (e.g. Leonxlnx/taste-skill).
#>
[CmdletBinding()]
param(
    [string]$ProjectPath,
    [switch]$SkipCursor,
    [switch]$SkipClaude,
    [switch]$SkipClaudeDesktop,
    [switch]$SkipCodex,
    [switch]$SkipLeanCtx,
    [switch]$SkipThirdPartySkills
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

$script:ProvisionErrors = @()

function Get-LeanCtxBinaryPath {
    $bin = (Get-Command lean-ctx.cmd -ErrorAction SilentlyContinue).Source
    if (-not $bin) { $bin = (Get-Command lean-ctx -ErrorAction SilentlyContinue).Source }
    if ($bin) { return ($bin -replace '\\', '/') }
    return $null
}

function Invoke-McpCliAdd([string]$toolName, [string]$serverName, [string[]]$argList) {
    $stderr = & $toolName @argList 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Registered '$serverName' ($toolName)."
        return $true
    }
    $detail = ($stderr | Out-String).Trim()
    if ($detail.Length -gt 300) { $detail = $detail.Substring(0, 300) + "..." }
    $msg = "$toolName mcp add '$serverName' failed (exit $LASTEXITCODE): $detail"
    $script:ProvisionErrors += $msg
    Write-Warn2 $msg
    return $false
}

function Repair-LeanCtxMcpFile([string]$mcpPath, [string]$label) {
    if (-not (Test-Path $mcpPath)) { return }
    $leanCtxBin = Get-LeanCtxBinaryPath
    if (-not $leanCtxBin) {
        Write-Warn2 "lean-ctx not on PATH -- skipping $label MCP repair"
        return
    }
    try {
        $mcp = Get-Content $mcpPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $lc = $mcp.mcpServers.'lean-ctx'
        if (-not $lc) { return }
        if ($lc.PSObject.Properties.Name -contains 'autoApprove') {
            $lc.PSObject.Properties.Remove('autoApprove')
        }
        $lc.command = $leanCtxBin
        if ($lc.PSObject.Properties.Name -contains 'type') {
            $lc.PSObject.Properties.Remove('type')
        }
        $json = $mcp | ConvertTo-Json -Depth 30
        Write-TextNoBom $mcpPath $json
        Write-OK "$label lean-ctx: removed autoApprove, command -> $leanCtxBin"
    } catch {
        Write-Warn2 "Could not repair lean-ctx in ${label} mcp config: $_"
    }
}

function Sync-LeanCtxToClaudeDesktop {
    if ($SkipClaudeDesktop) { return }
    $desktopPath = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
    if (-not (Test-Path $desktopPath)) { return }
    $leanCtxBin = Get-LeanCtxBinaryPath
    if (-not $leanCtxBin) { return }

    $leanEntry = [ordered]@{
        command = $leanCtxBin
        env     = [ordered]@{ LEAN_CTX_DATA_DIR = (Join-Path $HOME ".config\lean-ctx") }
    }
    $claudeJson = Join-Path $HOME ".claude.json"
    if (Test-Path $claudeJson) {
        try {
            $cj = Get-Content $claudeJson -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($cj.mcpServers.'lean-ctx') {
                $src = $cj.mcpServers.'lean-ctx'
                if ($src.command) { $leanEntry.command = ($src.command -replace '\\', '/') }
                if ($src.env) {
                    $leanEntry.env = [ordered]@{}
                    foreach ($ep in $src.env.PSObject.Properties) { $leanEntry.env[$ep.Name] = $ep.Value }
                }
            }
        } catch {}
    }

    try {
        $desktop = Get-Content $desktopPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $finalDesktop = [ordered]@{}
        if ($desktop.mcpServers) {
            foreach ($p in $desktop.mcpServers.PSObject.Properties) { $finalDesktop[$p.Name] = $p.Value }
        }
        $finalDesktop['lean-ctx'] = $leanEntry
        if ($finalDesktop['lean-ctx'].PSObject.Properties.Name -contains 'autoApprove') {
            $finalDesktop['lean-ctx'].PSObject.Properties.Remove('autoApprove')
        }
        $finalDesktop['lean-ctx'].command = $leanCtxBin

        $desktopRoot = [ordered]@{}
        foreach ($p in $desktop.PSObject.Properties) {
            if ($p.Name -ne 'mcpServers') { $desktopRoot[$p.Name] = $p.Value }
        }
        $desktopRoot['mcpServers'] = $finalDesktop
        Write-TextNoBom $desktopPath ($desktopRoot | ConvertTo-Json -Depth 30)
        Write-OK "Claude Desktop: lean-ctx merged (no autoApprove)"
    } catch {
        Write-Warn2 "Could not merge lean-ctx into Claude Desktop: $_"
    }
}

function Repair-LeanCtxForCursor {
    if ($SkipCursor) { return }
    $mcpPath = Join-Path $env:USERPROFILE ".cursor\mcp.json"
    Repair-LeanCtxMcpFile $mcpPath 'Cursor'

    $leanCtxBin = Get-LeanCtxBinaryPath
    if (-not $leanCtxBin) { return }
    $hooksPath = Join-Path $env:USERPROFILE ".cursor\hooks.json"
    if (Test-Path $hooksPath) {
        try {
            $hooksRaw = Get-Content $hooksPath -Raw -Encoding UTF8
            $fixed = $hooksRaw -replace '"command":\s*"lean-ctx', "`"command`": `"$leanCtxBin"
            if ($fixed -ne $hooksRaw) {
                Write-TextNoBom $hooksPath $fixed
                Write-OK "Cursor hooks: lean-ctx uses absolute path (hooks run without user PATH)"
            }
        } catch {
            Write-Warn2 "Could not repair hooks.json: $_"
        }
    }
}

function Sync-GlobalCursorRules {
    if ($SkipCursor) { return }
    $rulesSrc = Join-Path $Root "cursor\rules"
    if (-not (Test-Path $rulesSrc)) { return }
    $rulesDest = Join-Path $HOME ".cursor\rules"
    if (-not (Test-Path $rulesDest)) { New-Item -ItemType Directory -Path $rulesDest -Force | Out-Null }
    foreach ($f in Get-ChildItem $rulesSrc -Filter '*.mdc' -File) {
        Copy-Item $f.FullName (Join-Path $rulesDest $f.Name) -Force
    }
    Write-OK "Synced global Cursor rules -> $rulesDest (overrides lean-ctx onboard's aggressive rule)"
}

function Remove-WorkspaceLeanCtxMcp([string]$repoPath) {
    if (-not $repoPath -or -not (Test-Path $repoPath)) { return }
    $wsMcp = Join-Path $repoPath ".cursor\mcp.json"
    if (-not (Test-Path $wsMcp)) { return }
    try {
        $mcp = Get-Content $wsMcp -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $mcp.mcpServers.'lean-ctx') { return }
        $mcp.mcpServers.PSObject.Properties.Remove('lean-ctx')
        Write-TextNoBom $wsMcp ($mcp | ConvertTo-Json -Depth 30)
        Write-OK "Removed duplicate workspace lean-ctx from $wsMcp (keep user-scope only)"
    } catch {
        Write-Warn2 "Could not strip workspace lean-ctx from $wsMcp : $_"
    }
}

function Remove-AlfredVendoredTasteSkills([string[]]$roots) {
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem $root -Directory -Filter 'alfred-taste-*' -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force
            Write-OK "Removed duplicate vendored skill '$($_.Name)' from $root"
        }
    }
}

function Install-ThirdPartyAgentSkills {
    if ($SkipThirdPartySkills) { return }
    $agentsSkills = Join-Path $HOME ".agents\skills\design-taste-frontend\SKILL.md"
    if (Test-Path $agentsSkills) {
        Write-Skip "taste-skill already in ~/.agents/skills -- skipping npx install."
        return
    }
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Write-Skip "npx not on PATH -- skipping third-party skills install."
        return
    }
    Write-Step "Third-party skills: Leonxlnx/taste-skill -> ~/.agents/skills"
    Push-Location $HOME
    try {
        $job = Start-Job -ScriptBlock {
            param($homeDir)
            Set-Location $homeDir
            & npx --yes skills add https://github.com/Leonxlnx/taste-skill --yes 2>&1
        } -ArgumentList $HOME
        if (-not (Wait-Job $job -Timeout 90)) {
            Stop-Job $job -Force | Out-Null
            Remove-Job $job -Force | Out-Null
            Write-Warn2 "taste-skill install exceeded 90s -- run manually: npx skills add https://github.com/Leonxlnx/taste-skill"
            return
        }
        $out = Receive-Job $job
        Remove-Job $job -Force | Out-Null
        foreach ($line in ($out | Out-String) -split "`r?`n") {
            $t = $line.Trim()
            if ($t) { Write-Info $t }
        }
        if (Test-Path $agentsSkills) {
            Write-OK "taste-skill installed globally (~/.agents/skills)"
        } else {
            Write-Warn2 "taste-skill install finished but SKILL.md not found -- run manually if needed."
        }
    } catch {
        Write-Warn2 "taste-skill install failed: $_"
    } finally {
        Pop-Location
    }
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
Write-Host "  Alfred Pack -> global provision (Cursor + Claude + Codex)" -ForegroundColor Cyan
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

# Ensure Alfred venv + bin are on PATH so excellm, uvx, az, vd, etc. resolve during provision.
$venvScripts = Join-Path $Root ".venv\Scripts"
$binDir = Join-Path $Root "bin"
foreach ($p in @($venvScripts, $binDir)) {
    if ((Test-Path $p) -and ($env:PATH -split ';' | Where-Object { $_.TrimEnd('\') -ieq $p.TrimEnd('\') }).Count -eq 0) {
        $env:PATH = "$p;$env:PATH"
    }
}

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
    $retiredServers = @()
    if ($tpl.PSObject.Properties.Name -contains '_retiredServers') {
        $retiredServers = @($tpl._retiredServers)
    }
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
                if ($defKeys -contains '_fallback' -and $def._fallback) {
                    Write-Info "$name : '$requiresCmd' not on PATH — using _fallback config."
                    $fb = $def._fallback
                    $def = [pscustomobject]@{
                        command = $fb.command
                        args    = @($fb.args)
                        env     = $def.env
                        _requires = $def._requires
                        _aliases  = $def._aliases
                    }
                    $defKeys = @($def.PSObject.Properties.Name)
                    $requiresCmd = $null
                } else {
                    $skippedServers += "$name (needs '$requiresCmd' on PATH)"
                    continue
                }
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
            if ($defKeys -contains 'type' -and $def.type) { $serverObj.type = [string]$def.type }
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
    foreach ($r in $retiredServers) {
        if ($final.Contains($r)) {
            $final.Remove($r)
            Write-Info "Removed retired MCP '$r' from Cursor config."
        }
    }

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
        foreach ($r in $retiredServers) {
            try { & claude mcp remove $r --scope user 2>$null | Out-Null } catch {}
        }
        foreach ($name in $managed.Keys) {
            $srv = $managed[$name]
            try { & claude mcp remove $name --scope user 2>$null | Out-Null } catch {}
            $argList = @('mcp', 'add', $name, '--scope', 'user')
            foreach ($e in $managedEnvLists[$name]) { $argList += @('--env', $e) }
            $argList += '--'
            $argList += $srv.command
            $argList += $srv.args
            Invoke-McpCliAdd 'claude' $name $argList | Out-Null
        }
    }
}

# ── Claude Desktop app: %APPDATA%\Claude\claude_desktop_config.json ─────────────
# Separate from Claude Code CLI (~/.claude.json). The Desktop "Connectors" UI reads this file.
if (-not $SkipClaudeDesktop -and $managed.Count -gt 0) {
    Write-Step "Claude Desktop: claude_desktop_config.json"
    $claudeAppDir = Join-Path $env:APPDATA "Claude"
    if (-not (Test-Path $claudeAppDir)) { New-Item -ItemType Directory -Path $claudeAppDir -Force | Out-Null }
    $desktopPath = Join-Path $claudeAppDir "claude_desktop_config.json"

    $desktopRoot = [ordered]@{}
    if (Test-Path $desktopPath) {
        try {
            $existingDesktop = Get-Content $desktopPath -Raw | ConvertFrom-Json
            foreach ($p in $existingDesktop.PSObject.Properties) {
                if ($p.Name -ne 'mcpServers') { $desktopRoot[$p.Name] = $p.Value }
            }
            $finalDesktop = [ordered]@{}
            if ($existingDesktop.mcpServers) {
                foreach ($p in $existingDesktop.mcpServers.PSObject.Properties) { $finalDesktop[$p.Name] = $p.Value }
            }
        } catch {
            Write-Warn2 "Existing claude_desktop_config.json unreadable -- backing up and recreating mcpServers."
            Copy-Item $desktopPath "$desktopPath.bak" -Force -ErrorAction SilentlyContinue
            $finalDesktop = [ordered]@{}
        }
    } else {
        $finalDesktop = [ordered]@{}
    }
    foreach ($k in $managed.Keys) { $finalDesktop[$k] = $managed[$k] }
    foreach ($r in $retiredServers) {
        if ($finalDesktop.Contains($r)) {
            $finalDesktop.Remove($r)
            Write-Info "Removed retired MCP '$r' from Claude Desktop config."
        }
    }
    $desktopRoot['mcpServers'] = $finalDesktop

    $json = $desktopRoot | ConvertTo-Json -Depth 30
    Write-TextNoBom $desktopPath $json
    Write-OK "Wrote $($managed.Count) managed server(s); $($finalDesktop.Count) total in $desktopPath"
    Write-Info "Restart the Claude Desktop app to see Connectors update."
}

# ── Codex: codex mcp add (global, idempotent) ─────────────────────────────────
# Makes the SAME global MCP servers usable from Codex, not just Claude/Cursor.
if (-not $SkipCodex -and $managed.Count -gt 0) {
    Write-Step "Codex: registering servers (global)"
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        Write-Skip "codex CLI not found -- skipping Codex MCP registration."
    } else {
        foreach ($r in $retiredServers) {
            try { & codex mcp remove $r 2>$null | Out-Null } catch {}
        }
        foreach ($name in $managed.Keys) {
            $srv = $managed[$name]
            try { & codex mcp remove $name 2>$null | Out-Null } catch {}
            $argList = @('mcp', 'add', $name)
            foreach ($e in $managedEnvLists[$name]) { $argList += @('--env', $e) }
            $argList += '--'
            $argList += $srv.command
            $argList += $srv.args
            Invoke-McpCliAdd 'codex' $name $argList | Out-Null
        }
    }
}

# ── Skills: sync skills/*.md into both tools as alfred-<name>/SKILL.md ─────────
$script:SkillSkipPatterns = @('taste-*', 'lean-ctx', 'mcp-routing')

function Test-SkillSkipped([string]$base) {
    foreach ($pat in $script:SkillSkipPatterns) {
        if ($base -like $pat) { return $true }
    }
    return $false
}

function Sync-Skills([string]$srcDir, [string[]]$destRoots) {
    if (-not (Test-Path $srcDir)) { Write-Skip "No skills/ directory at $srcDir"; return }
    $mdFiles = @(Get-ChildItem -Path $srcDir -Filter *.md -File)
    if ($mdFiles.Count -eq 0) { Write-Skip "No skill files in $srcDir"; return }
    foreach ($root in $destRoots) {
        if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }
    }
    $expectedSlugs = [System.Collections.Generic.HashSet[string]]::new()
    $synced = 0
    $skipped = 0
    foreach ($f in $mdFiles) {
        $base = ($f.BaseName.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')
        if (Test-SkillSkipped $base) {
            $skipped++
            continue
        }
        if ($base -like 'alfred-*') { $slug = $base } else { $slug = "alfred-$base" }
        [void]$expectedSlugs.Add($slug)
        $content = Get-Content $f.FullName -Raw

        if ($content -match '^\s*---') {
            $skillBody = $content -replace '(?m)^name:\s*.+$', "name: $slug"
        } else {
            $lines = $content -split "`n"
            $titleLine = $lines | Where-Object { $_ -match '^\s*#\s+\S' } | Select-Object -First 1
            if ($titleLine) { $title = ($titleLine -replace '^\s*#\s+', '').Trim() } else { $title = $f.BaseName }
            $descLine = $lines | Where-Object { $_.Trim() -ne '' -and $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*---' } | Select-Object -First 1
            if (-not $descLine) { $descLine = "Alfred skill: $title" }
            $descLine = ($descLine.Trim() -replace '"', '')
            if ($descLine.Length -gt 120) { $descLine = $descLine.Substring(0, 120) }
            $skillBody = "---`nname: $slug`ndescription: $descLine`n---`n`n" + $content
        }

        foreach ($root in $destRoots) {
            $dir = Join-Path $root $slug
            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            Write-TextNoBom (Join-Path $dir "SKILL.md") $skillBody
        }
        $synced++
    }
    foreach ($root in $destRoots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem $root -Directory -Filter 'alfred-*' -ErrorAction SilentlyContinue | ForEach-Object {
            if (-not $expectedSlugs.Contains($_.Name)) {
                Remove-Item $_.FullName -Recurse -Force
                Write-OK "Removed orphan skill '$($_.Name)' from $root"
            }
        }
    }
    Write-OK "Synced $synced skill(s), skipped $skipped (taste/lean-ctx/mcp-routing) -> $($destRoots -join ', ')"
}

Write-Step "Skills: syncing Alfred skills into Cursor + Claude Code + Codex"
$skillDests = @()
if (-not $SkipCursor) { $skillDests += (Join-Path $HOME ".cursor\skills") }
if (-not $SkipClaude) { $skillDests += (Join-Path $HOME ".claude\skills") }
if (-not $SkipCodex)  { $skillDests += (Join-Path $HOME ".codex\skills") }
Remove-AlfredVendoredTasteSkills $skillDests
if ($skillDests.Count -gt 0) { Sync-Skills (Join-Path $Root "skills") $skillDests }
Install-ThirdPartyAgentSkills

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
        Remove-WorkspaceLeanCtxMcp $ProjectPath
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

# ── LeanCTX: context compression (merge-based — runs AFTER Alfred MCPs) ───────
# Runs lean-ctx with stdin closed and a hard timeout so it can NEVER block the
# install on an interactive prompt. Returns $true only on a clean exit 0.
function Invoke-LeanCtxGuarded([string]$Arguments, [int]$TimeoutSec = 120) {
    $exe = (Get-Command lean-ctx.cmd -ErrorAction SilentlyContinue).Source
    if (-not $exe) { $exe = (Get-Command lean-ctx -ErrorAction SilentlyContinue).Source }
    if (-not $exe) { return $false }
    $inF  = Join-Path $env:TEMP "leanctx_empty.in"
    $outF = Join-Path $env:TEMP "leanctx_$PID.out"
    $errF = Join-Path $env:TEMP "leanctx_$PID.err"
    New-Item -ItemType File -Path $inF -Force | Out-Null
    try {
        $p = Start-Process -FilePath $exe -ArgumentList $Arguments -NoNewWindow -PassThru `
             -RedirectStandardInput $inF -RedirectStandardOutput $outF -RedirectStandardError $errF
    } catch {
        Write-Warn2 "Could not start lean-ctx: $_"
        return $false
    }
    if (-not $p.WaitForExit($TimeoutSec * 1000)) {
        Write-Warn2 "lean-ctx $Arguments exceeded ${TimeoutSec}s -- killing and skipping (install continues)."
        & taskkill /PID $p.Id /T /F 2>&1 | Out-Null
        return $false
    }
    # onboard returns a non-zero "already connected" code on idempotent re-runs even
    # though it succeeded, so treat a clear success marker in the output as success too.
    $connected = $false
    foreach ($f in @($outF, $errF)) {
        if (Test-Path $f) {
            $raw = Get-Content $f -Raw
            if ($raw -match 'is connected|init complete|already configured') { $connected = $true }
            ($raw -split "`r?`n") | Where-Object { $_.Trim() } | ForEach-Object { Write-Info $_ }
        }
    }
    return (($p.ExitCode -eq 0) -or $connected)
}

if (-not $SkipLeanCtx) {
    Write-Step "LeanCTX: wiring context compression into Cursor + Claude + Codex"
    if (-not (Get-Command lean-ctx -ErrorAction SilentlyContinue)) {
        Write-Skip "lean-ctx not on PATH -- install lean-ctx-bin (npm-tools.txt), then re-run."
    } else {
        try {
            # lean-ctx 3.7.x: 'onboard' connects all detected AI tools with recommended
            # defaults. The old 'bootstrap' verb was REMOVED and now blocks on a stdin
            # prompt (hangs the installer), so we run 'onboard' stdin-closed under a hard
            # timeout via Invoke-LeanCtxGuarded -- it can never stall provisioning.
            $leanOk = Invoke-LeanCtxGuarded -Arguments 'onboard' -TimeoutSec 120
            Repair-LeanCtxForCursor
            Sync-LeanCtxToClaudeDesktop
            Sync-GlobalCursorRules
            if ($leanOk) {
                Write-OK "LeanCTX connected (ctx_* tools + hooks). No API keys required."
            } else {
                Write-Warn2 "lean-ctx onboard did not finish cleanly -- run 'lean-ctx onboard' manually later. Install continues."
            }
        } catch {
            Write-Warn2 "lean-ctx onboard failed: $_ -- install continues."
            Repair-LeanCtxForCursor
            Sync-LeanCtxToClaudeDesktop
            Sync-GlobalCursorRules
        }
    }
} else {
    Sync-GlobalCursorRules
}

# ── summary ───────────────────────────────────────────────────────────────────
if ($skippedServers.Count -gt 0) {
    Write-Step "Skipped servers (add the secret/prereq to Alfred .env, then re-run):"
    foreach ($s in $skippedServers) { Write-Info "- $s" }
}

if ($script:ProvisionErrors.Count -gt 0) {
    Write-Host ""
    Write-Warn2 "Provisioning finished with $($script:ProvisionErrors.Count) MCP registration error(s):"
    foreach ($e in $script:ProvisionErrors) { Write-Info "- $e" }
}

Write-Host ""
Write-Host "Provisioning complete. Restart Cursor, Claude Desktop, Claude Code, and/or Codex." -ForegroundColor Green
Write-Info "MCP tokens are machine-local only — rotate keys in Alfred .env if configs are ever shared."
Write-Host ""

if ($script:ProvisionErrors.Count -gt 0) { exit 1 }
