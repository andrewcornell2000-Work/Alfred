#Requires -Version 5.1
<#
.SYNOPSIS
    One-file Alfred bootstrapper. Download this file alone and run it.
.DESCRIPTION
    - Installs Git, Python 3.12, Node.js if missing (via winget)
    - Clones https://github.com/andrewcornell2000-Work/Alfred (or pulls updates)
    - Creates .venv and installs all Python packages
    - Installs Claude Code and Codex CLIs
    - Runs claude login and codex login (browser OAuth - no API keys)
    - Prompts for OpenAI API key and writes .env
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
    [string]$Branch     = "main",
    [string]$QuantUrl   = "https://alfred-production-8fe8.up.railway.app"
)

$ErrorActionPreference = "Continue"

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
    # Check both plain name and .cmd variant (Windows npm installs)
    $found = Get-Command $Name -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $found = Get-Command "$Name.cmd" -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    return $null
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

function Write-EnvVar([string]$EnvPath, [string]$Key, [string]$Value) {
    if (Test-Path $EnvPath) {
        $content = Get-Content $EnvPath -Raw
        if ($content -match "(?m)^$Key=") {
            $content = $content -replace "(?m)^$Key=.*", "$Key=$Value"
        } else {
            $content = $content.TrimEnd() + "`n$Key=$Value`n"
        }
        Set-Content $EnvPath $content -NoNewline
    } else {
        Set-Content $EnvPath "$Key=$Value`n"
    }
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
        Write-Fail "Python install failed. Install from https://www.python.org/downloads/ (tick Add to PATH), then re-run."
        exit 2
    }
}

$pyVer = & python --version 2>&1 | Select-Object -First 1
Write-OK "Python — $pyVer"

$VenvPath = Join-Path $InstallPath ".venv"
$PipExe   = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $VenvPath
    Write-Done ".venv created."
} else {
    Write-OK ".venv exists."
}

$ReqFile = Join-Path $InstallPath "requirements\python-requirements.txt"
if (Test-Path $PipExe) {
    Write-Host "  Installing Python packages..." -ForegroundColor Cyan
    if (Test-Path $ReqFile) {
        & $PipExe install --quiet -r $ReqFile
    } else {
        & $PipExe install --quiet openai rich python-dotenv typer
    }
    Write-Done "Python packages installed."
} else {
    Write-Fail "pip not found in .venv — package install skipped."
}

# ── Step 4: Node.js + CLIs ────────────────────────────────────────────────────

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

    $npmGlobal = & npm prefix -g 2>$null | Select-Object -First 1
    if ($npmGlobal) { Add-PathEntry $npmGlobal.Trim() }

    if (-not (Find-Command "claude")) {
        Write-Host "  Installing Claude Code CLI..." -ForegroundColor Cyan
        npm install -g @anthropic-ai/claude-code
        Refresh-Path
        if (Find-Command "claude") { Write-Done "Claude Code CLI installed." }
        else { Write-Warn "Claude Code installed but not on PATH yet — open a new terminal after install." }
    } else {
        Write-OK "Claude Code CLI already present."
    }

    if (-not (Find-Command "codex")) {
        Write-Host "  Installing Codex CLI..." -ForegroundColor Cyan
        npm install -g @openai/codex
        Refresh-Path
        Write-Done "Codex CLI installed."
    } else {
        Write-OK "Codex CLI already present."
    }
} else {
    Write-Warn "Node.js not available — Claude Code and Codex CLIs skipped."
}

# ── Step 5: Claude login ──────────────────────────────────────────────────────

Write-Step "Step 5: Claude login (Anthropic account)"
Write-Host ""
Write-Host "  Sign in with your Claude / Anthropic account — no API key needed." -ForegroundColor White
Write-Host ""

if (Find-Command "claude") {
    $doLogin = Read-Host "  Run claude login now? (Y/n)"
    if ($doLogin -notmatch "^[Nn]") {
        Write-Host "  Launching claude login..." -ForegroundColor Cyan
        & (Get-Command claude.cmd -ErrorAction SilentlyContinue)?.Source ?? "claude" login
    }
} else {
    Write-Warn "Claude Code CLI not found. Run 'claude login' after opening a new terminal."
}

# ── Step 6: Codex login ───────────────────────────────────────────────────────

Write-Step "Step 6: Codex login (ChatGPT / OpenAI account)"
Write-Host ""
Write-Host "  Sign in with your ChatGPT account — no API key needed." -ForegroundColor White
Write-Host ""

if (Find-Command "codex") {
    $doCodex = Read-Host "  Run codex login now? (Y/n)"
    if ($doCodex -notmatch "^[Nn]") {
        Write-Host "  Launching codex login..." -ForegroundColor Cyan
        & (Get-Command codex.cmd -ErrorAction SilentlyContinue)?.Source ?? "codex" login
    }
} else {
    Write-Warn "Codex CLI not found. Run 'codex login' after opening a new terminal."
}

# ── Step 7: OpenAI API key ────────────────────────────────────────────────────

Write-Step "Step 7: OpenAI API key (for fast chat and classification)"
Write-Host ""
Write-Host "  Alfred uses GPT-4o-mini for quick responses." -ForegroundColor White
Write-Host "  Get a key at: https://platform.openai.com/api-keys" -ForegroundColor DarkGray
Write-Host "  Add a few dollars of credit at: https://platform.openai.com/settings/organization/billing" -ForegroundColor DarkGray
Write-Host ""

$EnvFile = Join-Path $InstallPath ".env"
$existingKey = ""
if (Test-Path $EnvFile) {
    $existingKey = (Get-Content $EnvFile | Where-Object { $_ -match "^OPENAI_API_KEY=" }) -replace "^OPENAI_API_KEY=",""
}

if ($existingKey) {
    Write-OK "OpenAI API key already set in .env."
} else {
    $openBrowser = Read-Host "  Open platform.openai.com/api-keys in browser? (Y/n)"
    if ($openBrowser -notmatch "^[Nn]") {
        Start-Process "https://platform.openai.com/api-keys"
    }
    $apiKey = Read-Host "  Paste your OpenAI API key (sk-...)"
    if ($apiKey -match "^sk-") {
        Write-EnvVar $EnvFile "OPENAI_API_KEY" $apiKey
        Write-Done "API key saved to .env"
    } else {
        Write-Warn "Key not saved — you can add it later by re-running this installer."
    }
}

# Write Quant cloud URL to .env
Write-EnvVar $EnvFile "QUANT_BASE_URL" $QuantUrl
Write-OK "Quant plugin URL set to $QuantUrl"

# ── Step 8: Desktop shortcut ──────────────────────────────────────────────────

Write-Step "Step 8: Desktop shortcut"

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

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Banner "Alfred is ready"
Write-Host ""
Write-Host "  Launch: double-click the Alfred shortcut on your desktop" -ForegroundColor Green
Write-Host "  Or run: $LauncherPs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Quant plugin: $QuantUrl" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To update Alfred in future: re-run this installer." -ForegroundColor DarkGray
Write-Host ""
