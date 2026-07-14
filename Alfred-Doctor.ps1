#Requires -Version 5.1
<#
.SYNOPSIS
    Verify what Cursor, Claude Code, Claude Desktop, and Codex ACTUALLY see —
    per category (MCPs, skills, rules, CLIs, Excel/Power BI stack).
.DESCRIPTION
    "Script exited 0" is not success. This renders the real end-state matrix:
      * MCP servers: expected (from cursor/mcp.json, given this machine's
        secrets/commands) vs registered in each target's config.
      * Skills: exactly one copy in ~/.agents/skills; flags legacy duplicates.
      * Rules: per seeded project, .cursor/rules + AGENTS.md + graphify.
      * CLIs and the Excel / Power BI toolchain.
    Saves the report to %LOCALAPPDATA%\alfred\doctor.json and diffs against the
    previous run so drift (e.g. an app wiping its config) is called out.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Alfred-Doctor.ps1
#>
[CmdletBinding()]
param(
    [string[]]$SeedProjects = @(),
    [switch]$Json
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

function Write-Head([string]$m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }
function Write-Pass([string]$m) { Write-Host "  [PASS]  $m" -ForegroundColor Green }
function Write-Fail([string]$m) { Write-Host "  [FAIL]  $m" -ForegroundColor Red }
function Write-Warn2([string]$m){ Write-Host "  [WARN]  $m" -ForegroundColor Yellow }
function Write-Note([string]$m) { Write-Host "          $m" -ForegroundColor DarkGray }

$report = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    mcp       = [ordered]@{}
    skills    = [ordered]@{}
    rules     = [ordered]@{}
    clis      = [ordered]@{}
    data      = [ordered]@{}
    failures  = @()
    warnings  = @()
}
function Add-Failure([string]$m) { $report.failures += $m; Write-Fail $m }
function Add-Warning([string]$m) { $report.warnings += $m; Write-Warn2 $m }

function Read-DotEnv([string]$path) {
    $map = @{}
    if (Test-Path $path) {
        foreach ($line in Get-Content $path) {
            $t = $line.Trim()
            if ($t -eq '' -or $t.StartsWith('#')) { continue }
            $idx = $t.IndexOf('=')
            if ($idx -lt 1) { continue }
            $map[$t.Substring(0, $idx).Trim()] = $t.Substring($idx + 1).Trim().Trim('"').Trim("'")
        }
    }
    return $map
}
$EnvMap = Read-DotEnv (Join-Path $Root ".env")

function Resolve-Secret([string]$name) {
    if ($EnvMap.ContainsKey($name) -and "$($EnvMap[$name])" -ne '') { return $true }
    foreach ($scope in @("Process", "User", "Machine")) {
        if ([System.Environment]::GetEnvironmentVariable($name, $scope)) { return $true }
    }
    return $false
}

# ── Expected MCP servers (same skip logic as the provisioner) ──────────────────
Write-Head "MCP servers (expected on THIS machine, from cursor/mcp.json)"
$powerBiMcp = ""
$pbiExtRoot = Join-Path $env:USERPROFILE ".vscode\extensions"
if (Test-Path $pbiExtRoot) {
    $hit = Get-ChildItem $pbiExtRoot -Directory -Filter "analysis-services.powerbi-modeling-mcp-*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName "server\powerbi-modeling-mcp.exe" } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($hit) { $powerBiMcp = $hit }
}
$tokens = @{
    '${repoRoot}'   = $Root
    '${userProfile}'= $env:USERPROFILE
    '${dataDir}'    = (Join-Path $Root "data")
    '${memoryDir}'  = (Join-Path $Root "memory")
    '${powerBiMcp}' = $powerBiMcp
    '${financeDir}' = $env:USERPROFILE
}
function Expand-Tok([string]$v) {
    if ($null -eq $v) { return $v }
    foreach ($k in $tokens.Keys) { $v = $v.Replace($k, [string]$tokens[$k]) }
    return $v
}

$expected = @()      # servers that SHOULD be registered here
$notExpected = @()   # servers legitimately skipped (missing secret/command)
$tplPath = Join-Path $Root "cursor\mcp.json"
$retired = @()
if (Test-Path $tplPath) {
    $tpl = Get-Content $tplPath -Raw | ConvertFrom-Json
    if ($tpl.PSObject.Properties.Name -contains '_retiredServers') { $retired = @($tpl._retiredServers) }
    # Selected buckets for THIS machine, matching Provision-Cursor.ps1 precedence
    # (ALFRED_BUCKETS in .env or env var; 'all'; default core,office365,web). 'core' always on.
    $allBuckets = @()
    if ($tpl.PSObject.Properties.Name -contains '_buckets') { $allBuckets = @($tpl._buckets.PSObject.Properties.Name) }
    $bktRaw = ''
    $envFile = Join-Path $Root ".env"
    if (Test-Path $envFile) {
        $m = (Get-Content $envFile | Where-Object { $_ -match '^\s*ALFRED_BUCKETS\s*=' })
        if ($m) { $bktRaw = (($m -split '=',2)[1]) }
    }
    if (-not $bktRaw -and $env:ALFRED_BUCKETS) { $bktRaw = $env:ALFRED_BUCKETS }
    if ($bktRaw -and $bktRaw.ToLower().Trim() -eq 'all') { $selectedBuckets = $allBuckets }
    elseif ($bktRaw) { $selectedBuckets = @($bktRaw -split '[,; ]+' | Where-Object { $_ } | ForEach-Object { $_.ToLower().Trim('"') }) }
    else { $selectedBuckets = $allBuckets }   # no choice recorded -> match provisioner (all)
    $selectedBuckets = @(@($selectedBuckets) + 'core' | Select-Object -Unique)
    foreach ($prop in $tpl.mcpServers.PSObject.Properties) {
        $name = $prop.Name; $def = $prop.Value
        $defKeys = @($def.PSObject.Properties.Name)
        $why = $null
        if ($defKeys -contains '_requiresCommand' -and $def._requiresCommand) {
            if (-not (Get-Command $def._requiresCommand -ErrorAction SilentlyContinue)) {
                if (-not ($defKeys -contains '_fallback' -and $def._fallback)) { $why = "needs '$($def._requiresCommand)' on PATH" }
            }
        }
        if (-not $why -and ($defKeys -contains '_requires')) {
            foreach ($r in @($def._requires)) {
                $names = @($r)
                if ($defKeys -contains '_aliases' -and $def._aliases.PSObject.Properties.Name -contains $r) { $names += @($def._aliases.$r) }
                $found = $false
                foreach ($n in $names) { if (Resolve-Secret $n) { $found = $true; break } }
                if (-not $found) { $why = "missing secret '$r'"; break }
            }
        }
        if (-not $why -and ($defKeys -contains 'command')) {
            $cmd = Expand-Tok ([string]$def.command)
            if ([string]::IsNullOrWhiteSpace($cmd)) { $why = "unresolved command token" }
            elseif ($cmd -match '^[A-Za-z]:\\' -and -not (Test-Path $cmd)) { $why = "command not on this machine: $cmd" }
        }
        if (-not $why) {
            $srvBucket = 'core'; if ($defKeys -contains '_bucket') { $srvBucket = ([string]$def._bucket).ToLower() }
            if ($selectedBuckets -notcontains $srvBucket) { $why = "bucket '$srvBucket' not selected" }
        }
        if ($why) { $notExpected += "$name ($why)" } else { $expected += $name }
    }
}
Write-Note ("expected: " + ($expected -join ', '))
if ($notExpected.Count -gt 0) { Write-Note ("not expected here: " + ($notExpected -join '; ')) }
$report.mcp.expected = $expected
$report.mcp.notExpected = $notExpected

# ── Per-target registration checks ─────────────────────────────────────────────
function Get-JsonServers([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    try {
        $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.mcpServers) { return @($j.mcpServers.PSObject.Properties.Name) }
        return @()
    } catch { return $null }
}

$targets = [ordered]@{}
$targets['cursor (~/.cursor/mcp.json)']           = Get-JsonServers (Join-Path $HOME ".cursor\mcp.json")
$targets['claude-code (~/.claude.json user)']     = Get-JsonServers (Join-Path $HOME ".claude.json")
$targets['claude-desktop (claude_desktop_config)'] = Get-JsonServers (Join-Path $env:APPDATA "Claude\claude_desktop_config.json")
$codexToml = Join-Path $HOME ".codex\config.toml"
if (Test-Path $codexToml) {
    $targets['codex (~/.codex/config.toml)'] = @(
        Select-String -Path $codexToml -Pattern '^\[mcp_servers\.([^.\]]+)\]' -AllMatches |
        ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value.Trim('"') }
    )
} else { $targets['codex (~/.codex/config.toml)'] = $null }

# OAuth-deferred servers live in mcp.json files only, never in claude/codex CLI registries.
$oauthNames = @()
if (Test-Path $tplPath) {
    foreach ($prop in $tpl.mcpServers.PSObject.Properties) {
        if (@($prop.Value.PSObject.Properties.Name) -contains '_oauthOnFirstUse' -and $prop.Value._oauthOnFirstUse) { $oauthNames += $prop.Name }
    }
}

foreach ($t in $targets.Keys) {
    $present = $targets[$t]
    $isCliRegistry = ($t -like 'claude-code*') -or ($t -like 'codex*')
    if ($null -eq $present) {
        Add-Warning "$t : config missing/unreadable"
        $report.mcp[$t] = "missing"
        continue
    }
    $missing = @()
    foreach ($e in $expected) {
        if ($isCliRegistry -and ($oauthNames -contains $e)) { continue }
        if ($present -notcontains $e) { $missing += $e }
    }
    $staleRetired = @($retired | Where-Object { $present -contains $_ })
    $dupes = @($present | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })
    if ($missing.Count -eq 0 -and $staleRetired.Count -eq 0 -and $dupes.Count -eq 0) {
        Write-Pass "$t : $($present.Count) server(s), all expected present, no retired/dupes"
    }
    if ($missing.Count -gt 0) {
        if ($t -like 'claude-desktop*') { Add-Warning "$t : missing $($missing -join ', ') (Desktop app can rewrite this file; re-run provision with apps closed)" }
        else { Add-Failure "$t : missing $($missing -join ', ')" }
    }
    if ($staleRetired.Count -gt 0) { Add-Warning "$t : retired servers still present: $($staleRetired -join ', ')" }
    if ($dupes.Count -gt 0) { Add-Failure "$t : DUPLICATE entries: $($dupes -join ', ')" }
    $report.mcp[$t] = [ordered]@{ present = $present; missing = $missing; retired = $staleRetired; dupes = $dupes }
}

# ── Secret hygiene: no plaintext tokens in any config ──────────────────────────
Write-Head "Secret hygiene (no plaintext tokens in configs)"
$secretScanTargets = @(
    (Join-Path $HOME ".cursor\mcp.json"),
    (Join-Path $HOME ".claude.json"),
    (Join-Path $env:APPDATA "Claude\claude_desktop_config.json"),
    (Join-Path $HOME ".codex\config.toml")
)
# Known live-token prefixes. ${env:...} placeholders are safe by construction.
$secretPatterns = @('ghp_[A-Za-z0-9]{20,}', 'github_pat_[A-Za-z0-9_]{20,}', 'sk-ant-[A-Za-z0-9\-_]{20,}', 'sk-[A-Za-z0-9]{20,}', 'fc-[A-Za-z0-9]{20,}', 'tvly-[A-Za-z0-9]{16,}', 'xox[baprs]-[A-Za-z0-9-]{10,}')
$secretHits = 0
foreach ($cfg in $secretScanTargets) {
    if (-not (Test-Path $cfg)) { continue }
    $raw = Get-Content $cfg -Raw -ErrorAction SilentlyContinue
    if (-not $raw) { continue }
    $hitPrefixes = @()
    foreach ($pat in $secretPatterns) { if ($raw -match $pat) { $hitPrefixes += ($pat -split '\[')[0] } }
    if ($hitPrefixes.Count -gt 0) {
        $secretHits++
        $leaf = Split-Path $cfg -Leaf
        Add-Failure ("PLAINTEXT SECRET in $leaf (prefix " + ($hitPrefixes -join ', ') + ") -- rotate it and move to Alfred .env as an env placeholder")
    }
}
if ($secretHits -eq 0) { Write-Pass "No plaintext tokens found in Cursor/Claude/Codex configs" }
$report.secretLeaks = $secretHits

# ── Skills: one copy, in ~/.agents/skills ──────────────────────────────────────
Write-Head "Skills (single copy in ~/.agents/skills)"
$agentsSkills = Join-Path $HOME ".agents\skills"
# Skill bucket map (same file the provisioner uses) so expected skills track selection.
$skBucketMap = @{}; $skPackMap = @{}; $skDefault = 'core'
$skFile = Join-Path $Root "skills\_buckets.json"
if (Test-Path $skFile) {
    try {
        $sbj = Get-Content $skFile -Raw | ConvertFrom-Json
        if ($sbj.PSObject.Properties.Name -contains '_default') { $skDefault = ([string]$sbj._default).ToLower() }
        if ($sbj.PSObject.Properties.Name -contains 'skills') { foreach ($p in $sbj.skills.PSObject.Properties) { $skBucketMap[$p.Name.ToLower()] = ([string]$p.Value).ToLower() } }
        if ($sbj.PSObject.Properties.Name -contains 'packs')  { foreach ($p in $sbj.packs.PSObject.Properties)  { $skPackMap[$p.Name.ToLower()]  = ([string]$p.Value).ToLower() } }
    } catch {}
}
$expectedSkills = @()
$skillsSrc = Join-Path $Root "skills"
if (Test-Path $skillsSrc) {
    foreach ($f in Get-ChildItem $skillsSrc -Filter *.md -File) {
        $base = ($f.BaseName.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')
        if ($base -like 'taste-*' -or $base -eq 'mcp-routing') { continue }
        $key = ($base -replace '^alfred-',''); $b = $skDefault
        if ($skBucketMap.ContainsKey($key)) { $b = $skBucketMap[$key] }
        if ($selectedBuckets -notcontains $b) { continue }   # not selected on this machine
        if ($base -like 'alfred-*') { $expectedSkills += $base } else { $expectedSkills += "alfred-$base" }
    }
}
$packNames = @()
$packsDir = Join-Path $Root "skills\_packs"
if (Test-Path $packsDir) {
    foreach ($pd in @(Get-ChildItem $packsDir -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') })) {
        $rel = $pd.FullName.Substring($packsDir.Length).TrimStart('\','/'); $pack = ($rel -split '[\\/]')[0]
        $pb = $skDefault; if ($skPackMap.ContainsKey($pack.ToLower())) { $pb = $skPackMap[$pack.ToLower()] }
        if ($selectedBuckets -contains $pb) { $packNames += $pd.Name }
    }
}
$missingSkills = @()
foreach ($s in ($expectedSkills + $packNames)) {
    if (-not (Test-Path (Join-Path $agentsSkills "$s\SKILL.md"))) { $missingSkills += $s }
}
if ($missingSkills.Count -eq 0) {
    Write-Pass "~/.agents/skills has all $($expectedSkills.Count + $packNames.Count) Alfred skills (incl. $($packNames.Count) pack skills)"
} else {
    Add-Failure "~/.agents/skills missing: $($missingSkills -join ', ')"
}
$legacyDupes = @()
foreach ($tool in @('.cursor', '.claude', '.codex')) {
    $r = Join-Path $HOME "$tool\skills"
    if (-not (Test-Path $r)) { continue }
    $hits = @(Get-ChildItem $r -Directory -ErrorAction SilentlyContinue |
              Where-Object { ($_.Name -like 'alfred-*') -or ($packNames -contains $_.Name) })
    if ($hits.Count -gt 0) { $legacyDupes += "$tool ($($hits.Count))" }
}
if ($legacyDupes.Count -eq 0) { Write-Pass "no legacy per-tool duplicates (Cursor would list each copy separately)" }
else { Add-Warning "legacy skill copies remain in: $($legacyDupes -join ', ') -- re-run Provision-Cursor.ps1" }
foreach ($h in @('.cursor', '.claude', '.codex')) {
    $imp = Join-Path $HOME "$h\skills\impeccable\SKILL.md"
    if (-not (Test-Path $imp)) { Add-Warning "impeccable missing from ~$h/skills (per-harness by design)" }
}
$thirdPartyDesign = @('ui-design-brain', 'frontend-design', 'accessibility', 'design-taste-frontend')
$missingDesign = @()
foreach ($d in $thirdPartyDesign) {
    if (-not (Test-Path (Join-Path $agentsSkills "$d\SKILL.md"))) { $missingDesign += $d }
}
if ($missingDesign.Count -eq 0) {
    Write-Pass "design stack skills present in ~/.agents/skills ($($thirdPartyDesign -join ', '))"
} else {
    Add-Warning "~/.agents/skills missing design skills: $($missingDesign -join ', ') -- re-run Provision-Cursor.ps1"
}
$report.skills = [ordered]@{ expected = ($expectedSkills.Count + $packNames.Count); missing = $missingSkills; legacyDupes = $legacyDupes; missingDesign = $missingDesign }

# ── Rules: per seeded project ──────────────────────────────────────────────────
Write-Head "Rules (per-project; Cursor reads <repo>/.cursor/rules only)"
$seeds = @($SeedProjects)
$envSeeds = $EnvMap["ALFRED_PROJECT_PATHS"]
if ($envSeeds) { $seeds += ($envSeeds -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
$seeds += $Root
$seeds = @($seeds | Select-Object -Unique)
foreach ($repo in $seeds) {
    if (-not (Test-Path $repo)) { Add-Warning "seed project not found: $repo"; continue }
    $mdc = @(Get-ChildItem (Join-Path $repo ".cursor\rules") -Filter *.mdc -File -ErrorAction SilentlyContinue)
    $agents = Test-Path (Join-Path $repo "AGENTS.md")
    $graph = Test-Path (Join-Path $repo ".cursor\rules\graphify.mdc")
    $cursorSub = @(Get-ChildItem (Join-Path $repo ".cursor\agents") -Filter "*.md" -File -ErrorAction SilentlyContinue)
    $claudeSub = @(Get-ChildItem (Join-Path $repo ".claude\agents") -Filter "*.md" -File -ErrorAction SilentlyContinue)
    $bits = @()
    $bits += "$($mdc.Count) rule(s)"
    if ($agents) { $bits += "AGENTS.md" }
    if ($graph)  { $bits += "graphify" }
    if ($cursorSub.Count -gt 0) { $bits += "$($cursorSub.Count) cursor subagent(s)" }
    if ($claudeSub.Count -gt 0) { $bits += "$($claudeSub.Count) claude subagent(s)" }
    if ($mdc.Count -gt 0) { Write-Pass "$repo : $($bits -join ' + ')" }
    else { Add-Warning "$repo : no .cursor/rules -- run Provision-Cursor.ps1 (seeds via ALFRED_PROJECT_PATHS)" }
    if ($cursorSub.Count -gt 0 -and $claudeSub.Count -lt $cursorSub.Count) {
        Add-Warning "$repo : .claude/agents out of sync ($($claudeSub.Count)/$($cursorSub.Count)) -- run tools/sync-claude-agents.ps1 or re-provision"
    }
    $betweenSteps = Test-Path (Join-Path $repo ".cursor\skills\between-steps-ux\SKILL.md")
    if ($repo -like '*boostly*' -and -not $betweenSteps) {
        Add-Warning "$repo : missing .cursor/skills/between-steps-ux (Jean Paul async UX)"
    }
    $report.rules[$repo] = [ordered]@{
        mdcCount = $mdc.Count; agentsMd = $agents; graphify = $graph
        cursorSubagents = $cursorSub.Count; claudeSubagents = $claudeSub.Count; betweenStepsUx = $betweenSteps
    }
}

# ── CLIs + data-analysis toolchain ────────────────────────────────────────────
Write-Head "CLIs"
foreach ($cli in @('claude', 'codex', 'node', 'npx', 'uvx', 'git', 'gh', 'jq', 'pandoc', 'graphify')) {
    $found = Get-Command $cli -ErrorAction SilentlyContinue
    if ($found) { Write-Pass "$cli"; $report.clis[$cli] = $true }
    else {
        $report.clis[$cli] = $false
        if ($cli -in @('claude', 'codex', 'node', 'npx', 'git')) { Add-Failure "$cli not on PATH" }
        else { Add-Warning "$cli not on PATH (optional)" }
    }
}

Write-Head "Node TLS trust (corporate proxy / Zscaler)"
# Node uses its own CA bundle, not the Windows store. Behind a re-signing proxy
# that means npx/mcp-remote MCP servers die with UNABLE_TO_GET_ISSUER_CERT_LOCALLY.
# The fix is NODE_EXTRA_CA_CERTS -> a PEM of the Windows roots (Set-AlfredNodeCaCert).
$vendorPattern = "Zscaler|Netskope|Palo Alto|Cisco Umbrella|Forcepoint|Blue Coat|Broadcom|Fortinet|McAfee|Skyhigh|Menlo|Cloudflare Gateway"
$mitmRoots = @()
foreach ($store in @("Cert:\CurrentUser\Root", "Cert:\LocalMachine\Root")) {
    $mitmRoots += Get-ChildItem $store -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -match $vendorPattern }
}
$caPath = [System.Environment]::GetEnvironmentVariable("NODE_EXTRA_CA_CERTS", "User")
$caOk = $caPath -and (Test-Path $caPath)
$report.data.nodeExtraCaCerts = $caOk
if ($caOk) {
    Write-Pass "NODE_EXTRA_CA_CERTS -> $caPath"
} elseif (@($mitmRoots).Count -gt 0) {
    $vendor = ([regex]::Match(@($mitmRoots)[0].Subject, $vendorPattern)).Value
    Add-Warning "Corporate TLS proxy ($vendor) present but NODE_EXTRA_CA_CERTS not set — Node MCP servers (mcp-remote) will fail."
    $common = Join-Path $Root "Alfred-Common.ps1"
    if ((Test-Path $common) -and (Get-Command node -ErrorAction SilentlyContinue)) {
        . $common
        if (Get-Command Set-AlfredNodeCaCert -ErrorAction SilentlyContinue) {
            Write-Note "Repairing: exporting Windows roots and setting NODE_EXTRA_CA_CERTS..."
            if (Set-AlfredNodeCaCert -OnStep { param($m) Write-Note $m }) {
                Write-Pass "NODE_EXTRA_CA_CERTS repaired (restart Cursor/Claude to apply)"
                $report.data.nodeExtraCaCerts = $true
            }
        }
    }
} else {
    Write-Note "No re-signing proxy detected — Node CA override not needed."
}

Write-Head "Excel / Power BI stack"
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $pkgs = & $venvPy -c "
import importlib.metadata as m
missing = []
for p in ['pandas','openpyxl','xlwings','excellm','pbi-cli-tool']:
    try: m.version(p)
    except Exception: missing.append(p)
print(','.join(missing))" 2>$null
    if ([string]::IsNullOrWhiteSpace("$pkgs")) { Write-Pass "venv data stack (pandas, openpyxl, xlwings, excellm, pbi-cli-tool)"; $report.data.venv = $true }
    else { Add-Failure "venv missing packages: $pkgs"; $report.data.venv = "$pkgs" }
} else { Add-Failure ".venv not built -- run setup.ps1"; $report.data.venv = $false }

$excelMcpExe = Join-Path $Root "bin\excel-mcp\mcp-excel.exe"
if (Test-Path $excelMcpExe) { Write-Pass "ExcelMcp server exe (bin\excel-mcp)"; $report.data.excelMcp = $true }
else { Add-Warning "ExcelMcp exe missing (closed-workbook Excel MCP unavailable) -- re-run setup.ps1"; $report.data.excelMcp = $false }

if ($powerBiMcp) { Write-Pass "Power BI Modeling MCP (VS Code extension)"; $report.data.powerBiMcp = $true }
else { Add-Warning "Power BI Modeling MCP extension not found (~/.vscode/extensions)"; $report.data.powerBiMcp = $false }

$excelExe = "C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
if (Test-Path $excelExe) { Write-Pass "Excel desktop app"; $report.data.excel = $true }
else { Add-Warning "Excel not found at the default Office16 path"; $report.data.excel = $false }

$pbiDesktop = @(
    "C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
    (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\PBIDesktopStore.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $pbiDesktop) {
    $store = Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop" -ErrorAction SilentlyContinue
    if ($store) { $pbiDesktop = "store" }
}
if ($pbiDesktop) { Write-Pass "Power BI Desktop"; $report.data.pbiDesktop = $true }
else { Add-Warning "Power BI Desktop not detected (pbi-cli + modeling MCP need it running)"; $report.data.pbiDesktop = $false }

# ── Save + drift vs previous run ───────────────────────────────────────────────
$stateDir = Join-Path $env:LOCALAPPDATA "alfred"
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
$statePath = Join-Path $stateDir "doctor.json"
if (Test-Path $statePath) {
    try {
        $prev = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $prevFails = @($prev.failures)
        $newFails = @($report.failures | Where-Object { $prevFails -notcontains $_ })
        $fixed    = @($prevFails | Where-Object { $report.failures -notcontains $_ })
        if ($newFails.Count -gt 0) { Write-Head "Drift since $($prev.timestamp)"; foreach ($n in $newFails) { Write-Fail "NEW: $n" } }
        if ($fixed.Count -gt 0)    { foreach ($f in $fixed) { Write-Pass "FIXED since last run: $f" } }
    } catch {}
}
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statePath, ($report | ConvertTo-Json -Depth 8), $enc)

Write-Host ""
if ($report.failures.Count -eq 0) {
    Write-Host "Doctor: HEALTHY ($($report.warnings.Count) warning(s)). Report: $statePath" -ForegroundColor Green
} else {
    Write-Host "Doctor: $($report.failures.Count) FAILURE(S), $($report.warnings.Count) warning(s). Report: $statePath" -ForegroundColor Red
}
if ($Json) { $report | ConvertTo-Json -Depth 8 }
if ($report.failures.Count -gt 0) { exit 1 }
exit 0
