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
    - Prompts for Tavily API key and writes .env
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

function Write-CommandOutput {
    process {
        if ($null -ne $_ -and "$_".Trim()) {
            Write-Host "  $_" -ForegroundColor DarkGray
        }
    }
}

function Invoke-PipInstall([string[]]$Packages) {
    & $PipExe install --quiet --disable-pip-version-check @Packages
}

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
    & git -C $InstallPath pull --ff-only origin $Branch 2>&1 | Write-CommandOutput
    $pullExitCode = $LASTEXITCODE
    if ($pullExitCode -ne 0) {
        Write-Warn "Pull had conflicts — continuing with local version."
    } else {
        Write-Done "Repository updated."
    }
} else {
    Write-Host "  Cloning Alfred..." -ForegroundColor Cyan
    & git clone --branch $Branch $RepoUrl $InstallPath 2>&1 | Write-CommandOutput
    $cloneExitCode = $LASTEXITCODE
    if ($cloneExitCode -ne 0) {
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
        $failedPythonPackages = @()
        Get-Content $ReqFile | ForEach-Object {
            $pkg = $_.Trim()
            if ($pkg -and -not $pkg.StartsWith("#")) {
                Invoke-PipInstall @($pkg)
                if ($LASTEXITCODE -ne 0) { $failedPythonPackages += $pkg }
            }
        }
        if ($failedPythonPackages.Count -gt 0) {
            Write-Warn "Some optional Python packages failed: $($failedPythonPackages -join ', ')"
            Write-Host "  Alfred will continue; repair affected specialist features from Control Tower." -ForegroundColor DarkGray
        }
    } else {
        Invoke-PipInstall @("openai", "rich", "python-dotenv", "typer")
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
        Write-Host "  Opening a new terminal for Codex authentication..." -ForegroundColor Cyan
        Write-Host "  Sign in via the browser that opens, then close the new window." -ForegroundColor DarkGray
        Start-Process "cmd.exe" -ArgumentList "/k `"$codexExe`""
        Read-Host "  Press Enter here once you have finished authenticating"
    }
} else {
    Write-Warn "Codex CLI not found on PATH. Run 'codex login' after opening a new terminal."
}

# ── Step 7: Tavily API key (live web research) ────────────────────────────────

Write-Step "Step 7: Tavily API key (live web research)"
Write-Host ""
Write-Host "  Alfred uses Tavily to fetch current docs, news, prices, and live information." -ForegroundColor White
Write-Host "  Free plan: 1,000 queries/month. Get a key: https://app.tavily.com" -ForegroundColor DarkGray
Write-Host ""

$EnvFile = Join-Path $InstallPath ".env"
$tavilyKey = ""
$existingTavily = ""
if (Test-Path $EnvFile) {
    $existingTavily = (Get-Content $EnvFile | Where-Object { $_ -match "^TAVILY_API_KEY=" }) -replace "^TAVILY_API_KEY=",""
}
if ($existingTavily) {
    $tavilyKey = $existingTavily
    Write-OK "Tavily API key already saved."
} else {
    $openTavily = Read-Host "  Open app.tavily.com in browser? (Y/n)"
    if ($openTavily -notmatch "^[Nn]") { Start-Process "https://app.tavily.com" }
    $secureInput = Read-Host "  Paste your Tavily API key (tvly-... or press Enter to skip)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureInput)
    try { $tavilyKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($tavilyKey -match "^tvly-") {
        Write-EnvVar $EnvFile "TAVILY_API_KEY" $tavilyKey
        Write-Done "Tavily API key saved to .env"
    } else {
        Write-Warn "Tavily key not saved — web research will be skipped until added."
        $tavilyKey = ""
    }
}

Write-EnvVar $EnvFile "QUANT_BASE_URL" $QuantUrl
Write-OK "Quant plugin URL configured."

# ── Step 7b: Anthropic API Key (10x faster responses) ────────────────────────

Write-Step "Step 7b: Anthropic API Key (recommended — makes Alfred 10x faster)"
Write-Host ""
Write-Host "  Without this key Alfred uses the Claude CLI subprocess (~10-20s per response)." -ForegroundColor White
Write-Host "  With this key Alfred calls the Anthropic API directly (~1-2s per response)." -ForegroundColor White
Write-Host "  Get a key: https://console.anthropic.com/settings/keys" -ForegroundColor DarkGray
Write-Host ""

$anthropicKey = ""
$existingAnthropic = ""
if (Test-Path $EnvFile) {
    $existingAnthropic = (Get-Content $EnvFile | Where-Object { $_ -match "^ANTHROPIC_API_KEY=" }) -replace "^ANTHROPIC_API_KEY=",""
}
if ($existingAnthropic) {
    $anthropicKey = $existingAnthropic
    Write-OK "Anthropic API key already saved — fast response mode active."
} else {
    $openAnthropic = Read-Host "  Open console.anthropic.com in browser? (Y/n)"
    if ($openAnthropic -notmatch "^[Nn]") { Start-Process "https://console.anthropic.com/settings/keys" }
    $secureInput = Read-Host "  Paste your Anthropic API key (sk-ant-... or press Enter to skip)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureInput)
    try { $anthropicKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($anthropicKey -match "^sk-ant-") {
        Write-EnvVar $EnvFile "ANTHROPIC_API_KEY" $anthropicKey
        Write-Done "Anthropic API key saved — fast response mode enabled."
    } else {
        Write-Warn "Anthropic key skipped — Alfred will use Claude CLI (slower). Add later by re-running installer."
        $anthropicKey = ""
    }
}

# ── Step 7c: GitHub Personal Access Token ────────────────────────────────────

Write-Step "Step 7c: GitHub Personal Access Token (create PRs, manage issues, search repos)"
Write-Host ""
Write-Host "  Alfred uses GitHub MCP to manage repositories directly from chat." -ForegroundColor White
Write-Host "  Create a token (classic): https://github.com/settings/tokens/new" -ForegroundColor DarkGray
Write-Host "  Recommended scopes: repo, read:org, workflow" -ForegroundColor DarkGray
Write-Host ""

$githubToken = ""
$existingGithub = ""
if (Test-Path $EnvFile) {
    $existingGithub = (Get-Content $EnvFile | Where-Object { $_ -match "^GITHUB_TOKEN=" }) -replace "^GITHUB_TOKEN=",""
}
if ($existingGithub) {
    $githubToken = $existingGithub
    Write-OK "GitHub token already saved."
} else {
    $openGithub = Read-Host "  Open github.com/settings/tokens in browser? (Y/n)"
    if ($openGithub -notmatch "^[Nn]") { Start-Process "https://github.com/settings/tokens/new" }
    $secureInput = Read-Host "  Paste your GitHub Personal Access Token (ghp_... or press Enter to skip)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureInput)
    try { $githubToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($githubToken) {
        Write-EnvVar $EnvFile "GITHUB_TOKEN" $githubToken
        Write-Done "GitHub token saved to .env"
    } else {
        Write-Warn "GitHub token skipped — GitHub MCP will not be configured."
    }
}

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

# ── Step 9: MCP Tools ────────────────────────────────────────────────────────

Write-Step "Step 9: MCP Tools (Power BI + Excel)"

$ClaudeSettingsDir = Join-Path $InstallPath ".claude"
New-Item -ItemType Directory -Path $ClaudeSettingsDir -Force | Out-Null

$mcpServers = [ordered]@{}

# ── Power BI Modeling MCP ─────────────────────────────────────────────────────
# Requires VS Code + the analysis-services.powerbi-modeling-mcp extension.
# Alfred auto-installs the extension if VS Code is present.

$vscodeCLI = Find-Command "code"
if (-not $vscodeCLI) {
    foreach ($cand in @(
        "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd",
        "$env:ProgramFiles\Microsoft VS Code\bin\code.cmd",
        "${env:ProgramFiles(x86)}\Microsoft VS Code\bin\code.cmd"
    )) {
        if (Test-Path $cand) { $vscodeCLI = $cand; break }
    }
}

if (-not $vscodeCLI) {
    Write-Warn "VS Code not found — required for Power BI MCP."
    $installVSCode = Read-Host "  Install VS Code now (user install, no admin)? (Y/n)"
    if ($installVSCode -notmatch "^[Nn]") {
        Install-Tool "Microsoft.VisualStudioCode" "vscode" "VS Code" | Out-Null
        Refresh-Path
        foreach ($cand in @(
            "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd",
            "$env:ProgramFiles\Microsoft VS Code\bin\code.cmd"
        )) {
            if (Test-Path $cand) { $vscodeCLI = $cand; break }
        }
        if (-not $vscodeCLI) { $vscodeCLI = Find-Command "code" }
    }
}

if ($vscodeCLI) {
    Write-OK "VS Code — $vscodeCLI"

    # Look for extension; auto-install if missing
    $pbimcpExt = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" `
        -Filter "analysis-services.powerbi-modeling-mcp*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1

    if (-not $pbimcpExt) {
        Write-Host "  Installing Power BI Modeling MCP extension..." -ForegroundColor Cyan
        & $vscodeCLI --install-extension analysis-services.powerbi-modeling-mcp --force 2>$null
        Start-Sleep -Seconds 5
        $pbimcpExt = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" `
            -Filter "analysis-services.powerbi-modeling-mcp*" -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | Select-Object -First 1
    }

    if ($pbimcpExt) {
        $pbimcpExe = Join-Path $pbimcpExt.FullName "server\powerbi-modeling-mcp.exe"
        if (Test-Path $pbimcpExe) {
            $mcpServers["powerbi-modeling-mcp"] = [ordered]@{
                command = $pbimcpExe
                args    = @("--start")
            }
            Write-OK "Power BI Modeling MCP — $($pbimcpExt.Name)"
        } else {
            Write-Warn "Power BI MCP extension found but server exe missing: $pbimcpExe"
            Write-Host "  Try re-installing: VS Code > Extensions > analysis-services.powerbi-modeling-mcp > Uninstall then Install" -ForegroundColor DarkGray
        }
    } else {
        Write-Warn "Power BI MCP extension could not be installed automatically."
        Write-Host "  Install manually in VS Code: Extensions > Search 'powerbi-modeling-mcp' > Install" -ForegroundColor DarkGray
    }
} else {
    Write-Warn "VS Code not installed — Power BI MCP skipped."
    Write-Host "  Install VS Code from https://code.visualstudio.com then re-run this installer." -ForegroundColor DarkGray
}

# ── Excel Live MCP ────────────────────────────────────────────────────────────
# excellm must run from the venv Python so it can import the installed package.
# Using system Python would fail if excellm is only in the venv.

$venvPython = Join-Path $InstallPath ".venv\Scripts\python.exe"
$pyForMcp = if (Test-Path $venvPython) { $venvPython } else { "python" }

$excellmOk = $false
try {
    & $pyForMcp -c "import excellm" 2>$null | Out-Null
    $excellmOk = ($LASTEXITCODE -eq 0)
} catch {}

if (-not $excellmOk) {
    Write-Host "  Installing excellm into venv..." -ForegroundColor Cyan
    Invoke-PipInstall @("excellm") 2>$null
    try {
        & $pyForMcp -c "import excellm" 2>$null | Out-Null
        $excellmOk = ($LASTEXITCODE -eq 0)
    } catch {}
}

if ($excellmOk) {
    $mcpServers["excel"] = [ordered]@{
        command = $pyForMcp
        args    = @("-m", "excellm")
    }
    Write-OK "Excel MCP (excellm) ready — using $pyForMcp"
} else {
    Write-Warn "excellm install failed — Excel MCP skipped."
    Write-Host "  Activate .venv and run: pip install excellm" -ForegroundColor DarkGray
}

# ── Tavily (direct API — no MCP server needed) ────────────────────────────────
# Alfred calls Tavily directly from Python using the key stored in .env.
# No MCP server entry required.

if ($tavilyKey) {
    Write-OK "Tavily web research enabled — key stored in .env"
} else {
    Write-Warn "Tavily key missing — web research unavailable. Re-run installer to add it."
}

# ── GitHub MCP ────────────────────────────────────────────────────────────────

if ($githubToken) {
    $mcpServers["github"] = [ordered]@{
        command = "npx"
        args    = @("-y", "@modelcontextprotocol/server-github")
        env     = [ordered]@{ GITHUB_PERSONAL_ACCESS_TOKEN = $githubToken }
    }
    Write-OK "GitHub MCP configured — PR creation, issue management, repo search enabled."
} else {
    Write-Warn "GitHub MCP skipped (no token). Re-run installer to add it."
}

# ── Playwright MCP ────────────────────────────────────────────────────────────

if (Find-Command "npx") {
    $mcpServers["playwright"] = [ordered]@{
        command = "npx"
        args    = @("-y", "@playwright/mcp", "--browser", "chromium")
    }
    Write-OK "Playwright MCP configured — browser automation enabled."
} else {
    Write-Warn "Playwright MCP skipped (npx not found — install Node.js first)."
}

# ── Write settings.json ───────────────────────────────────────────────────────

if ($mcpServers.Count -gt 0) {
    $settingsObj = [ordered]@{ mcpServers = $mcpServers }
    $settingsJson = $settingsObj | ConvertTo-Json -Depth 5
    $settingsPath = Join-Path $ClaudeSettingsDir "settings.json"
    Set-Content $settingsPath $settingsJson -Encoding UTF8
    Write-Done ".claude\settings.json written with $($mcpServers.Count) MCP server(s)."
    Write-Host "  Power BI:   edit measures, tables, relationships, DAX" -ForegroundColor DarkGray
    Write-Host "  Excel:      read/write cells, charts, pivot tables, VBA" -ForegroundColor DarkGray
    Write-Host "  Web Search: real-time results via Tavily" -ForegroundColor DarkGray
    Write-Host "  GitHub:     create PRs, manage issues, search repos" -ForegroundColor DarkGray
    Write-Host "  Browser:    navigate pages, fill forms, scrape data, take screenshots" -ForegroundColor DarkGray
} else {
    Write-Warn "No MCP servers configured — .claude\settings.json not written."
    Write-Host "  Re-run this installer after installing VS Code + Power BI extension." -ForegroundColor DarkGray
}

# ── Playwright Chromium browser ───────────────────────────────────────────────

if ($mcpServers.ContainsKey("playwright")) {
    Write-Host ""
    Write-Host "  Playwright needs a Chromium browser to run (~150 MB download)." -ForegroundColor White
    $doChrome = Read-Host "  Download Chromium now for browser automation? (Y/n)"
    if ($doChrome -notmatch "^[Nn]") {
        Write-Host "  Installing Chromium — this may take a few minutes..." -ForegroundColor Cyan
        npx -y playwright install chromium
        if ($LASTEXITCODE -eq 0) {
            Write-Done "Chromium installed for Playwright browser automation."
        } else {
            Write-Warn "Chromium install may have had issues. Run 'npx playwright install chromium' manually if browser tasks fail."
        }
    } else {
        Write-Warn "Chromium skipped. Run 'npx playwright install chromium' before using browser automation."
    }
}

# ── pbi-cli: Power BI Visual Creation ────────────────────────────────────────
# Installs 13 Power BI skills into Claude Code for visual add/update/delete,
# DAX execution, and PBIR report editing — built specifically for Claude Code.
# Ships its own .NET DLLs; no separate .NET install needed.
# Prerequisite at runtime: open Power BI Desktop with your file, then run 'pbi connect'.

Write-Host ""
Write-Host "  pbi-cli: Power BI visual editing..." -ForegroundColor Cyan

# Find pbi-cli in venv (may be .exe or .cmd)
$pbiCliExe = $null
foreach ($candidate in @("pbi-cli.exe", "pbi-cli.cmd", "pbi-cli")) {
    $path = Join-Path $InstallPath ".venv\Scripts\$candidate"
    if (Test-Path $path) { $pbiCliExe = $path; break }
}

if (-not $pbiCliExe) {
    Write-Host "  Installing pbi-cli-tool into venv..." -ForegroundColor Cyan
    Invoke-PipInstall @("pbi-cli-tool") 2>$null
    foreach ($candidate in @("pbi-cli.exe", "pbi-cli.cmd", "pbi-cli")) {
        $path = Join-Path $InstallPath ".venv\Scripts\$candidate"
        if (Test-Path $path) { $pbiCliExe = $path; break }
    }
}

if ($pbiCliExe) {
    Write-Host "  Registering Power BI visual skills with Claude Code..." -ForegroundColor Cyan
    & $pbiCliExe skills install 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Done "pbi-cli ready — 13 Power BI skills registered with Claude Code."
    } else {
        Write-Warn "pbi-cli skills install returned non-zero — skills may not have registered. Try: pbi-cli skills install"
    }
    Write-Host ""
    Write-Host "  To enable visual editing:" -ForegroundColor DarkGray
    Write-Host "    1. Open Power BI Desktop with your .pbip or .pbix file" -ForegroundColor DarkGray
    Write-Host "    2. Run: pbi connect   (in a terminal with .venv active)" -ForegroundColor Yellow
    Write-Host "    3. Then ask Alfred to create or edit visuals" -ForegroundColor DarkGray
} else {
    Write-Warn "pbi-cli-tool install failed — Power BI visual editing unavailable."
    Write-Host "  Try manually: .venv\Scripts\pip install pbi-cli-tool" -ForegroundColor DarkGray
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
