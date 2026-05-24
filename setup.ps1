#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for Alfred on a fresh Windows machine.
.DESCRIPTION
    Checks and installs prerequisites (using winget when available), creates the
    Python venv, installs Python packages from requirements/python-requirements.txt,
    installs npm CLI tools from requirements/npm-tools.txt, writes .env.template,
    and prints login instructions.
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

function Refresh-Path {
    # Reload Machine + User PATH into the current process after a winget install.
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

function Add-PathEntry([string]$PathEntry) {
    if ([string]::IsNullOrWhiteSpace($PathEntry) -or -not (Test-Path $PathEntry)) {
        return $false
    }

    $currentParts = @($env:PATH -split ';' | Where-Object { $_ })
    if (-not ($currentParts | Where-Object { $_.TrimEnd('\') -ieq $PathEntry.TrimEnd('\') })) {
        $env:PATH = "$PathEntry;$env:PATH"
    }

    $userPath = [System.Environment]::GetEnvironmentVariable("PATH","User")
    $userParts = @($userPath -split ';' | Where-Object { $_ })
    if (-not ($userParts | Where-Object { $_.TrimEnd('\') -ieq $PathEntry.TrimEnd('\') })) {
        $updatedUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
            $PathEntry
        } else {
            "$userPath;$PathEntry"
        }
        [System.Environment]::SetEnvironmentVariable("PATH", $updatedUserPath, "User")
    }

    return $true
}

function Get-NpmGlobalBin {
    if (-not (Find-Command "npm")) { return $null }
    $prefix = & npm prefix -g 2>$null | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($prefix)) { return $null }
    return $prefix.Trim()
}

function Ensure-NpmGlobalPath {
    $npmGlobalBin = Get-NpmGlobalBin
    if ([string]::IsNullOrWhiteSpace($npmGlobalBin)) { return $null }
    $null = Add-PathEntry $npmGlobalBin
    return $npmGlobalBin
}

function Invoke-WingetInstall([string]$PackageId, [string]$Name) {
    if (-not (Find-Command "winget")) {
        Write-Info "winget not available -- install $Name manually."
        return $false
    }
    Write-Host "  Installing $Name via winget (this may take a moment)..." -ForegroundColor Cyan
    winget install --id $PackageId --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        Refresh-Path
        Write-Done "$Name installed."
        return $true
    }
    Write-Fail "$Name install via winget failed -- install manually."
    return $false
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
Write-Host "  Alfred -- Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── load tool manifests ───────────────────────────────────────────────────────

$NpmToolsFile  = Join-Path $Root "requirements\npm-tools.txt"
$PythonReqFile = Join-Path $Root "requirements\python-requirements.txt"

# Parse npm-tools.txt: "package:command:description" — lines starting with # are comments
$npmToolList = @()
if (Test-Path $NpmToolsFile) {
    Get-Content $NpmToolsFile | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } | ForEach-Object {
        $parts = $_ -split ':', 3
        if ($parts.Count -ge 2) {
            $npmToolList += [PSCustomObject]@{
                Package     = $parts[0].Trim()
                Command     = $parts[1].Trim()
                Description = if ($parts.Count -ge 3) { $parts[2].Trim() } else { $parts[0].Trim() }
            }
        }
    }
}

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
    $null = Invoke-WingetInstall "Python.Python.3.12" "Python 3.12"
    if (Find-Command "python") {
        $pyVer = & python --version 2>&1 | Select-Object -First 1
        Write-OK "Python -- $pyVer"
        $hasPython = $true
    } else {
        Write-Info "Install Python 3.10+ from https://www.python.org/downloads/"
        Write-Info "IMPORTANT: tick 'Add Python to PATH' during install, then re-run."
    }
}

# Git
$hasGit = $false
if (Find-Command "git") {
    $gitVer = & git --version 2>&1 | Select-Object -First 1
    Write-OK "Git -- $gitVer"
    $hasGit = $true
} else {
    Write-Warn "Git not found."
    $null = Invoke-WingetInstall "Git.Git" "Git"
    if (Find-Command "git") {
        $gitVer = & git --version 2>&1 | Select-Object -First 1
        Write-OK "Git -- $gitVer"
        $hasGit = $true
    } else {
        Write-Info "Install Git from https://git-scm.com/download/win"
    }
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
        Write-Info "Upgrade: winget install OpenJS.NodeJS.LTS  or  https://nodejs.org/"
    }
} else {
    Write-Warn "Node.js not found."
    $null = Invoke-WingetInstall "OpenJS.NodeJS.LTS" "Node.js LTS"
    if (Find-Command "node") {
        $nodeVerStr = & node --version 2>&1 | Select-Object -First 1
        Write-OK "Node.js -- $nodeVerStr"
        $hasNode = $true
        $nodeVersionMajor = ($nodeVerStr -replace 'v', '').Split('.')[0] -as [int]
    } else {
        Write-Info "Install Node.js 18+ from https://nodejs.org/"
    }
}

# npm
$hasNpm = $false
if (Find-Command "npm") {
    $npmVer = & npm --version 2>&1 | Select-Object -First 1
    Write-OK "npm -- $npmVer"
    $hasNpm = $true
    $npmGlobalBin = Ensure-NpmGlobalPath
    if ($npmGlobalBin) {
        Write-OK "npm global CLI path -- $npmGlobalBin"
    }
} else {
    Write-Warn "npm not found (should come bundled with Node.js)."
}

# ── npm CLI tools (from requirements/npm-tools.txt) ───────────────────────────

Write-Step "npm CLI tools (requirements/npm-tools.txt)..."

$toolStatus = @{}

if (-not $hasNpm) {
    Write-Skip "npm not available -- skipping all npm tool installs."
    foreach ($tool in $npmToolList) { $toolStatus[$tool.Command] = $false }
} elseif ($npmToolList.Count -eq 0) {
    Write-Skip "requirements/npm-tools.txt is empty or missing -- nothing to install."
} else {
    foreach ($tool in $npmToolList) {
        if (Find-Command $tool.Command) {
            $ver = & $tool.Command --version 2>&1 | Select-Object -First 1
            Write-OK "$($tool.Description) -- $ver"
            $toolStatus[$tool.Command] = $true
        } else {
            Write-Host "  Installing $($tool.Description) (npm install -g $($tool.Package))..." -ForegroundColor Cyan
            npm install -g $tool.Package
            if ($LASTEXITCODE -eq 0) {
                $null = Ensure-NpmGlobalPath
                if (Find-Command $tool.Command) {
                    Write-Done "$($tool.Description) installed."
                    $toolStatus[$tool.Command] = $true
                } else {
                    Write-Fail "$($tool.Description) installed, but '$($tool.Command)' is not on PATH."
                    Write-Info "Open a new terminal or add the npm global folder to PATH."
                    $toolStatus[$tool.Command] = $false
                }
            } else {
                Write-Fail "$($tool.Description) install failed."
                Write-Info "Run manually: npm install -g $($tool.Package)"
                $toolStatus[$tool.Command] = $false
            }
        }
    }
}

# Convenience flags used by login instructions below
$hasClaude = $toolStatus["claude"] -eq $true
$hasCodex  = $toolStatus["codex"]  -eq $true

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

$VenvPath = Join-Path $Root ".venv"
$PipExe   = Join-Path $VenvPath "Scripts\pip.exe"

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
        if (Test-Path $PythonReqFile) {
            Write-Host "  Installing Python packages from requirements/python-requirements.txt..." -ForegroundColor Cyan
            & $PipExe install --quiet -r $PythonReqFile
            Write-Done "Packages installed from requirements/python-requirements.txt"
        } else {
            Write-Host "  Installing Python packages (fallback)..." -ForegroundColor Cyan
            & $PipExe install --quiet anthropic openai rich python-dotenv typer
            Write-Done "Packages installed: anthropic, openai, rich, python-dotenv, typer"
        }
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

if ($hasPython) { Write-Host "  [x] Python"   -ForegroundColor Green  } else { Write-Host "  [ ] Python 3.10+  --  https://www.python.org/downloads/"  -ForegroundColor Yellow }
if ($hasGit)    { Write-Host "  [x] Git"      -ForegroundColor Green  } else { Write-Host "  [ ] Git           --  https://git-scm.com/download/win"    -ForegroundColor Yellow }
if ($hasNode)   { Write-Host "  [x] Node.js"  -ForegroundColor Green  } else { Write-Host "  [ ] Node.js 18+   --  https://nodejs.org/"                 -ForegroundColor Yellow }

foreach ($tool in $npmToolList) {
    $ok = $toolStatus[$tool.Command] -eq $true
    if ($ok) {
        Write-Host "  [x] $($tool.Description)" -ForegroundColor Green
    } else {
        Write-Host "  [ ] $($tool.Description)  --  npm install -g $($tool.Package)" -ForegroundColor Yellow
    }
}

if ($hasEnv) { Write-Host "  [x] .env (API keys)" -ForegroundColor Green } else { Write-Host "  [ ] .env  --  copy .env.template to .env and add your keys" -ForegroundColor Yellow }

Write-Host ""

if ($readyToRun) {
    Write-Host "  Alfred is ready to run." -ForegroundColor Green
} else {
    Write-Host "  Fix the items above, then re-run Install-Alfred.bat." -ForegroundColor DarkYellow
}

Write-Host ""

# Exit codes (read by Install-Alfred.bat and run-alfred.bat)
if (-not $hasPython) { exit 2 }
if (-not $hasEnv)    { exit 1 }
exit 0
