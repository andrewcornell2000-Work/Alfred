#Requires -Version 5.1
<#
.SYNOPSIS
    One-file Alfred bootstrapper. Download and run — no admin required if tools already exist.
.DESCRIPTION
    - Checks for Git, Python 3.12, Node.js — installs via winget (admin) or scoop (no admin)
    - Clones https://github.com/andrewcornell2000-Work/Alfred (or pulls updates)
    - Creates .venv and installs all Python packages
    - Installs Claude Code and Codex CLIs (user-level, no admin)
    - Runs claude login and codex login (browser OAuth)
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

function Find-Command([string]$Name) {
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

function Install-Tool([string]$WingetId, [string]$ScoopName, [string]$DisplayName) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        # --scope user avoids UAC — installs to %LOCALAPPDATA% with no admin needed
        Write-Host "  Installing $DisplayName via winget (user scope, no admin)..." -ForegroundColor Cyan
        winget install --id $WingetId --scope user --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if ($LASTEXITCODE -eq 0) { return $true }
        # Some packages only support machine scope — try without --scope as fallback
        winget install --id $WingetId --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if ($LASTEXITCODE -eq 0) { return $true }
    }

    # Fall back to scoop (no admin required)
    Write-Warn "winget unavailable or failed — trying scoop (no admin required)..."
    if (-not (Find-Command "scoop")) {
        Write-Host "  Installing scoop..." -ForegroundColor Cyan
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
        Refresh-Path
    }
    if (Find-Command "scoop") {
        scoop install $ScoopName
        Refresh-Path
        return $true
    }

    Write-Fail "Could not install $DisplayName automatically."
    Write-Host "  Install manually from the web, then re-run this installer." -ForegroundColor Yellow
    return $false
}

function Install-Python-NoAdmin {
    # Downloads the official Python installer and runs it in per-user mode — no admin needed.
    $pyVer = "3.12.9"
    $url   = "https://www.python.org/ftp/python/$pyVer/python-$pyVer-amd64.exe"
    $tmp   = Join-Path $env:TEMP "python-$pyVer-amd64.exe"
    Write-Host "  Downloading Python $pyVer (user install)..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
        $proc = Start-Process $tmp `
            -ArgumentList "/passive InstallAllUsers=0 Include_launcher=0 PrependPath=1" `
            -Wait -PassThru
        Remove-Item $tmp -ErrorAction SilentlyContinue
        Refresh-Path
        if ($proc.ExitCode -eq 0 -and (Find-Command "python")) { return $true }
    } catch {
        Write-Warn "Python direct download failed: $_"
    }
    return $false
}

function Install-Node-Portable([string]$RepoPath) {
    # Downloads the Node.js portable ZIP — no installer, no admin needed.
    # run-alfred.bat already looks for node.exe under $REPO\Node\node-v*-win-x64\
    $nodeVer = "22.13.1"
    try {
        $idx     = Invoke-RestMethod "https://nodejs.org/dist/index.json" -UseBasicParsing
        $lts     = $idx | Where-Object { $_.lts } | Select-Object -First 1
        if ($lts) { $nodeVer = $lts.version.TrimStart('v') }
    } catch {}

    $url       = "https://nodejs.org/dist/v$nodeVer/node-v$nodeVer-win-x64.zip"
    $zip       = Join-Path $env:TEMP "node-$nodeVer.zip"
    $nodeParent = Join-Path $RepoPath "Node"
    Write-Host "  Downloading portable Node.js v$nodeVer..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
        if (Test-Path $nodeParent) { Remove-Item $nodeParent -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Path $nodeParent -Force | Out-Null
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $nodeParent)
        Remove-Item $zip -ErrorAction SilentlyContinue
        # Add the versioned subfolder (e.g. node-v22.13.1-win-x64) to PATH
        $nodeDir = Get-ChildItem $nodeParent -Directory | Select-Object -ExpandProperty FullName -First 1
        if ($nodeDir) { Add-PathEntry $nodeDir }
        Refresh-Path
        return $true
    } catch {
        Write-Warn "Portable Node.js download failed: $_"
        return $false
    }
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
Write-Host "  No admin required — falls back to portable/user installs automatically." -ForegroundColor DarkGray
Write-Host ""

$confirm = Read-Host "  Install / update Alfred here? (Y/n)"
if ($confirm -match "^[Nn]") { Write-Host "Cancelled."; exit 0 }

# ── Step 1: Git ───────────────────────────────────────────────────────────────

Write-Step "Step 1: Git"

if (Find-Command "git") {
    Write-OK "Git — $(& git --version 2>&1 | Select-Object -First 1)"
} else {
    $ok = Install-Tool "Git.Git" "git" "Git"
    if (-not $ok -and -not (Find-Command "git")) {
        Write-Fail "Git is required. Install from https://git-scm.com/download/win then re-run."
        exit 2
    }
}

# ── Step 2: Clone or pull ─────────────────────────────────────────────────────

Write-Step "Step 2: Alfred repository"

if (Test-Path (Join-Path $InstallPath ".git")) {
    Write-OK "Existing checkout found — pulling latest..."
    $dirty = & git -C $InstallPath status --porcelain 2>$null
    if ($dirty) {
        & git -C $InstallPath add -A
        & git -C $InstallPath commit -m "Alfred auto-save before update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>$null
    }
    & git -C $InstallPath pull --ff-only origin $Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Pull had conflicts — continuing with local version."
    } else {
        Write-Done "Repository updated."
    }
} else {
    Write-Host "  Cloning Alfred..." -ForegroundColor Cyan
    & git clone --branch $Branch $RepoUrl $InstallPath
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Clone failed. Check your network connection."
        exit 3
    }
    Write-Done "Repository cloned."
}

# ── Step 3: Python ────────────────────────────────────────────────────────────

Write-Step "Step 3: Python"

if (Find-Command "python") {
    Write-OK "Python — $(& python --version 2>&1 | Select-Object -First 1)"
} else {
    $ok = Install-Tool "Python.Python.3.12" "python" "Python 3.12"
    if (-not $ok -and -not (Find-Command "python")) {
        Write-Warn "winget/scoop failed — trying direct Python download (no admin)..."
        $ok = Install-Python-NoAdmin
    }
    if (-not $ok -and -not (Find-Command "python")) {
        Write-Fail "Python is required. Install from https://www.python.org/downloads/ then re-run."
        exit 2
    }
}

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

if (Find-Command "node") {
    Write-OK "Node.js — $(& node --version 2>&1 | Select-Object -First 1)"
} else {
    $ok = Install-Tool "OpenJS.NodeJS.LTS" "nodejs" "Node.js LTS"
    if (-not $ok -and -not (Find-Command "node")) {
        Write-Warn "winget/scoop failed — downloading portable Node.js (no admin)..."
        Install-Node-Portable $InstallPath | Out-Null
    }
}

if (Find-Command "node") {
    # Add npm global dir to PATH (user-level, no admin)
    $npmGlobal = & npm prefix -g 2>$null | Select-Object -First 1
    if ($npmGlobal) { Add-PathEntry $npmGlobal.Trim() }

    if (-not (Find-Command "claude")) {
        Write-Host "  Installing Claude Code CLI (user-level)..." -ForegroundColor Cyan
        npm install -g @anthropic-ai/claude-code
        Refresh-Path
        if (Find-Command "claude") { Write-Done "Claude Code CLI installed." }
        else { Write-Warn "Claude Code CLI installed — open a new terminal if it is not found." }
    } else {
        Write-OK "Claude Code CLI already present."
    }

    if (-not (Find-Command "codex")) {
        Write-Host "  Installing Codex CLI (user-level)..." -ForegroundColor Cyan
        npm install -g @openai/codex
        Refresh-Path
        Write-Done "Codex CLI installed."
    } else {
        Write-OK "Codex CLI already present."
    }
} else {
    Write-Warn "Node.js not found — Claude Code and Codex CLIs skipped. Re-run after installing Node.js."
}

# ── Step 5: Claude login ──────────────────────────────────────────────────────

Write-Step "Step 5: Claude login (Anthropic account — browser, no API key)"
Write-Host ""

# Find claude.cmd by PATH or directly in npm global bin
$npmPrefix = & npm prefix -g 2>$null | Select-Object -First 1
$claudeExe = $null
if ($npmPrefix) {
    $candidate = Join-Path $npmPrefix.Trim() "claude.cmd"
    if (Test-Path $candidate) { $claudeExe = $candidate }
}
if (-not $claudeExe) {
    $claudeCmd = Get-Command claude.cmd -ErrorAction SilentlyContinue
    if (-not $claudeCmd) { $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue }
    if ($claudeCmd) { $claudeExe = $claudeCmd.Source }
}

if ($claudeExe) {
    $doLogin = Read-Host "  Run claude login now? (Y/n)"
    if ($doLogin -notmatch "^[Nn]") {
        Write-Host "  Opening a new terminal for Claude authentication..." -ForegroundColor Cyan
        Write-Host "  Sign in via the browser that opens, then close the new window." -ForegroundColor DarkGray
        Start-Process "cmd.exe" -ArgumentList "/k `"$claudeExe`""
        Read-Host "  Press Enter here once you have finished authenticating"
    }
} else {
    Write-Warn "Claude Code CLI not found on PATH. Open a new terminal and run 'claude' to authenticate."
}

# ── Step 6: Codex login ───────────────────────────────────────────────────────

Write-Step "Step 6: Codex login (ChatGPT account — browser, no API key)"
Write-Host ""

$codexExe = $null
if ($npmPrefix) {
    $candidate = Join-Path $npmPrefix.Trim() "codex.cmd"
    if (Test-Path $candidate) { $codexExe = $candidate }
}
if (-not $codexExe) {
    $codexCmd = Get-Command codex.cmd -ErrorAction SilentlyContinue
    if (-not $codexCmd) { $codexCmd = Get-Command codex -ErrorAction SilentlyContinue }
    if ($codexCmd) { $codexExe = $codexCmd.Source }
}

if ($codexExe) {
    $doCodex = Read-Host "  Run codex login now? (Y/n)"
    if ($doCodex -notmatch "^[Nn]") {
        & $codexExe login
    }
} else {
    Write-Warn "Codex CLI not found on PATH. Run 'codex login' after opening a new terminal."
}

# ── Step 7: OpenAI API key ────────────────────────────────────────────────────

Write-Step "Step 7: OpenAI API key (for fast chat and classification)"
Write-Host ""
Write-Host "  Alfred uses GPT-4o-mini for quick responses." -ForegroundColor White
Write-Host "  Get a key: https://platform.openai.com/api-keys" -ForegroundColor DarkGray
Write-Host "  Add credit: https://platform.openai.com/settings/organization/billing" -ForegroundColor DarkGray
Write-Host ""

$EnvFile = Join-Path $InstallPath ".env"
$existingKey = ""
if (Test-Path $EnvFile) {
    $existingKey = (Get-Content $EnvFile | Where-Object { $_ -match "^OPENAI_API_KEY=" }) -replace "^OPENAI_API_KEY=",""
}

if ($existingKey) {
    Write-OK "OpenAI API key already saved."
} else {
    $openBrowser = Read-Host "  Open platform.openai.com/api-keys in browser? (Y/n)"
    if ($openBrowser -notmatch "^[Nn]") { Start-Process "https://platform.openai.com/api-keys" }
    $apiKey = Read-Host "  Paste your OpenAI API key (sk-...)"
    if ($apiKey -match "^sk-") {
        Write-EnvVar $EnvFile "OPENAI_API_KEY" $apiKey
        Write-Done "API key saved to .env"
    } else {
        Write-Warn "Key not saved — re-run this installer to add it later."
    }
}

Write-EnvVar $EnvFile "QUANT_BASE_URL" $QuantUrl
Write-OK "Quant plugin URL configured."

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
Write-Host "  Launch: double-click Alfred on your desktop" -ForegroundColor Green
Write-Host "  Or run: $LauncherPs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Quant plugin running at: $QuantUrl" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To update Alfred in future: re-run this installer." -ForegroundColor DarkGray
Write-Host ""
