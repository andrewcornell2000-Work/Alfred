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
.PARAMETER SeedProjects
    Additional repos to seed rules + AGENTS.md + graphify into. Also read from
    ALFRED_PROJECT_PATHS in Alfred .env (semicolon-separated), so day-to-day
    repos are seeded on every provision without remembering a flag.
.PARAMETER SkipDoctor
    Skip the post-provision Alfred-Doctor.ps1 verification report.
.PARAMETER SkipCursor
    Skip Cursor (~/.cursor) provisioning.
.PARAMETER SkipClaude
    Skip Claude Code (claude mcp / ~/.claude) provisioning.
.PARAMETER SkipClaudeDesktop
    Skip Claude Desktop app (%APPDATA%\Claude\claude_desktop_config.json).
.PARAMETER SkipCodex
    Skip Codex (codex mcp add) provisioning.
.PARAMETER SkipThirdPartySkills
    Skip npx install of third-party agent skills (e.g. Leonxlnx/taste-skill).
#>
[CmdletBinding()]
param(
    [string]$ProjectPath,
    [string[]]$SeedProjects = @(),
    [switch]$SkipDoctor,
    [switch]$SkipCursor,
    [switch]$SkipClaude,
    [switch]$SkipClaudeDesktop,
    [switch]$SkipCodex,
    [switch]$SkipCloseAgentApps,
    [switch]$SkipThirdPartySkills,
    [switch]$SkipOptionalPlugins,
    [string]$Buckets = '',
    [switch]$SyncOnly,
    [switch]$InstallerMode
)

# -SyncOnly: fast path for Alfred-Sync.ps1 — sync skills + subagents only, no MCP
# registration, no app-closing, no doctor. Reuses the existing per-target skips.
if ($SyncOnly) {
    $SkipCursor = $true; $SkipClaude = $true; $SkipClaudeDesktop = $true
    $SkipThirdPartySkills = $true; $SkipOptionalPlugins = $true; $SkipDoctor = $true; $SkipCloseAgentApps = $true
}

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

$closeAppsScript = Join-Path $Root 'installer\Close-AgentApps.ps1'
if (Test-Path $closeAppsScript) { . $closeAppsScript }

$removeLeanCtxScript = Join-Path $Root 'installer\Remove-LeanCtx.ps1'
if (Test-Path $removeLeanCtxScript) { . $removeLeanCtxScript -RepoRoot $Root }

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

function Invoke-McpCliAdd([string]$toolName, [string]$serverName, [string[]]$argList) {
    $exe = (Get-Command $toolName -ErrorAction SilentlyContinue).Source
    if (-not $exe) {
        Write-Warn2 "$toolName not found -- skipped '$serverName'."
        return $false
    }

    if ($InstallerMode) {
        $tag = "$PID-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
        $outF = Join-Path $env:TEMP "alfred_mcp_$tag.out"
        $errF = Join-Path $env:TEMP "alfred_mcp_$tag.err"
        try {
            $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru `
                -RedirectStandardOutput $outF -RedirectStandardError $errF
            if (-not $p.WaitForExit(120000)) {
                & taskkill /PID $p.Id /T /F 2>&1 | Out-Null
                Write-Warn2 "$toolName mcp add '$serverName' timed out -- configure manually later."
                return $false
            }
            $stderr = if (Test-Path $errF) { Get-Content $errF -Raw } else { '' }
            $exitCode = $p.ExitCode
        } finally {
            Remove-Item $outF, $errF -Force -ErrorAction SilentlyContinue
        }
    } else {
        $stderr = & $toolName @argList 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }

    if ($exitCode -eq 0) {
        Write-OK "Registered '$serverName' ($toolName)."
        return $true
    }
    $detail = "$stderr".Trim()
    if ($detail.Length -gt 300) { $detail = $detail.Substring(0, 300) + "..." }
    $msg = "$toolName mcp add '$serverName' failed (exit $exitCode): $detail"
    $script:ProvisionErrors += $msg
    Write-Warn2 $msg
    return $false
}

function Sync-AlfredRepoCtxRules {
    param([string]$RepoRoot = $Root)

    if (-not $RepoRoot -or -not (Test-Path $RepoRoot)) { return }

    $cursorrules = @'
# Alfred agent tooling

See `.cursor/rules/00-agent-tooling.mdc` (native Read/Grep/Shell/Edit default).
'@
    Write-TextNoBom (Join-Path $RepoRoot '.cursorrules') $cursorrules
    Write-OK "Synced repo .cursorrules -> native-first agent tooling"
}

# NOTE: global ~/.cursor/rules syncing was removed deliberately (2026-07-10 audit):
# Cursor has no documented global rules directory — User Rules live in the Settings
# GUI and project rules in <repo>/.cursor/rules. Seeding is per-project (see
# Invoke-ProjectSeed below / ALFRED_PROJECT_PATHS in .env).

function Remove-AlfredVendoredTasteSkills([string[]]$roots) {
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem $root -Directory -Filter 'alfred-taste-*' -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force
            Write-OK "Removed duplicate vendored skill '$($_.Name)' from $root"
        }
    }
}

function Invoke-NpxBackgroundJob([string]$Label, [string[]]$NpxArgs, [int]$TimeoutSec = 120) {
    $npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
    if (-not $npx) { $npx = (Get-Command npx -ErrorAction SilentlyContinue).Source }
    if (-not $npx) {
        Write-Warn2 "$Label skipped -- npx not on PATH"
        return $false
    }

    $savedPath = $env:PATH
    foreach ($extra in @(
        (Join-Path $env:APPDATA 'npm'),
        (Join-Path $env:LOCALAPPDATA 'Programs\cursor\resources\app\bin')
    )) {
        if ((Test-Path $extra) -and ($env:PATH -split ';' | Where-Object { $_.TrimEnd('\') -ieq $extra.TrimEnd('\') }).Count -eq 0) {
            $env:PATH = "$extra;$env:PATH"
        }
    }

    Push-Location $HOME
    try {
        $outF = Join-Path $env:TEMP "alfred_npx_$PID.out"
        $errF = Join-Path $env:TEMP "alfred_npx_$PID.err"
        if (Test-Path $outF) { Remove-Item $outF -Force -ErrorAction SilentlyContinue }
        if (Test-Path $errF) { Remove-Item $errF -Force -ErrorAction SilentlyContinue }

        $p = Start-Process -FilePath $npx -ArgumentList $NpxArgs -NoNewWindow -PassThru `
             -WorkingDirectory $HOME -RedirectStandardOutput $outF -RedirectStandardError $errF
        if (-not $p.WaitForExit($TimeoutSec * 1000)) {
            & taskkill /PID $p.Id /T /F 2>&1 | Out-Null
            Write-Warn2 "$Label exceeded ${TimeoutSec}s -- run manually: npx $($NpxArgs -join ' ')"
            return $false
        }
        foreach ($f in @($outF, $errF)) {
            if (Test-Path $f) {
                Get-Content $f | ForEach-Object {
                    $t = $_.Trim()
                    if ($t) { Write-Info $t }
                }
            }
        }
        return ($p.ExitCode -eq 0)
    } catch {
        Write-Warn2 "$Label failed: $_"
        return $false
    } finally {
        $env:PATH = $savedPath
        Pop-Location
    }
}

function Test-SupabaseAgentSkillsInstalled {
    return (Test-Path (Join-Path $HOME ".agents\skills\supabase\SKILL.md"))
}

function Test-VercelPluginInstalled {
    foreach ($root in @(
        (Join-Path $HOME ".cursor\plugins"),
        (Join-Path $HOME ".claude\plugins"),
        (Join-Path $HOME ".codex\plugins"),
        (Join-Path $HOME ".agents\skills")
    )) {
        if (-not (Test-Path $root)) { continue }
        if (Get-ChildItem $root -Directory -Filter '*vercel*' -ErrorAction SilentlyContinue | Select-Object -First 1) {
            return $true
        }
    }
    return $false
}

function Install-ThirdPartyAgentSkills {
    if ($SkipThirdPartySkills) { return }
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Write-Skip "npx not on PATH -- skipping third-party skills/plugins install."
        return
    }

    $agentsSkills = Join-Path $HOME ".agents\skills\design-taste-frontend\SKILL.md"
    if (Test-Path $agentsSkills) {
        Write-Skip "taste-skill already in ~/.agents/skills -- skipping npx install."
    } else {
        Write-Step "Third-party skills: Leonxlnx/taste-skill -> ~/.agents/skills"
        if (Invoke-NpxBackgroundJob 'taste-skill' @('--yes', 'skills', 'add', 'https://github.com/Leonxlnx/taste-skill', '--yes') 90) {
            if (Test-Path $agentsSkills) {
                Write-OK "taste-skill installed globally (~/.agents/skills)"
            } else {
                Write-Warn2 "taste-skill install finished but SKILL.md not found -- run manually if needed."
            }
        }
    }

    if (Test-SupabaseAgentSkillsInstalled) {
        Write-Skip "supabase/agent-skills already in ~/.agents/skills -- skipping npx install."
    } else {
        Write-Step "Third-party skills: supabase/agent-skills -> ~/.agents/skills"
        if (Invoke-NpxBackgroundJob 'supabase/agent-skills' @('--yes', 'skills', 'add', 'supabase/agent-skills', '--yes') 120) {
            if (Test-SupabaseAgentSkillsInstalled) {
                Write-OK "supabase/agent-skills installed globally (~/.agents/skills)"
            } else {
                Write-Warn2 "supabase/agent-skills install finished but no supabase* skill folder found -- run manually: npx skills add supabase/agent-skills"
            }
        }
    }

    if (Test-VercelPluginInstalled) {
        Write-Skip "vercel/vercel-plugin already installed -- skipping npx install."
    } elseif ($SkipOptionalPlugins -or $InstallerMode) {
        Write-Skip "vercel/vercel-plugin deferred -- install later if you use Vercel: npx plugins add vercel/vercel-plugin"
    } else {
        Write-Step "Third-party plugin: vercel/vercel-plugin (skills, agents, slash commands)"
        if (Invoke-NpxBackgroundJob 'vercel/vercel-plugin' @('--yes', 'plugins', 'add', 'vercel/vercel-plugin', '--yes', '--target', 'claude-code', '--target', 'cursor', '--target', 'codex') 180) {
            if (Test-VercelPluginInstalled) {
                Write-OK "vercel/vercel-plugin installed (see https://vercel.com/docs/agent-resources/vercel-plugin)"
            } else {
                Write-Warn2 "vercel/vercel-plugin install finished but plugin folder not detected -- run manually: npx plugins add vercel/vercel-plugin"
            }
        }
    }

    # Jean Paul / Boostl design stack (global ~/.agents/skills)
    $designSkills = @(
        @{ Name = 'ui-design-brain';    Repo = 'https://github.com/carmahhawwari/ui-design-brain';    Skill = 'ui-design-brain' },
        @{ Name = 'frontend-design';    Repo = 'https://github.com/anthropics/skills';                 Skill = 'frontend-design' },
        @{ Name = 'accessibility';      Repo = 'https://github.com/addyosmani/web-quality-skills';     Skill = 'accessibility' }
    )
    foreach ($ds in $designSkills) {
        $skillPath = Join-Path $HOME ".agents\skills\$($ds.Name)\SKILL.md"
        if (Test-Path $skillPath) {
            Write-Skip "$($ds.Name) already in ~/.agents/skills -- skipping npx install."
            continue
        }
        Write-Step "Third-party skills: $($ds.Name) -> ~/.agents/skills"
        $args = @('--yes', 'skills', 'add', $ds.Repo, '--skill', $ds.Skill, '--yes')
        if (Invoke-NpxBackgroundJob $ds.Name $args 120) {
            if (Test-Path $skillPath) {
                Write-OK "$($ds.Name) installed globally (~/.agents/skills)"
            } else {
                Write-Warn2 "$($ds.Name) install finished but SKILL.md not found -- run manually: npx skills add $($ds.Repo) --skill $($ds.Skill)"
            }
        }
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

if (-not $SkipCloseAgentApps -and (Get-Command Stop-AlfredAgentProcesses -ErrorAction SilentlyContinue)) {
    Write-Step 'Closing Cursor, Claude, and ChatGPT before provisioning...'
    Stop-AlfredAgentProcesses | Out-Null
}

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

# ── MCP bucket selection (which categories install on THIS machine) ────────────
# Each server in cursor/mcp.json has a "_bucket" category. Only servers whose
# bucket is selected get installed, so e.g. a laptop that never touches Power BI
# doesn't run that server. Precedence: -Buckets param > ALFRED_BUCKETS in .env >
# interactive picker > default (core,office365,web). 'core' is always included.
$bucketCatalog = [ordered]@{}   # bucket -> description
$serverBucket  = @{}            # server -> bucket
$McpTemplateForBuckets = Join-Path $Root "cursor\mcp.json"
if (Test-Path $McpTemplateForBuckets) {
    try {
        $tplB = Get-Content $McpTemplateForBuckets -Raw | ConvertFrom-Json
        if ($tplB.PSObject.Properties.Name -contains '_buckets') {
            foreach ($bp in $tplB._buckets.PSObject.Properties) { $bucketCatalog[$bp.Name] = [string]$bp.Value }
        }
        foreach ($sp in $tplB.mcpServers.PSObject.Properties) {
            $bk = 'core'
            if (@($sp.Value.PSObject.Properties.Name) -contains '_bucket') { $bk = [string]$sp.Value._bucket }
            $serverBucket[$sp.Name] = $bk.ToLower()
            if (-not $bucketCatalog.Contains($bk)) { $bucketCatalog[$bk] = '' }
        }
    } catch {}
}

function Resolve-SelectedBuckets {
    $sel = @(); $raw = ''
    if ($Buckets) { $raw = $Buckets }
    elseif ($EnvMap.ContainsKey('ALFRED_BUCKETS') -and $EnvMap['ALFRED_BUCKETS']) { $raw = [string]$EnvMap['ALFRED_BUCKETS'] }

    if ($raw) {
        if ($raw.ToLower().Trim() -eq 'all') { return @($bucketCatalog.Keys) }
        $sel = @($raw -split '[,; ]+' | Where-Object { $_ })
    }
    elseif ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
        Write-Step "Choose MCP buckets to install on this machine"
        $names = @($bucketCatalog.Keys)
        for ($i = 0; $i -lt $names.Count; $i++) {
            $bn = $names[$i]
            $servers = @($serverBucket.GetEnumerator() | Where-Object { $_.Value -eq $bn.ToLower() } | ForEach-Object { $_.Key })
            $tag = if ($bn -eq 'core') { ' (always on)' } else { '' }
            Write-Host ("   [{0}] {1,-10}{2} - {3}" -f ($i + 1), $bn, $tag, $bucketCatalog[$bn]) -ForegroundColor Gray
            Write-Host ("        {0}" -f ($servers -join ', ')) -ForegroundColor DarkGray
        }
        $pick = Read-Host "Enter numbers/names (comma-separated), 'all', or Enter for [core,office365,web]"
        if (-not $pick) { $sel = @('core', 'office365', 'web') }
        elseif ($pick.ToLower().Trim() -eq 'all') { $sel = @($bucketCatalog.Keys) }
        else {
            foreach ($tok in ($pick -split '[,; ]+' | Where-Object { $_ })) {
                if ($tok -match '^\d+$') { $idx = [int]$tok - 1; if ($idx -ge 0 -and $idx -lt $names.Count) { $sel += $names[$idx] } }
                else { $sel += $tok }
            }
        }
    }
    else {
        # non-interactive with no explicit choice: install everything (never silently drop).
        $sel = @($bucketCatalog.Keys)
        Write-Info "Non-interactive, no bucket selection -> installing all buckets. Set -Buckets or ALFRED_BUCKETS to trim."
    }
    $sel = @(@($sel) + 'core' | ForEach-Object { $_.ToLower().Trim() } | Where-Object { $_ } | Select-Object -Unique)
    return @($sel | Where-Object { $bucketCatalog.Contains($_) })
}
$SelectedBuckets = @(Resolve-SelectedBuckets)
Write-Info ("Selected MCP buckets: " + ($SelectedBuckets -join ', '))
# persist choice so re-provisions are consistent + non-interactive
# (never during -SyncOnly: a background sync must not change the user's selection)
if (-not $SyncOnly) {
try {
    $envPath = Join-Path $Root ".env"
    $joined = ($SelectedBuckets -join ',')
    $lines = if (Test-Path $envPath) { @(Get-Content $envPath) } else { @() }
    if ($lines | Where-Object { $_ -match '^\s*ALFRED_BUCKETS\s*=' }) {
        $lines = $lines | ForEach-Object { if ($_ -match '^\s*ALFRED_BUCKETS\s*=') { "ALFRED_BUCKETS=$joined" } else { $_ } }
    } else { $lines += "ALFRED_BUCKETS=$joined" }
    Set-Content -Path $envPath -Value $lines -Encoding UTF8
} catch {}
}
$bucketDeferred = @()

# ── skill bucketing (same buckets as MCPs) ─────────────────────────────────────
# skills/_buckets.json maps each skill (and vendored _packs/<name>) to a bucket.
# Only skills whose bucket is selected sync to ~/.agents/skills; the rest are
# pruned by the existing orphan cleanup. Unlisted skills fall back to _default.
$skillBucketMap = @{}; $packBucketMap = @{}; $skillDefaultBucket = 'core'
$skillBucketsFile = Join-Path $Root "skills\_buckets.json"
if (Test-Path $skillBucketsFile) {
    try {
        $sb = Get-Content $skillBucketsFile -Raw | ConvertFrom-Json
        if ($sb.PSObject.Properties.Name -contains '_default') { $skillDefaultBucket = ([string]$sb._default).ToLower() }
        if ($sb.PSObject.Properties.Name -contains 'skills') {
            foreach ($p in $sb.skills.PSObject.Properties) { $skillBucketMap[$p.Name.ToLower()] = ([string]$p.Value).ToLower() }
        }
        if ($sb.PSObject.Properties.Name -contains 'packs') {
            foreach ($p in $sb.packs.PSObject.Properties) { $packBucketMap[$p.Name.ToLower()] = ([string]$p.Value).ToLower() }
        }
    } catch { Write-Warn2 "skills/_buckets.json unreadable -- syncing all skills." }
}
function Test-SkillBucketSelected([string]$skillBase) {
    $b = $skillDefaultBucket
    $key = ($skillBase.ToLower() -replace '^alfred-','')
    if ($skillBucketMap.ContainsKey($key)) { $b = $skillBucketMap[$key] }
    return ($SelectedBuckets -contains $b)
}

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

function Expand-EnvPlaceholders([string]$value, [hashtable]$envMap, [hashtable]$aliases, [array]$requires, [ref]$missingRequired) {
    if ([string]::IsNullOrWhiteSpace($value)) { return $value }
    return [regex]::Replace($value, '\$\{env:([^}]+)\}', {
        param($m)
        $varName = $m.Groups[1].Value
        $lookups = @($varName)
        if ($aliases.ContainsKey($varName)) { $lookups += $aliases[$varName] }
        $secret = $null
        foreach ($ln in $lookups) { $secret = Resolve-Secret $ln $envMap; if ($secret) { break } }
        if ($secret) { return $secret }
        if ($requires -contains $varName) { $missingRequired.Value = $varName }
        return $m.Value
    })
}

# Does this command refer to an absolute file path that is missing on this machine?
function Test-CommandMissing([string]$command) {
    if ([string]::IsNullOrWhiteSpace($command)) { return $true }   # unresolved token
    if ($command -match '^[A-Za-z]:\\') { return -not (Test-Path $command) }
    return $false   # bare commands (npx, uvx, python) resolve via PATH at runtime
}

# ── resolve MCP servers from the template ─────────────────────────────────────
$McpTemplatePath = Join-Path $Root "cursor\mcp.json"
$managed         = [ordered]@{}   # name -> ordered hashtable { command, args, env } or { url }
$managedEnvLists = @{}            # name -> array of "KEY=VALUE" (for claude --env)
$oauthDeferred   = @{}            # name -> $true when OAuth happens at first use in the IDE
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
            if ($defKeys -contains '_oauthOnFirstUse' -and $def._oauthOnFirstUse) {
                $oauthDeferred[$name] = $true
            }
            $aliases = @{}
            if ($defKeys -contains '_aliases') {
                foreach ($ap in $def._aliases.PSObject.Properties) { $aliases[$ap.Name] = @($ap.Value) }
            }

            # Bucket selection: skip servers whose category isn't selected here.
            $srvBucket = 'core'; if ($defKeys -contains '_bucket') { $srvBucket = ([string]$def._bucket).ToLower() }
            if ($SelectedBuckets -notcontains $srvBucket) {
                $bucketDeferred += $name
                continue
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

            if ($defKeys -contains 'url') {
                $urlMissingRequired = $null
                $expandedUrl = Expand-Tokens ([string]$def.url)
                $expandedUrl = Expand-EnvPlaceholders $expandedUrl $EnvMap $aliases $requires ([ref]$urlMissingRequired)
                if ($urlMissingRequired) {
                    $skippedServers += "$name (missing required secret '$urlMissingRequired' -- add it to Alfred .env)"
                    continue
                }
                if ($expandedUrl -match '\$\{env:') {
                    $skippedServers += "$name (unresolved env placeholder in URL -- add values to Alfred .env)"
                    continue
                }
                $serverObj = [ordered]@{ url = $expandedUrl }
                $managed[$name] = $serverObj
                $managedEnvLists[$name] = $envList
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
    # Servers in non-selected buckets are removed from every target too, so a prior
    # provision that wrote them is cleaned up on re-provision (selection takes effect).
    if ($bucketDeferred.Count -gt 0) { $retiredServers = @($retiredServers) + @($bucketDeferred) }
}

if ($managed.Count -gt 0) {
    Write-Step "Resolved $($managed.Count) MCP server(s): $($managed.Keys -join ', ')"
}
if ($bucketDeferred.Count -gt 0) {
    Write-Skip "MCPs in non-selected buckets (not installed here): $($bucketDeferred -join ', ')"
    Write-Info "Add a bucket later: Provision-Cursor.ps1 -Buckets `"$($SelectedBuckets -join ',')`,powerbi`"  (or 'all'), or edit ALFRED_BUCKETS in .env"
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
            if ($oauthDeferred[$name]) {
                Write-Info "$name : in mcp.json only -- sign in from Cursor/Claude when you first use it."
                continue
            }
            try { & claude mcp remove $name --scope user 2>$null | Out-Null } catch {}
            if ($srv.url) {
                $argList = @('mcp', 'add', $name, '--scope', 'user', '--transport', 'http', [string]$srv.url)
                Invoke-McpCliAdd 'claude' $name $argList | Out-Null
                continue
            }
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
if (-not $SkipCodex -and -not $SyncOnly -and $managed.Count -gt 0) {
    Write-Step "Codex: registering servers (global)"
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        Write-Skip "codex CLI not found -- skipping Codex MCP registration."
    } else {
        foreach ($r in $retiredServers) {
            try { & codex mcp remove $r 2>$null | Out-Null } catch {}
        }
        foreach ($name in $managed.Keys) {
            $srv = $managed[$name]
            if ($oauthDeferred[$name]) {
                Write-Info "$name : in mcp.json only -- sign in from Codex when you first use it."
                continue
            }
            try { & codex mcp remove $name 2>$null | Out-Null } catch {}
            if ($srv.url) {
                $argList = @('mcp', 'add', $name, '--url', [string]$srv.url)
                Invoke-McpCliAdd 'codex' $name $argList | Out-Null
                continue
            }
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
$script:SkillSkipPatterns = @('taste-*', 'mcp-routing')

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
        # Bucket filter: skip skills whose category isn't selected (auto-pruned below).
        if ((Get-Command Test-SkillBucketSelected -ErrorAction SilentlyContinue) -and -not (Test-SkillBucketSelected $base)) {
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
    Write-OK "Synced $synced skill(s), skipped $skipped (taste/mcp-routing) -> $($destRoots -join ', ')"
}

# Folder skills (a directory with SKILL.md + bundled references) are copied whole,
# preserving structure and frontmatter. Used for vendored multi-file skill packs
# under skills/_packs/<pack>/<skill>/ (e.g. Microsoft skills-for-fabric).
function Sync-SkillFolders([string]$packsDir, [string[]]$destRoots) {
    if (-not (Test-Path $packsDir)) { Write-Skip "No skill packs at $packsDir"; return }
    $skillDirs = @(Get-ChildItem $packsDir -Recurse -Directory -ErrorAction SilentlyContinue |
                   Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') })
    if ($skillDirs.Count -eq 0) { return }
    foreach ($root in $destRoots) {
        if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }
    }
    $copied = 0; $pruned = 0
    foreach ($sd in $skillDirs) {
        # pack = first directory segment under packsDir; bucket via packBucketMap
        $rel  = $sd.FullName.Substring($packsDir.Length).TrimStart('\', '/')
        $pack = ($rel -split '[\\/]')[0]
        $pb = $skillDefaultBucket
        if ($packBucketMap -and $packBucketMap.ContainsKey($pack.ToLower())) { $pb = $packBucketMap[$pack.ToLower()] }
        $selected = ($SelectedBuckets -contains $pb)
        foreach ($root in $destRoots) {
            $dest = Join-Path $root $sd.Name
            if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
            if ($selected) { Copy-Item $sd.FullName $dest -Recurse -Force }
        }
        if ($selected) { $copied++ } else { $pruned++ }
    }
    Write-OK "Synced $copied folder skill(s); pruned $pruned in non-selected buckets -> $($destRoots -join ', ')"
}

# Impeccable (pbakaus/impeccable) — a multi-file design skill vendored under
# skills/_vendor/impeccable. Unlike _packs folder skills (copied verbatim to every
# harness), impeccable's SKILL.md and reference docs hard-code the skill's own script
# path (".claude/skills/impeccable/scripts/..."). We copy the canonical build per
# harness and rewrite that prefix so `node ...` script calls resolve correctly under
# Cursor (.cursor), Claude Code (.claude), and Codex (.codex).
function Sync-Impeccable([hashtable]$harnessRoots) {
    $src = Join-Path $Root "skills\_vendor\impeccable"
    if (-not (Test-Path (Join-Path $src 'SKILL.md'))) { Write-Skip "impeccable not vendored at $src"; return }
    foreach ($harness in $harnessRoots.Keys) {
        $root = $harnessRoots[$harness]
        if (-not $root) { continue }
        if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }
        $dest = Join-Path $root 'impeccable'
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $src $dest -Recurse -Force
        # Drop the Alfred-only provenance note from the live skill.
        $prov = Join-Path $dest '.alfred-source.md'
        if (Test-Path $prov) { Remove-Item $prov -Force }
        # Rewrite the script-path prefix for non-Claude harnesses (canonical build is Claude).
        if ($harness -ne 'claude') {
            $fromPrefix = ".claude/skills/impeccable"
            $toPrefix   = ".$harness/skills/impeccable"
            Get-ChildItem $dest -Recurse -Filter *.md -File | ForEach-Object {
                $txt = Get-Content $_.FullName -Raw -Encoding UTF8
                if ($txt.Contains($fromPrefix)) {
                    Write-TextNoBom $_.FullName ($txt.Replace($fromPrefix, $toPrefix))
                }
            }
        }
    }
    Write-OK "Synced impeccable design skill -> $($harnessRoots.Values -join ', ')"
}

# Wire impeccable's deterministic pre-edit detector hook into Cursor's GLOBAL hooks.json
# (preToolUse), with an absolute node path so it runs without relying on the user's PATH.
# Merges into the existing file (preserves other hooks). Idempotent.
function Wire-ImpeccableCursorHook {
    if ($SkipCursor) { return }
    $cursorDir   = Join-Path $HOME ".cursor"
    $skillScript = Join-Path $cursorDir "skills\impeccable\scripts\hook-before-edit.mjs"
    if (-not (Test-Path $skillScript)) { return }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Skip "node not on PATH -- impeccable Cursor hook not wired (skill still works; deterministic pre-edit checks disabled)."
        return
    }
    $hooksPath = Join-Path $cursorDir "hooks.json"
    $cmd = 'node "' + ($skillScript -replace '\\', '/') + '"'
    $hooks = $null
    if (Test-Path $hooksPath) {
        try { $hooks = Get-Content $hooksPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $hooks = $null }
    }
    if (-not $hooks) { $hooks = [pscustomobject]@{ version = 1; hooks = [pscustomobject]@{} } }
    if (-not ($hooks.PSObject.Properties.Name -contains 'hooks') -or -not $hooks.hooks) {
        $hooks | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $pre = @()
    if (($hooks.hooks.PSObject.Properties.Name -contains 'preToolUse') -and $hooks.hooks.preToolUse) {
        $pre = @($hooks.hooks.preToolUse)
    }
    if (-not ($pre | Where-Object { $_.command -eq $cmd })) {
        $pre += [pscustomobject]@{ command = $cmd; timeout = 5 }
    }
    if ($hooks.hooks.PSObject.Properties.Name -contains 'preToolUse') {
        $hooks.hooks.preToolUse = $pre
    } else {
        $hooks.hooks | Add-Member -NotePropertyName preToolUse -NotePropertyValue $pre -Force
    }
    Write-TextNoBom $hooksPath ($hooks | ConvertTo-Json -Depth 30)
    Write-OK "Wired impeccable pre-edit detector hook into Cursor hooks.json (absolute node path)"
}

# Skills land ONCE in ~/.agents/skills — the cross-tool Agent Skills standard.
# Cursor, Claude Code, and Codex all scan it (Cursor additionally scans the legacy
# ~/.cursor|.claude|.codex skill roots, so per-tool copies show up in triplicate —
# that duplication is why the legacy copies are actively removed below).
# Exception: impeccable stays per-harness because its docs hard-code harness paths.
function Remove-LegacySkillCopies {
    $packNames = @()
    $packsDir = Join-Path $Root "skills\_packs"
    if (Test-Path $packsDir) {
        $packNames = @(Get-ChildItem $packsDir -Recurse -Directory -ErrorAction SilentlyContinue |
                       Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } |
                       ForEach-Object { $_.Name })
    }
    foreach ($tool in @('.cursor', '.claude', '.codex')) {
        $root = Join-Path $HOME "$tool\skills"
        if (-not (Test-Path $root)) { continue }
        $removed = 0
        Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            if (($_.Name -like 'alfred-*') -or ($packNames -contains $_.Name)) {
                Remove-Item $_.FullName -Recurse -Force
                $removed++
            }
        }
        if ($removed -gt 0) { Write-OK "Removed $removed legacy skill cop(ies) from $root (now served from ~/.agents/skills)" }
    }
}

Write-Step "Skills: syncing Alfred skills once into ~/.agents/skills (read by Cursor + Claude Code + Codex)"
$agentsSkillsRoot = Join-Path $HOME ".agents\skills"
Remove-AlfredVendoredTasteSkills @($agentsSkillsRoot)
Sync-Skills (Join-Path $Root "skills") @($agentsSkillsRoot)
Sync-SkillFolders (Join-Path $Root "skills\_packs") @($agentsSkillsRoot)
Remove-LegacySkillCopies
$impeccableRoots = @{}
if (-not $SkipCursor) { $impeccableRoots['cursor'] = (Join-Path $HOME ".cursor\skills") }
if (-not $SkipClaude) { $impeccableRoots['claude'] = (Join-Path $HOME ".claude\skills") }
if (-not $SkipCodex)  { $impeccableRoots['codex']  = (Join-Path $HOME ".codex\skills") }
if ($impeccableRoots.Count -gt 0) { Sync-Impeccable $impeccableRoots }
Install-ThirdPartyAgentSkills

# ── Subagents: sync Alfred/agents/*.md into Claude Code + Cursor (bucket-aware) ─
# Canonical subagents live in the repo (agents/). Each agent may declare a
# 'bucket:' in frontmatter (default core); only selected buckets install, matching
# MCP/skill selection. Alfred-Sync.ps1 imports machine-authored agents back here.
function Convert-AgentMdToCodexToml([string]$MdContent) {
    if ($MdContent -notmatch '(?ms)^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$') { return $null }
    $fm = $Matches[1]; $body = $Matches[2].Trim()
    $name = 'agent'
    $desc = 'Alfred subagent'
    $model = $null
    foreach ($line in ($fm -split "`n")) {
        if ($line -match '^\s*name:\s*(.+)$') { $name = $Matches[1].Trim().Trim('"').Trim("'") }
        elseif ($line -match '^\s*description:\s*(.+)$') { $desc = $Matches[1].Trim().Trim('"').Trim("'") }
        elseif ($line -match '^\s*model:\s*(.+)$') { $model = $Matches[1].Trim().Trim('"').Trim("'") }
    }
    if ($desc.Length -gt 500) { $desc = $desc.Substring(0, 497) + '...' }
    $descEsc = $desc -replace '\\', '\\\\' -replace '"', '\"'
    $bodyEsc = $body -replace '\\', '\\\\' -replace '"""', '\"""'
    $lines = @(
        "name = `"$name`"",
        "description = `"$descEsc`""
    )
    if ($model -and $model -ne 'inherit') { $lines += "model = `"$model`"" }
    $lines += ''
    $lines += 'developer_instructions = """'
    $lines += $bodyEsc
    $lines += '"""'
    return ($lines -join "`n") + "`n"
}

function Sync-Agents {
    $src = Join-Path $Root "agents"
    if (-not (Test-Path $src)) { Write-Skip "No agents/ directory -- no subagents to sync."; return }
    $files = @(Get-ChildItem $src -Filter *.md -File -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) { Write-Skip "agents/ is empty."; return }
    # Subagents mirror to Claude Code, Cursor, and Codex (TOML).
    $dests = @((Join-Path $HOME ".claude\agents"), (Join-Path $HOME ".cursor\agents"))
    $codexAgents = Join-Path $HOME ".codex\agents"
    foreach ($d in $dests) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }
    if (-not $SkipCodex) {
        if (-not (Test-Path $codexAgents)) { New-Item -ItemType Directory -Path $codexAgents -Force | Out-Null }
    }
    $expected = [System.Collections.Generic.HashSet[string]]::new()
    $expectedCodex = [System.Collections.Generic.HashSet[string]]::new()
    $synced = 0; $skippedB = 0
    foreach ($f in $files) {
        if ($f.Name -ieq 'README.md') { continue }
        $head = Get-Content $f.FullName -TotalCount 15 -ErrorAction SilentlyContinue
        $bkt = 'core'
        $bl = $head | Where-Object { $_ -match '^\s*bucket:\s*\S' } | Select-Object -First 1
        if ($bl) { $bkt = (($bl -replace '^\s*bucket:\s*', '').Trim().Trim('"').ToLower()) }
        if ($SelectedBuckets -notcontains $bkt) { $skippedB++; continue }
        [void]$expected.Add($f.Name)
        $mdRaw = Get-Content $f.FullName -Raw
        foreach ($d in $dests) { Copy-Item $f.FullName (Join-Path $d $f.Name) -Force }
        if (-not $SkipCodex) {
            $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
            $toml = Convert-AgentMdToCodexToml $mdRaw
            if ($toml) {
                Write-TextNoBom (Join-Path $codexAgents "$base.toml") $toml
                [void]$expectedCodex.Add("$base.toml")
            }
        }
        $synced++
    }
    # prune agents whose bucket was de-selected but a prior sync left them
    foreach ($d in $dests) {
        Get-ChildItem $d -Filter *.md -File -ErrorAction SilentlyContinue | ForEach-Object {
            $repoHas = Test-Path (Join-Path $src $_.Name)
            if ($repoHas -and -not $expected.Contains($_.Name)) { Remove-Item $_.FullName -Force }
        }
    }
    if (-not $SkipCodex -and (Test-Path $codexAgents)) {
        Get-ChildItem $codexAgents -Filter *.toml -File -ErrorAction SilentlyContinue | ForEach-Object {
            $mdName = ($_.BaseName + '.md')
            $repoHas = Test-Path (Join-Path $src $mdName)
            if ($repoHas -and -not $expectedCodex.Contains($_.Name)) { Remove-Item $_.FullName -Force }
        }
    }
    $codexNote = if (-not $SkipCodex) { ", $codexAgents (TOML)" } else { '' }
    Write-OK "Synced $synced subagent(s) -> $($dests -join ', ')$codexNote$(if($skippedB){" (skipped $skippedB in non-selected buckets)"})"
}
Sync-Agents

# ── Rules: per-project seeding ────────────────────────────────────────────────
# Cursor only reads rules from <repo>/.cursor/rules (project scope) or the
# Settings GUI (User Rules). There is NO documented global rules directory, so
# Alfred seeds every repo listed via -ProjectPath / -SeedProjects /
# ALFRED_PROJECT_PATHS (.env, semicolon-separated) instead of writing a global
# ~/.cursor/rules that Cursor never loads.
function Invoke-ProjectSeed([string]$repo) {
    if (-not (Test-Path $repo)) {
        Write-Warn2 "Seed project '$repo' does not exist -- skipping."
        return
    }
    Write-Step "Rules: seeding into $repo"
    if (-not $SkipCursor) {
        $rulesSrc = Join-Path $Root "cursor\rules"
        if (Test-Path $rulesSrc) {
            $rulesDest = Join-Path $repo ".cursor\rules"
            if (-not (Test-Path $rulesDest)) { New-Item -ItemType Directory -Path $rulesDest -Force | Out-Null }
            Copy-Item (Join-Path $rulesSrc '*.mdc') $rulesDest -Force
            Write-OK "Copied Cursor rules -> $rulesDest"
        }
    }
    $agentsSrc  = Join-Path $Root "cursor\AGENTS.shared.md"
    $agentsDest = Join-Path $repo "AGENTS.md"
    if (Test-Path $agentsDest) {
        Write-Skip "AGENTS.md already exists in project -- left untouched."
    } elseif (Test-Path $agentsSrc) {
        Copy-Item $agentsSrc $agentsDest
        Write-OK "Created AGENTS.md (shared rules for Cursor + Claude Code)."
    }
    Sync-AlfredRepoCtxRules -RepoRoot $repo
    # Subagents: Cursor (.cursor/agents) + Claude Code (.claude/agents) parity
    $cursorAgents = Join-Path $repo ".cursor\agents"
    if (Test-Path $cursorAgents) {
        $claudeAgents = Join-Path $repo ".claude\agents"
        if (-not (Test-Path $claudeAgents)) { New-Item -ItemType Directory -Path $claudeAgents -Force | Out-Null }
        $agentFiles = @(Get-ChildItem $cursorAgents -Filter "*.md" -File -ErrorAction SilentlyContinue)
        foreach ($af in $agentFiles) {
            Copy-Item $af.FullName (Join-Path $claudeAgents $af.Name) -Force
        }
        if ($agentFiles.Count -gt 0) {
            Write-OK "Synced $($agentFiles.Count) subagent(s) .cursor/agents -> .claude/agents"
        }
        $syncScript = Join-Path $repo "tools\sync-claude-agents.ps1"
        if (Test-Path $syncScript) {
            try {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $syncScript -RepoRoot $repo 2>&1 | Out-Null
            } catch { Write-Warn2 "sync-claude-agents.ps1 failed: $_" }
        }
    }
    # Graphify: free/local codebase knowledge graph — project-scoped Cursor rule
    # (graphify install writes <cwd>/.cursor/rules/graphify.mdc).
    if (-not $SkipCursor -and (Get-Command graphify -ErrorAction SilentlyContinue)) {
        Push-Location $repo
        try {
            & graphify install --platform cursor 2>&1 | Out-Null
            if (Test-Path (Join-Path $repo ".cursor\rules\graphify.mdc")) {
                Write-OK "Seeded graphify Cursor rule (build the graph with: graphify or /graphify)."
            }
        } catch {
            Write-Warn2 "graphify seed failed: $_"
        } finally {
            Pop-Location
        }
    }
}

# Graphify CLI: install once (uv tool, local/deterministic, no API keys).
if (-not (Get-Command graphify -ErrorAction SilentlyContinue)) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Step "Installing graphify (local knowledge-graph CLI, no API cost)"
        & uv tool install graphifyy -q 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Info $_ }
    } else {
        Write-Skip "graphify not installed and uv unavailable -- install later: uv tool install graphifyy"
    }
}

$seedList = @()
if ($ProjectPath) { $seedList += $ProjectPath }
$seedList += $SeedProjects
$envSeeds = $EnvMap["ALFRED_PROJECT_PATHS"]
if ($envSeeds) { $seedList += ($envSeeds -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
$seedList = @($seedList | Select-Object -Unique)
if ($seedList.Count -gt 0) {
    foreach ($repo in $seedList) { Invoke-ProjectSeed $repo }
} else {
    Write-Info "Rules are per-project. Pass -ProjectPath <repo> or set ALFRED_PROJECT_PATHS in Alfred .env."
}

Sync-AlfredRepoCtxRules -RepoRoot $Root

# ── Impeccable Cursor hook ──
Wire-ImpeccableCursorHook

Write-Step "Removing lean-ctx from agent configs"
if (Get-Command Invoke-RemoveLeanCtxFromMachine -ErrorAction SilentlyContinue) {
    [void](Invoke-RemoveLeanCtxFromMachine -SourceRoot $Root -Project $ProjectPath)
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

# ── Doctor: verify what each assistant actually sees (exit 0 != installed) ────
if (-not $SkipDoctor) {
    $doctorScript = Join-Path $Root "Alfred-Doctor.ps1"
    if (Test-Path $doctorScript) {
        & $doctorScript -SeedProjects $seedList
    }
}

if ($script:ProvisionErrors.Count -gt 0) { exit 1 }
