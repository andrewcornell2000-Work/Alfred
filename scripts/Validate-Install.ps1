#Requires -Version 5.1
<#
.SYNOPSIS
    Post-install validation for Alfred global capability provisioning.
.DESCRIPTION
    Verifies user-scope configs, skill sync, and MCP template validity.
    Exit 0 = all critical checks passed; 1 = one or more failures.
.PARAMETER AlfredRoot
    Alfred repository root (default: script parent directory).
.PARAMETER LogFile
    Append results to this log file.
#>
param(
    [string]$AlfredRoot = (Split-Path $PSScriptRoot -Parent),
    [string]$LogFile = ""
)

$ErrorActionPreference = "Continue"
$failures = @()
$warnings = @()
$passed = @()

function Write-Check([string]$Status, [string]$Msg) {
    switch ($Status) {
        "OK"   { $script:passed += $Msg; Write-Host "  [OK]   $Msg" -ForegroundColor Green }
        "WARN" { $script:warnings += $Msg; Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
        "FAIL" { $script:failures += $Msg; Write-Host "  [FAIL] $Msg" -ForegroundColor Red }
    }
    if ($LogFile) {
        "$(Get-Date -Format o) [$Status] $Msg" | Add-Content -Path $LogFile -Encoding UTF8
    }
}

function Test-JsonFile([string]$Path) {
    if (-not (Test-Path $Path)) { return $false }
    try {
        Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
        return $true
    } catch { return $false }
}

Write-Host ""
Write-Host "Alfred install validation" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# ── Repo ──────────────────────────────────────────────────────────────────────
if (Test-Path (Join-Path $AlfredRoot "Provision-Cursor.ps1")) {
    Write-Check "OK" "Alfred repo: $AlfredRoot"
} else {
    Write-Check "FAIL" "Provision-Cursor.ps1 not found under $AlfredRoot"
}

if (Test-JsonFile (Join-Path $AlfredRoot "cursor\mcp.json")) {
    Write-Check "OK" "MCP template (cursor/mcp.json) is valid JSON"
} else {
    Write-Check "FAIL" "cursor/mcp.json missing or invalid JSON"
}

$skillCount = @(Get-ChildItem (Join-Path $AlfredRoot "skills\*.md") -ErrorAction SilentlyContinue).Count
if ($skillCount -gt 0) {
    Write-Check "OK" "Source skills: $skillCount top-level .md files"
} else {
    Write-Check "WARN" "No top-level skills/*.md found in repo"
}

# ── Cursor ────────────────────────────────────────────────────────────────────
$cursorMcp = Join-Path $env:USERPROFILE ".cursor\mcp.json"
$cursorSkills = Join-Path $env:USERPROFILE ".cursor\skills"
$cursorRules = Join-Path $env:USERPROFILE ".cursor\rules"

if (Test-JsonFile $cursorMcp) {
    $mcp = Get-Content $cursorMcp -Raw | ConvertFrom-Json
    $n = @($mcp.mcpServers.PSObject.Properties.Name).Count
    Write-Check "OK" "Cursor MCP config: $n server(s) in ~/.cursor/mcp.json"
} else {
    Write-Check "WARN" "Cursor MCP config not found (~/.cursor/mcp.json) — Cursor may not be provisioned yet"
}

if (Test-Path $cursorSkills) {
    $alfredSkills = @(Get-ChildItem $cursorSkills -Directory -Filter "alfred-*" -ErrorAction SilentlyContinue).Count
    if ($alfredSkills -gt 0) {
        Write-Check "OK" "Cursor skills: $alfredSkills alfred-* folder(s) in ~/.cursor/skills"
    } else {
        Write-Check "WARN" "Cursor skills dir exists but no alfred-* skills found"
    }
} else {
    Write-Check "WARN" "Cursor skills directory missing (~/.cursor/skills)"
}

if (Test-Path $cursorRules) {
    $rules = @(Get-ChildItem $cursorRules -Filter "*.mdc" -ErrorAction SilentlyContinue).Count
    if ($rules -gt 0) {
        Write-Check "OK" "Cursor global rules: $rules .mdc file(s) in ~/.cursor/rules"
    } else {
        Write-Check "WARN" "Cursor rules directory empty"
    }
} else {
    Write-Check "WARN" "Cursor global rules not provisioned (~/.cursor/rules)"
}

# ── Claude Code ───────────────────────────────────────────────────────────────
$claudeSkills = Join-Path $env:USERPROFILE ".claude\skills"
$claudeJson = Join-Path $env:USERPROFILE ".claude.json"

if (Test-Path $claudeSkills) {
    $n = @(Get-ChildItem $claudeSkills -Recurse -Filter "SKILL.md" -ErrorAction SilentlyContinue).Count
    Write-Check "OK" "Claude Code skills: $n SKILL.md file(s) under ~/.claude/skills"
} else {
    Write-Check "WARN" "Claude Code skills not synced (~/.claude/skills)"
}

if (Test-JsonFile $claudeJson) {
    Write-Check "OK" "Claude user config present (~/.claude.json)"
} elseif (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Check "WARN" "~/.claude.json not found — run Provision-Cursor.ps1"
} else {
    Write-Check "WARN" "Claude Code CLI not on PATH — MCP registration skipped"
}

# ── Claude Desktop ────────────────────────────────────────────────────────────
$desktopCfg = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
if (Test-JsonFile $desktopCfg) {
    Write-Check "OK" "Claude Desktop config present"
} else {
    Write-Check "WARN" "Claude Desktop config not found (optional if you don't use Desktop)"
}

# ── Codex ─────────────────────────────────────────────────────────────────────
$codexSkills = Join-Path $env:USERPROFILE ".codex\skills"
if (Test-Path $codexSkills) {
    $n = @(Get-ChildItem $codexSkills -Recurse -Filter "SKILL.md" -ErrorAction SilentlyContinue).Count
    Write-Check "OK" "Codex skills: $n SKILL.md file(s) under ~/.codex/skills"
} else {
    Write-Check "WARN" "Codex skills not synced (~/.codex/skills)"
}

# ── Catalog integrity ─────────────────────────────────────────────────────────
$validatePy = Join-Path $AlfredRoot ".github\scripts\validate_catalog.py"
if (Test-Path $validatePy) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if ($py) {
        & $py.Source $validatePy 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        if ($LASTEXITCODE -eq 0) { Write-Check "OK" "Catalog dedup validation passed" }
        else { Write-Check "FAIL" "Catalog validation failed (validate_catalog.py)" }
    } else {
        Write-Check "WARN" "Python not on PATH — skipped validate_catalog.py"
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Passed : $($passed.Count)" -ForegroundColor Green
Write-Host "  Warnings: $($warnings.Count)" -ForegroundColor Yellow
Write-Host "  Failed : $($failures.Count)" -ForegroundColor $(if ($failures.Count) { "Red" } else { "Green" })
Write-Host ""

if ($failures.Count -gt 0) {
    Write-Host "  Validation FAILED — re-run Provision-Cursor.ps1 or Alfred-Install.exe" -ForegroundColor Red
    exit 1
}

if ($warnings.Count -gt 0) {
    Write-Host "  Validation passed with warnings (optional targets may be missing)." -ForegroundColor Yellow
} else {
    Write-Host "  Validation passed — capabilities are available to supported AI tools." -ForegroundColor Green
}
exit 0
