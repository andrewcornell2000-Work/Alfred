#Requires -Version 5.1
<#
.SYNOPSIS
    First-time setup for Alfred on a fresh machine.
.DESCRIPTION
    Checks prerequisites, creates the Python venv, installs dependencies,
    and ensures a .env file (or template) is in place.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Check-Command {
    param([string]$Name, [string]$Label, [string]$InstallHint)
    $found = $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
    if ($found) {
        $ver = & $Name --version 2>&1 | Select-Object -First 1
        Write-Host "  [OK] $Label — $ver" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $Label not found." -ForegroundColor Yellow
        Write-Host "            $InstallHint" -ForegroundColor DarkYellow
    }
    return $found
}

Write-Host ""
Write-Host "=== Alfred setup ===" -ForegroundColor Cyan
Write-Host "Checking prerequisites..."
Write-Host ""

# --- Prerequisites ---
$hasPython = Check-Command "python"  "Python 3" "Install from https://www.python.org/downloads/ (add to PATH)"
$hasGit    = Check-Command "git"     "Git"       "Install from https://git-scm.com/download/win"
$hasNode   = Check-Command "node"    "Node.js"   "Install from https://nodejs.org/ or use nvm-windows"
$hasNpm    = Check-Command "npm"     "npm"       "Comes with Node.js"
$hasClaude = Check-Command "claude"  "Claude Code CLI" "npm install -g @anthropic-ai/claude-code"
$hasCodex  = Check-Command "codex"   "Codex CLI" "npm install -g @openai/codex"

Write-Host ""

# --- Python venv ---
$VenvPath = Join-Path $Root ".venv"
if (-not (Test-Path $VenvPath)) {
    if (-not $hasPython) {
        Write-Host "[SKIP] Cannot create .venv — Python not found." -ForegroundColor Yellow
    } else {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
        python -m venv $VenvPath
        Write-Host "  [OK] .venv created." -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] .venv already exists." -ForegroundColor Green
}

# --- Install Python dependencies ---
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
if ((Test-Path $PipExe)) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & $PipExe install --quiet --upgrade anthropic openai rich python-dotenv
    Write-Host "  [OK] anthropic, openai, rich, python-dotenv installed." -ForegroundColor Green
} else {
    Write-Host "[SKIP] pip not found in .venv — skipping dependency install." -ForegroundColor Yellow
}

Write-Host ""

# --- .env check ---
$EnvFile     = Join-Path $Root ".env"
$EnvTemplate = Join-Path $Root ".env.template"

if (Test-Path $EnvFile) {
    Write-Host "  [OK] .env found." -ForegroundColor Green
} else {
    Write-Host "  [MISSING] .env not found." -ForegroundColor Yellow
    if (-not (Test-Path $EnvTemplate)) {
        Set-Content -Path $EnvTemplate -Encoding utf8 -Value @"
# Copy this file to .env and fill in your API keys.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
"@
        Write-Host "  [CREATED] .env.template — copy it to .env and add your keys." -ForegroundColor Cyan
    } else {
        Write-Host "            .env.template already exists — copy it to .env and add your keys." -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan

if (-not (Test-Path $EnvFile)) {
    Write-Host "  1. Copy .env.template to .env and add your API keys:"
    Write-Host "       OPENAI_API_KEY    — https://platform.openai.com/api-keys"
    Write-Host "       ANTHROPIC_API_KEY — https://console.anthropic.com/settings/keys"
}
if (-not $hasClaude) {
    Write-Host "  2. Install Claude Code CLI:  npm install -g @anthropic-ai/claude-code"
    Write-Host "     Then log in:              claude login"
}
if ($hasClaude) {
    Write-Host "  2. If not yet logged in to Claude Code:  claude login"
}
if (-not $hasCodex) {
    Write-Host "  3. Install Codex CLI:  npm install -g @openai/codex"
    Write-Host "     Then log in:        codex login"
}
Write-Host "  4. Run Alfred:  .\run-alfred.bat  (or double-click it)"
Write-Host ""
