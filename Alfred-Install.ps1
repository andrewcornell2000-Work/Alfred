#Requires -Version 5.1
<#
.SYNOPSIS
    One-file Alfred bootstrapper. Download this file alone and run it.
.DESCRIPTION
    - Installs Git, Python 3.12, Node.js if missing (via winget)
    - Clones https://github.com/andrewcornell2000-Work/Alfred  (or pulls updates)
    - Creates .venv and installs all Python packages
    - Installs Claude Code and Codex CLIs
    - Prompts for API keys and writes .env
    - Creates a desktop shortcut
    - Idempotent: safe to re-run to update or repair
.PARAMETER InstallPath
    Where to put Alfred. Defaults to %USERPROFILE%\Alfred
.EXAMPLE
    .\Alfred-Install.ps1
    .\Alfred-Install.ps1 -InstallPath "C:\Tools\Alfred"
#>

param(
    [string]$InstallPath = "$env:USERPROFILE\Alfred",
    [string]$RepoUrl    = "https://github.com/andrewcornell2000-Work/Alfred.git",
    [string]$Branch     = "main"
)

$ErrorActionPreference = "Continue"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Banner([string]$Text) {
    Write-Host ""
    Write-Host ("=" * 50) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor Cyan
}
function Write-Step([string]$Msg)  { Write-Host ""; Write-Host $Msg -ForegroundColor Cyan }
function Write-OK([string]$Msg)    { Write-Host "  [OK]     $Msg" -ForegroundColor Green }
function Write-Done([string]$Msg)  { Write-Host "  [DONE]   $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg)  { Write-Host "  [WARN]   $Msg" -ForegroundColor Yellow }
function Write-Fail([string]$Msg)  { Write-Host "  [FAIL]   $Msg" -ForegroundColor Red }
function Write-Info([string]$Msg)  { Write-Host "           $Msg" -ForegroundColor DarkGray }

function Find-Command([string]$Name) {
    return (Get-Command $Name -ErrorAction SilentlyContinue)?.Source
}

function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

function Add-PathEntry([string]$Entry) {
    if (-not $Entry -or -not (Test-Path $Entry)) { return }
    if ($env:PATH -notlike "*$Entry*") { $env:PATH = "$Entry;$env:PATH" }
    $user = [System.Environment]::GetEnvironmentVariable("PATH","User")
    if ($user -notlike "*$Entry*") {
        [System.Environment]::SetEnvironmentVariable("PATH", "$user;$Entry", "User")
    }
}

function Install-Winget([string]$Id, [string]$Name) {
    if (-not (Find-Command "winget")) {
        Write-Warn "winget not available — install $Name manually."
        return $false
    }
    Write-Host "  Installing $Name via winget..." -ForegroundColor Cyan
    winget install --id $Id --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
    return ($LASTEXITCODE -eq 0)
}

# ── Banner ────────────────────────────────────────────────────────────────────

Write-Banner "Alfred Installer"
Write-Host ""
Write-Host "  Install path : $InstallPath" -ForegroundColor White
Write-Host "  Repository   : $RepoUrl" -ForegroundColor White
Write-Host "  Branch       : $Branch" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "  Install / update Alfred here? (Y/n)"
if ($confirm -match "^[Nn]") { Write-Host "Cancelled."; exit 0 }

# ── Step 1: Git ───────────────────────────────────────────────────────────────

Write-Step "Step 1: Git"

if (-not (Find-Command "git")) {
    Write-Warn "Git not found — installing..."
    $ok = Install-Winget "Git.Git" "Git"
    if (-not $ok -or -not (Find-Command "git")) {
        Write-Fail "Git install failed. Install from https://git-scm.com/download/win then re-run."
        exit 2
    }
}
$gitVer = & git --version 2>&1 | Select-Object -First 1
Write-OK "Git — $gitVer"

# ── Step 2: Clone or pull ─────────────────────────────────────────────────────

Write-Step "Step 2: Alfred repository"

if (Test-Path (Join-Path $InstallPath ".git")) {
    Write-OK "Existing checkout found — pulling latest..."
    $dirty = & git -C $InstallPath status --porcelain 2>$null
    if ($dirty) {
        Write-Warn "Local changes detected — committing before pull..."
        & git -C $InstallPath add -A
        & git -C $InstallPath commit -m "Alfred auto-save before update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>$null
    }
    & git -C $InstallPath pull --ff-only origin $Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Pull had conflicts — continuing with local version."
    } else {
        Write-Done "Repository updated."
    }
} elseif (Test-Path $InstallPath) {
    Write-Warn "$InstallPath exists but is not a Git repo — cloning into it may fail."
    & git clone --branch $Branch $RepoUrl $InstallPath
} else {
    Write-Host "  Cloning Alfred..." -ForegroundColor Cyan
    & git clone --branch $Branch $RepoUrl $InstallPath
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Clone failed. Check your network and GitHub access."
        exit 3
    }
    Write-Done "Repository cloned."
}

# ── Step 3: Python ────────────────────────────────────────────────────────────

Write-Step "Step 3: Python"

if (-not (Find-Command "python")) {
    Write-Warn "Python not found — installing Python 3.12..."
    $ok = Install-Winget "Python.Python.3.12" "Python 3.12"
    if (-not $ok) {
        Write-Fail "Python install failed. Install from https://www.python.org/downloads/ (tick 'Add to PATH'), then re-run."
        exit 2
    }
}

$pyVer = & python --version 2>&1 | Select-Object -First 1
Write-OK "Python — $pyVer"

# venv
$VenvPath = Join-Path $InstallPath ".venv"
$PipExe   = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $VenvPath
    Write-Done ".venv created."
} else {
    Write-OK ".venv exists."
}

# Install Python packages
$ReqFile = Join-Path $InstallPath "requirements\python-requirements.txt"
if (Test-Path $PipExe) {
    Write-Host "  Installing Python packages..." -ForegroundColor Cyan
    if (Test-Path $ReqFile) {
        & $PipExe install --quiet -r $ReqFile
    } else {
        & $PipExe install --quiet anthropic openai rich python-dotenv typer
    }
    Write-Done "Python packages installed."
} else {
    Write-Fail "pip not found in .venv — package install skipped."
}

# ── Step 4: Node.js ───────────────────────────────────────────────────────────

Write-Step "Step 4: Node.js"

if (-not (Find-Command "node")) {
    Write-Warn "Node.js not found — installing..."
    $ok = Install-Winget "OpenJS.NodeJS.LTS" "Node.js LTS"
    if (-not $ok) {
        Write-Warn "Node.js install failed. Install from https://nodejs.org/ then re-run."
    }
}

if (Find-Command "node") {
    $nodeVer = & node --version 2>&1 | Select-Object -First 1
    Write-OK "Node.js — $nodeVer"

    # npm global bin on PATH
    $npmGlobal = & npm prefix -g 2>$null | Select-Object -First 1
    if ($npmGlobal) { Add-PathEntry $npmGlobal.Trim() }

    # Claude Code CLI
    if (-not (Find-Command "claude")) {
        Write-Host "  Installing Claude Code CLI..." -ForegroundColor Cyan
        npm install -g @anthropic-ai/claude-code
        if (Find-Command "claude") { Write-Done "Claude Code CLI installed." }
        else { Write-Warn "Claude Code installed but not on PATH yet — open a new terminal." }
    } else {
        Write-OK "Claude Code CLI — $(& claude --version 2>&1 | Select-Object -First 1)"
    }

    # Codex CLI
    if (-not (Find-Command "codex") -and -not (Find-Command "codex.cmd")) {
        Write-Host "  Installing Codex CLI..." -ForegroundColor Cyan
        npm install -g @openai/codex
        Write-Done "Codex CLI installed."
    } else {
        Write-OK "Codex CLI already present."
    }
} else {
    Write-Warn "Node.js not available — Claude Code and Codex CLIs skipped."
}

# ── Step 5: .env (API keys) ───────────────────────────────────────────────────

Write-Step "Step 5: API keys"

$EnvFile = Join-Path $InstallPath ".env"

if (Test-Path $EnvFile) {
    Write-OK ".env found."
} else {
    Write-Warn ".env not found — Alfred needs API keys to run."
    Write-Host ""

    $openaiKey = Read-Host "  Paste your OpenAI API key (sk-...)   [press Enter to skip]"
    $anthropicKey = Read-Host "  Paste your Anthropic API key (sk-ant-) [press Enter to skip]"

    $envContent = "# Alfred API keys — do not commit this file`n"
    if ($openaiKey.Trim()) {
        $envContent += "OPENAI_API_KEY=$($openaiKey.Trim())`n"
        Write-Done "OpenAI key saved."
    } else {
        $envContent += "OPENAI_API_KEY=sk-replace-me`n"
        Write-Warn "OpenAI key skipped — edit .env before running Alfred."
    }
    if ($anthropicKey.Trim()) {
        $envContent += "ANTHROPIC_API_KEY=$($anthropicKey.Trim())`n"
        Write-Done "Anthropic key saved."
    } else {
        $envContent += "ANTHROPIC_API_KEY=sk-ant-replace-me`n"
        Write-Warn "Anthropic key skipped — edit .env before running Alfred."
    }

    Set-Content -Path $EnvFile -Encoding utf8 -Value $envContent
    Write-Done ".env written to $EnvFile"
}

# ── Step 6: Desktop shortcut ──────────────────────────────────────────────────

Write-Step "Step 6: Desktop shortcut"

$Desktop    = [System.Environment]::GetFolderPath("Desktop")
$Shortcut   = Join-Path $Desktop "Alfred.lnk"
$LauncherPs = Join-Path $InstallPath "run-alfred.bat"

if (-not (Test-Path $Shortcut)) {
    try {
        $wsh = New-Object -ComObject WScript.Shell
        $lnk = $wsh.CreateShortcut($Shortcut)
        $lnk.TargetPath       = "cmd.exe"
        $lnk.Arguments        = "/c `"$LauncherPs`""
        $lnk.WorkingDirectory = $InstallPath
        $lnk.Description      = "Alfred AI Assistant"
        $lnk.IconLocation     = "cmd.exe,0"
        $lnk.Save()
        Write-Done "Desktop shortcut created — Alfred.lnk"
    } catch {
        Write-Warn "Could not create desktop shortcut: $_"
    }
} else {
    Write-OK "Desktop shortcut already exists."
}

# ── Step 7: Auth reminders ────────────────────────────────────────────────────

Write-Step "Step 7: One-time logins (if not done yet)"
Write-Host ""
Write-Host "  Run these once in a terminal:" -ForegroundColor White
Write-Host "    claude login    # Authenticate Claude Code with your Anthropic account" -ForegroundColor Yellow
Write-Host "    codex login     # Authenticate Codex with your OpenAI account" -ForegroundColor Yellow

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Banner "Alfred is ready"
Write-Host ""
Write-Host "  Launch: double-click the Alfred shortcut on your desktop" -ForegroundColor Green
Write-Host "  Or run: $LauncherPs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To update Alfred in future: re-run this installer — it will pull" -ForegroundColor DarkGray
Write-Host "  the latest from GitHub and install any new dependencies." -ForegroundColor DarkGray
Write-Host ""
