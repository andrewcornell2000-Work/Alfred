#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for Alfred on a fresh Windows machine.
.DESCRIPTION
    Checks and installs prerequisites, creates the Python venv, installs
    Python packages, auto-installs Claude Code and Codex CLIs via npm,
    writes .env.template, and prints login instructions.
    Safe to re-run at any time — all steps are idempotent.
.OUTPUTS
    Exit 0 — all required components ready; Alfred can start.
    Exit 1 — .env is missing; add API keys then re-run.
    Exit 2 — Python not found; install Python then re-run.
#>

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

# ── helpers ──────────────────────────────────────────────────────────────────

function Find-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return $null }
    return $cmd.Source
}

function Write-Step([string]$Msg) {
    Write-Host ""
    Write-Host $Msg -ForegroundColor Cyan
}

function Write-OK([string]$Msg)   { Write-Host "  [OK]       $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "  [MISSING]  $Msg" -ForegroundColor Yellow }
function Write-Info([string]$Msg) { Write-Host "             $Msg" -ForegroundColor DarkYellow }
function Write-Done([string]$Msg) { Write-Host "  [DONE]     $Msg" -ForegroundColor Green }
function Write-Skip([string]$Msg) { Write-Host "  [SKIP]     $Msg" -ForegroundColor DarkGray }
function Write-Fail([string]$Msg) { Write-Host "  [FAILED]   $Msg" -ForegroundColor Red }

# ── banner ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Alfred -- First-time Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── prerequisites ─────────────────────────────────────────────────────────────

Write-Step "Checking prerequisites..."

# Python
$hasPython = $false
if (Find-Command "python") {
    $pyVer = & python --version 2>&1 | Select-Object -First 1
    Write-OK "Python -- $pyVer"
    $hasPython = $true
} else {
    Write-Warn "Python not found."
    Write-Info "Install Python 3.10+ from https://www.python.org/downloads/"
    Write-Info "IMPORTANT: tick 'Add Python to PATH' during install."
}

# Git
$hasGit = $false
if (Find-Command "git") {
    $gitVer = & git --version 2>&1 | Select-Object -First 1
    Write-OK "Git -- $gitVer"
    $hasGit = $true
} else {
    Write-Warn "Git not found."
    Write-Info "Install Git from https://git-scm.com/download/win"
}

# Node.js + version tracking for MCP check
$hasNode = $false
$nodeVersionMajor = 0
if (Find-Command "node") {
    $nodeVerStr = & node --version 2>&1 | Select-Object -First 1
    Write-OK "Node.js -- $nodeVerStr"
    $hasNode = $true
    $nodeVersionMajor = ($nodeVerStr -replace 'v', '').Split('.')[0] -as [int]
    if ($nodeVersionMajor -lt 18) {
        Write-Warn "Node.js $nodeVerStr is below 18. Claude Code MCP requires Node 18+."
        Write-Info "Upgrade at https://nodejs.org/"
    }
} else {
    Write-Warn "Node.js not found."
    Write-Info "Install Node.js 18+ from https://nodejs.org/"
}

# npm
$hasNpm = $false
if (Find-Command "npm") {
    $npmVer = & npm --version 2>&1 | Select-Object -First 1
    Write-OK "npm -- $npmVer"
    $hasNpm = $true
} else {
    Write-Warn "npm not found (should come bundled with Node.js)."
}

# ── Claude Code CLI ───────────────────────────────────────────────────────────

Write-Step "Claude Code CLI..."

$hasClaude = $false
if ($hasNpm) {
    if (Find-Command "claude") {
        $claudeVer = & claude --version 2>&1 | Select-Object -First 1
        Write-OK "Claude Code CLI -- $claudeVer"
        $hasClaude = $true
    } else {
        Write-Host "  Installing Claude Code CLI (npm install -g @anthropic-ai/claude-code)..." -ForegroundColor Cyan
        npm install -g @anthropic-ai/claude-code
        if ($LASTEXITCODE -eq 0) {
            Write-Done "Claude Code CLI installed."
            $hasClaude = $true
        } else {
            Write-Fail "Claude Code CLI install failed."
            Write-Info "Run manually: npm install -g @anthropic-ai/claude-code"
        }
    }
} else {
    Write-Skip "npm not available -- skipping Claude Code CLI install."
}

# ── Codex CLI ─────────────────────────────────────────────────────────────────

Write-Step "Codex CLI..."

$hasCodex = $false
if ($hasNpm) {
    if (Find-Command "codex") {
        $codexVer = & codex --version 2>&1 | Select-Object -First 1
        Write-OK "Codex CLI -- $codexVer"
        $hasCodex = $true
    } else {
        Write-Host "  Installing Codex CLI (npm install -g @openai/codex)..." -ForegroundColor Cyan
        npm install -g @openai/codex
        if ($LASTEXITCODE -eq 0) {
            Write-Done "Codex CLI installed."
            $hasCodex = $true
        } else {
            Write-Fail "Codex CLI install failed."
            Write-Info "Run manually: npm install -g @openai/codex"
        }
    }
} else {
    Write-Skip "npm not available -- skipping Codex CLI install."
}

# ── MCP prerequisites ─────────────────────────────────────────────────────────

Write-Step "MCP prerequisites..."

if ($hasNode -and ($nodeVersionMajor -ge 18)) {
    Write-OK "Node.js $nodeVersionMajor meets MCP minimum (18+)."
} elseif ($hasNode) {
    Write-Warn "Node.js $nodeVersionMajor is below MCP minimum. Upgrade at https://nodejs.org/"
} else {
    Write-Warn "Node.js required for Claude Code MCP support. Install from https://nodejs.org/"
}

if ($hasClaude) {
    Write-OK "Claude Code CLI available (provides MCP runtime)."
} else {
    Write-Warn "Claude Code CLI missing -- MCP features unavailable until installed."
}

# ── Python virtual environment ────────────────────────────────────────────────

Write-Step "Python virtual environment..."

$VenvPath  = Join-Path $Root ".venv"
$PipExe    = Join-Path $VenvPath "Scripts\pip.exe"

if (-not $hasPython) {
    Write-Skip "Python not found -- skipping venv and package install."
} else {
    if (-not (Test-Path $VenvPath)) {
        Write-Host "  Creating .venv..." -ForegroundColor Cyan
        python -m venv $VenvPath
        if ($LASTEXITCODE -eq 0) {
            Write-Done ".venv created."
        } else {
            Write-Fail "Could not create .venv."
        }
    } else {
        Write-OK ".venv already exists."
    }

    if (Test-Path $PipExe) {
        Write-Host "  Installing Python packages..." -ForegroundColor Cyan
        & $PipExe install --quiet anthropic openai rich python-dotenv typer
        Write-Done "Packages installed: anthropic, openai, rich, python-dotenv, typer"
    } else {
        Write-Fail "pip not found in .venv -- package install skipped."
    }
}

# ── .env / secrets ────────────────────────────────────────────────────────────

Write-Step ".env (API keys)..."

$EnvFile     = Join-Path $Root ".env"
$EnvTemplate = Join-Path $Root ".env.template"

$hasEnv = Test-Path $EnvFile

if ($hasEnv) {
    Write-OK ".env found."
} else {
    Write-Warn ".env not found -- Alfred cannot run without API keys."

    if (-not (Test-Path $EnvTemplate)) {
        Set-Content -Path $EnvTemplate -Encoding utf8 -Value @"
# Copy this file to .env and fill in your keys.
# NEVER commit .env to Git -- it is already in .gitignore.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
"@
        Write-Done ".env.template created."
    } else {
        Write-OK ".env.template already exists."
    }

    Write-Host ""
    Write-Host "  To add your API keys:" -ForegroundColor White
    Write-Host "    Copy-Item .env.template .env" -ForegroundColor Yellow
    Write-Host "    notepad .env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Key sources:" -ForegroundColor White
    Write-Host "    OPENAI_API_KEY    -- https://platform.openai.com/api-keys" -ForegroundColor DarkYellow
    Write-Host "    ANTHROPIC_API_KEY -- https://console.anthropic.com/settings/keys" -ForegroundColor DarkYellow
}

# ── login instructions ────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Authentication (run once per machine)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($hasClaude) {
    Write-Host "  Claude Code login:" -ForegroundColor White
    Write-Host "    claude login" -ForegroundColor Yellow
    Write-Host "  Opens a browser to authenticate with your Anthropic account." -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "  Claude Code CLI not installed -- install it first:" -ForegroundColor Yellow
    Write-Host "    npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
    Write-Host "    claude login" -ForegroundColor Yellow
    Write-Host ""
}

if ($hasCodex) {
    Write-Host "  Codex CLI login:" -ForegroundColor White
    Write-Host "    codex login" -ForegroundColor Yellow
    Write-Host "  Opens a browser to authenticate with your OpenAI account." -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "  Codex CLI not installed -- install it first:" -ForegroundColor Yellow
    Write-Host "    npm install -g @openai/codex" -ForegroundColor Yellow
    Write-Host "    codex login" -ForegroundColor Yellow
    Write-Host ""
}

# ── summary ───────────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$readyToRun = $hasPython -and $hasEnv

if ($hasPython)  { Write-Host "  [x] Python" -ForegroundColor Green }   else { Write-Host "  [ ] Python 3.10+  --  https://www.python.org/downloads/" -ForegroundColor Yellow }
if ($hasGit)     { Write-Host "  [x] Git" -ForegroundColor Green }      else { Write-Host "  [ ] Git           --  https://git-scm.com/download/win" -ForegroundColor Yellow }
if ($hasNode)    { Write-Host "  [x] Node.js" -ForegroundColor Green }  else { Write-Host "  [ ] Node.js 18+   --  https://nodejs.org/" -ForegroundColor Yellow }
if ($hasClaude)  { Write-Host "  [x] Claude Code CLI" -ForegroundColor Green } else { Write-Host "  [ ] Claude Code CLI  --  npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow }
if ($hasCodex)   { Write-Host "  [x] Codex CLI" -ForegroundColor Green }       else { Write-Host "  [ ] Codex CLI        --  npm install -g @openai/codex" -ForegroundColor Yellow }
if ($hasEnv)     { Write-Host "  [x] .env (API keys)" -ForegroundColor Green } else { Write-Host "  [ ] .env             --  copy .env.template to .env and add your keys" -ForegroundColor Yellow }

Write-Host ""

if ($readyToRun) {
    Write-Host "  Alfred is ready to run." -ForegroundColor Green
} else {
    Write-Host "  Fix the items above, then re-run Install-Alfred.bat." -ForegroundColor DarkYellow
}

Write-Host ""

# Exit codes (read by Install-Alfred.bat)
if (-not $hasPython) { exit 2 }
if (-not $hasEnv)    { exit 1 }
exit 0
