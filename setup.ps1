#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for Alfred on a fresh Windows machine.
.DESCRIPTION
    Checks and installs prerequisites (using winget when available), creates the
    Python venv, installs Python packages from requirements/python-requirements.txt,
    installs npm CLI tools from requirements/npm-tools.txt, writes .env.template,
    and prints login instructions.
    Safe to re-run at any time -- all steps are idempotent.
.OUTPUTS
    Exit 0 -- all required components ready; Alfred can start.
    Exit 1 -- .env is missing; add API keys then re-run.
    Exit 2 -- Python not found; install Python then re-run.
    Exit 3 -- Git, Node.js, npm, Claude Code, or Codex is missing.
#>

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

. (Join-Path $Root 'Alfred-Common.ps1')
. (Join-Path $Root 'Alfred-CoreSetup.ps1')

function Add-RepoLocalNodeToPath {
    $candidates = @()

    $legacyPortableNode = Join-Path $Root "node"
    if (Test-Path (Join-Path $legacyPortableNode "node.exe")) {
        $candidates += $legacyPortableNode
    }

    $nodeCacheRoot = Join-Path $Root "Node"
    if (Test-Path $nodeCacheRoot) {
        $candidates += @(
            Get-ChildItem -Path $nodeCacheRoot -Directory -Filter "node-v*-win-x64" -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { $_.FullName }
        )
    }

    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate "node.exe")) {
            $null = Add-ProcessPathEntry $candidate
            Write-OK "Repo-local Node.js path -- $candidate"
            return $true
        }
    }

    return $false
}

function Get-NpmGlobalBin {
    $npmExe = Find-Command "npm"
    if (-not $npmExe) { return $null }
    $prefix = & $npmExe prefix -g 2>$null | Select-Object -First 1
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
        Write-Info "winget not available -- will try Scoop (no admin) instead."
        return $false
    }
    Write-Host "  Installing $Name via winget, user scope (this may take a moment)..." -ForegroundColor Cyan
    # Prefer user scope so no admin/UAC is needed; some packages ignore it harmlessly.
    winget install --id $PackageId --scope user --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        Refresh-Path
        Write-Done "$Name installed."
        return $true
    }
    Write-Info "$Name not installed via winget (may require admin) -- will try Scoop (no admin)."
    return $false
}

function Ensure-Scoop {
    if (Find-Command "scoop") { return $true }
    Write-Host "  Installing Scoop (user-space package manager, no admin required)..." -ForegroundColor Cyan
    try {
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
        Invoke-RestMethod -Uri "https://get.scoop.sh" | Invoke-Expression
        Refresh-Path
    } catch {
        Write-Fail "Scoop bootstrap failed: $_"
    }
    return [bool](Find-Command "scoop")
}

function Install-ViaScoop([string]$Package, [string]$Name) {
    if (-not (Ensure-Scoop)) {
        Write-Info "Scoop unavailable -- $Name needs a manual install."
        return $false
    }
    Write-Host "  Installing $Name via Scoop (no admin)..." -ForegroundColor Cyan
    & scoop install $Package 2>&1 | Out-Null
    Refresh-Path
    Write-Done "$Name install via Scoop attempted."
    return $true
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
$PythonInfo = Get-PythonExe
if ($PythonInfo) {
    Write-OK "Python -- $($PythonInfo.Version)"
    $hasPython = $true
} else {
    Write-Warn "Python not found."
    $null = Invoke-WingetInstall "Python.Python.3.13" "Python 3.13"
    $PythonInfo = Get-PythonExe
    if (-not $PythonInfo -and (Install-ViaScoop "python" "Python")) {
        $PythonInfo = Get-PythonExe
    }
    if ($PythonInfo) {
        Write-OK "Python -- $($PythonInfo.Version)"
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
    if (-not (Find-Command "git")) { $null = Install-ViaScoop "git" "Git" }
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
$null = Add-RepoLocalNodeToPath
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
    if (-not (Find-Command "node")) { $null = Install-ViaScoop "nodejs-lts" "Node.js LTS" }
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
    $NpmExe = Find-Command "npm"
    $npmVer = & $NpmExe --version 2>&1 | Select-Object -First 1
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
        $toolExe = Find-Command $tool.Command
        if ($toolExe) {
            $ver = & $toolExe --version 2>&1 | Select-Object -First 1
            Write-OK "$($tool.Description) -- $ver"
            $toolStatus[$tool.Command] = $true
        } else {
            Write-Host "  Installing $($tool.Description) (npm install -g $($tool.Package))..." -ForegroundColor Cyan
            & $NpmExe install -g $tool.Package
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

# CodeGraph retired from Alfred MCP stack (LeanCTX ctx_search covers repo code).
# Leave .codegraph/ on disk if present; it is no longer provisioned as an MCP.

# Convenience flags used by login instructions below
$hasClaude = $toolStatus["claude"] -eq $true
$hasCodex  = $toolStatus["codex"]  -eq $true
$hasSupportedNode = $hasNode -and ($nodeVersionMajor -ge 18)
$missingNpmTools = @($npmToolList | Where-Object { $toolStatus[$_.Command] -ne $true })
$allNpmToolsReady = $missingNpmTools.Count -eq 0

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
    Write-OK "Claude Code CLI available (MCP host + agent runtime)."
} else {
    Write-Warn "Claude Code CLI missing -- MCP features unavailable until installed."
}

if ($hasCodex) {
    Write-OK "Codex CLI available (MCP host + coding agent runtime)."
} else {
    Write-Warn "Codex CLI missing -- install via npm-tools.txt for coding agent routing."
}

# ── Python virtual environment ────────────────────────────────────────────────

Write-Step "Python virtual environment..."

$VenvPath = Join-Path $Root ".venv"
$PipExe   = Join-Path $VenvPath "Scripts\pip.exe"

if (-not $hasPython) {
    Write-Skip "Python not found -- skipping venv and package install."
} else {
    $pySetup = Install-AlfredPythonEnvironment -RepoRoot $Root -PythonInfo $PythonInfo -OnStep {
        param($Msg)
        Write-Host "  $Msg" -ForegroundColor Cyan
    }
    if (-not $pySetup.Ok) {
        Write-Fail $pySetup.Message
    } elseif (-not (Test-Path $VenvPath)) {
        Write-Fail "Could not create .venv."
    } else {
        if (Test-Path $VenvPath) { Write-OK ".venv ready." }
        if ($pySetup.Failed -and $pySetup.Failed.Count -gt 0) {
            Write-Warn "Some optional Python packages failed: $($pySetup.Failed -join ', ')"
            Write-Info "Alfred will continue; re-run setup or python -m backend.cli diagnose to check optional packages."
        } else {
            Write-Done "Packages installed from requirements/python-requirements.txt"
        }
        $xlwingsExe = Join-Path $VenvPath "Scripts\xlwings.exe"
        if (Test-Path $xlwingsExe) {
            & $xlwingsExe addin install 2>&1 | Out-Null
            Write-Done "xlwings Excel add-in registered."
        }
    }
}

# Alfred venv Scripts on PATH — excellm, uvx, az, vd, csvkit, xlwings for agents + MCP provision
$venvScripts = Join-Path $VenvPath "Scripts"
if (Test-Path $venvScripts) {
    $null = Add-PathEntry $venvScripts
    Write-OK "Alfred venv Scripts on user PATH -- $venvScripts"
}

# pbi-cli skills for Claude Code (Power BI report authoring)
$pbiExe = Join-Path $VenvPath "Scripts\pbi.exe"
if (-not (Test-Path $pbiExe)) { $pbiExe = Find-Command "pbi" }
if ($pbiExe) {
    Write-Host "  Registering Power BI skills for Claude Code (pbi setup)..." -ForegroundColor Cyan
    & $pbiExe setup 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Done "Power BI skills registered (pbi setup)." }
    else { Write-Warn "pbi setup may have had issues — run 'pbi setup' manually if Power BI tasks fail." }
}

# uvx check (installed via `uv` in python-requirements.txt)
if (Find-Command "uvx") {
    Write-OK "uvx available (fetch, time, markitdown MCPs)."
} elseif (Test-Path $PipExe) {
    Write-Warn "uvx not on PATH after venv install -- re-run setup or: .venv\Scripts\pip install uv"
} else {
    Write-Skip "uvx check skipped (no venv pip)."
}

# ── Optional CLI tools (no admin required) ───────────────────────────────────

Write-Step "Optional CLI tools (no admin required)..."

# Bin dir for portable tools — added to user PATH
$BinDir = Join-Path $Root "bin"
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }
$null = Add-PathEntry $BinDir

# jq — JSON processor (winget, single .exe, no elevation needed)
if (Find-Command "jq") {
    $jqVer = & jq --version 2>&1 | Select-Object -First 1
    Write-OK "jq (JSON processor) -- $jqVer"
} elseif (Find-Command "winget") {
    Write-Host "  Installing jq via winget..." -ForegroundColor Cyan
    winget install jqlang.jq --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    Refresh-Path
    if (Find-Command "jq") { Write-Done "jq installed." }
    else { Write-Info "jq: run 'winget install jqlang.jq' manually." }
} else {
    Write-Skip "jq: winget not available -- install from https://github.com/jqlang/jq/releases"
}

# pandoc — document converter (winget, no elevation needed)
if (Find-Command "pandoc") {
    $pandocVer = & pandoc --version 2>&1 | Select-Object -First 1
    Write-OK "pandoc (document converter) -- $pandocVer"
} elseif (Find-Command "winget") {
    Write-Host "  Installing pandoc via winget..." -ForegroundColor Cyan
    winget install JohnMacFarlane.Pandoc --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    Refresh-Path
    if (Find-Command "pandoc") { Write-Done "pandoc installed." }
    else { Write-Info "pandoc: run 'winget install JohnMacFarlane.Pandoc' manually." }
} else {
    Write-Skip "pandoc: winget not available -- install from https://pandoc.org/installing.html"
}

# gh — GitHub CLI (portable ZIP into Alfred\bin\, no admin)
$ghExe = Join-Path $BinDir "gh.exe"
if ((Find-Command "gh") -or (Test-Path $ghExe)) {
    $ghBin = if (Test-Path $ghExe) { $ghExe } else { "gh" }
    $ghVer = & $ghBin --version 2>&1 | Select-Object -First 1
    Write-OK "gh (GitHub CLI) -- $ghVer"
} else {
    Write-Host "  Installing gh CLI (portable, no admin)..." -ForegroundColor Cyan
    try {
        $release    = Invoke-RestMethod "https://api.github.com/repos/cli/cli/releases/latest" -UseBasicParsing -ErrorAction Stop
        $ghVersion  = $release.tag_name -replace '^v', ''
        $ghUrl      = "https://github.com/cli/cli/releases/download/v$ghVersion/gh_${ghVersion}_windows_amd64.zip"
        $zipPath    = Join-Path $env:TEMP "gh_portable.zip"
        $extractDir = Join-Path $env:TEMP "gh_portable_extract"

        Invoke-WebRequest -Uri $ghUrl -OutFile $zipPath -UseBasicParsing -ErrorAction Stop
        if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
        $src = Get-ChildItem -Path $extractDir -Filter "gh.exe" -Recurse | Select-Object -First 1
        if ($src) {
            Copy-Item $src.FullName $ghExe -Force
            $null = Add-PathEntry $BinDir
            Write-Done "gh CLI $ghVersion installed to Alfred\bin\ (no admin)."
            Write-Info "Run 'gh auth login' once to connect your GitHub account."
        } else {
            Write-Fail "gh.exe not found in downloaded archive."
        }
        Remove-Item $zipPath, $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Fail "gh portable install failed: $_"
        Write-Info "Download manually from https://github.com/cli/cli/releases (extract gh.exe to Alfred\bin\)"
    }
}

# excel-mcp — ExcelMcp MCP server (sbroenne, self-contained .exe into Alfred\bin\excel-mcp\, no admin, no .NET runtime)
$excelMcpDir = Join-Path $BinDir "excel-mcp"
$excelMcpExe = Join-Path $excelMcpDir "mcp-excel.exe"
if (Test-Path $excelMcpExe) {
    Write-OK "excel-mcp (ExcelMcp MCP server) -- present in Alfred\bin\excel-mcp\"
} else {
    Write-Host "  Installing ExcelMcp MCP server (portable, no admin)..." -ForegroundColor Cyan
    try {
        $emRelease = Invoke-RestMethod "https://api.github.com/repos/sbroenne/mcp-server-excel/releases/latest" -UseBasicParsing -ErrorAction Stop
        $emAsset   = $emRelease.assets | Where-Object { $_.name -match '^ExcelMcp-MCP-Server-.*-windows\.zip$' } | Select-Object -First 1
        if (-not $emAsset) { throw "ExcelMcp-MCP-Server-*-windows.zip asset not found in latest release." }
        $emZip        = Join-Path $env:TEMP "excelmcp_server.zip"
        $emExtractDir = Join-Path $env:TEMP "excelmcp_server_extract"
        Invoke-WebRequest -Uri $emAsset.browser_download_url -OutFile $emZip -UseBasicParsing -ErrorAction Stop
        if (Test-Path $emExtractDir) { Remove-Item $emExtractDir -Recurse -Force }
        Expand-Archive -Path $emZip -DestinationPath $emExtractDir -Force
        $emSrc = Get-ChildItem -Path $emExtractDir -Filter "mcp-excel.exe" -Recurse | Select-Object -First 1
        if ($emSrc) {
            if (-not (Test-Path $excelMcpDir)) { New-Item -ItemType Directory -Path $excelMcpDir -Force | Out-Null }
            Copy-Item $emSrc.FullName $excelMcpExe -Force
            Write-Done "ExcelMcp MCP server $($emRelease.tag_name) installed to Alfred\bin\excel-mcp\ (no admin)."
            Write-Info "Registered as the 'excel-mcp' MCP. Requires Excel; close open workbooks before use (exclusive access)."
        } else {
            Write-Fail "mcp-excel.exe not found in downloaded archive."
        }
        Remove-Item $emZip, $emExtractDir -Recurse -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Fail "ExcelMcp portable install failed: $_"
        Write-Info "Download manually from https://github.com/sbroenne/mcp-server-excel/releases (extract mcp-excel.exe to Alfred\bin\excel-mcp\)"
    }
}

# az — Azure CLI (winget; avoid pip — azure-cli via pip is ~500 MB into venv and often 10+ min with no progress output)
$azVenv = @(
    (Join-Path $VenvPath "Scripts\az.cmd"),
    (Join-Path $VenvPath "Scripts\az.bat"),
    (Join-Path $VenvPath "Scripts\az")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ((Find-Command "az") -or $azVenv) {
    $azBin = if (Find-Command "az") { "az" } else { $azVenv }
    $azVer = & $azBin version 2>&1 | Select-Object -First 1
    Write-OK "az (Azure CLI) -- $azVer"
} elseif (Find-Command "winget") {
    Write-Host "  Installing Azure CLI via winget..." -ForegroundColor Cyan
    winget install Microsoft.AzureCLI --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    Refresh-Path
    if (Find-Command "az") {
        Write-Done "Azure CLI installed."
        Write-Info "Run 'az login' once to connect your Microsoft/Maersk account."
    } else {
        Write-Info "az: run 'winget install Microsoft.AzureCLI' manually. Alfred works fine without it."
    }
} else {
    Write-Skip "az: winget not available -- install from https://aka.ms/install-azure-cli"
}

# ── .env / secrets ────────────────────────────────────────────────────────────

Write-Step ".env (API keys)..."

$EnvFile     = Join-Path $Root ".env"
$EnvTemplate = Join-Path $Root ".env.template"

$hasEnv = Test-Path $EnvFile

if ($hasEnv) {
    Write-OK ".env found (optional config)."
} else {
    Write-Info ".env not present -- that's fine. Auth uses 'claude auth login', no API keys needed."
    if (-not (Test-Path $EnvTemplate)) {
        Copy-Item (Join-Path $Root ".env.template") $EnvTemplate -ErrorAction SilentlyContinue
    }
}

# ── Cursor + Claude Code provisioning (shared MCPs + skills) ──────────────────

Write-Step "Provisioning MCP servers + skills + LeanCTX for Cursor, Claude Code, and Codex..."

$provisionScript = Join-Path $Root "Provision-Cursor.ps1"
if (Test-Path $provisionScript) {
    try {
        & $provisionScript -ProjectPath $Root
    } catch {
        Write-Warn "Cursor/Claude provisioning step failed: $_"
        Write-Info "Re-run manually: powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1"
    }
} else {
    Write-Skip "Provision-Cursor.ps1 not found -- skipping cross-tool provisioning."
}

# ── Desktop shortcut (custom icon) ────────────────────────────────────────────

Write-Step "Desktop shortcut..."
try {
    $Desktop     = [System.Environment]::GetFolderPath("Desktop")
    $Shortcut    = Join-Path $Desktop "Alfred.lnk"
    $LauncherBat = Join-Path $Root "run-alfred.bat"
    $IconPath    = Join-Path $Root "assets\alfred.ico"
    if (Test-Path $LauncherBat) {
        $existed = Test-Path $Shortcut
        $wsh = New-Object -ComObject WScript.Shell
        $lnk = $wsh.CreateShortcut($Shortcut)
        $lnk.TargetPath       = "cmd.exe"
        $lnk.Arguments        = "/c `"$LauncherBat`""
        $lnk.WorkingDirectory = $Root
        $lnk.Description      = "Alfred - update and provision"
        if (Test-Path $IconPath) { $lnk.IconLocation = "$IconPath,0" } else { $lnk.IconLocation = "cmd.exe,0" }
        $lnk.Save()
        if ($existed) { Write-OK "Desktop shortcut refreshed (custom icon)." }
        else { Write-Done "Desktop shortcut created (custom icon)." }
    } else {
        Write-Skip "run-alfred.bat not found -- skipping desktop shortcut."
    }
} catch {
    Write-Warn "Could not create desktop shortcut: $_"
}

# ── login instructions ────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Authentication (run once per machine)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($hasClaude) {
    Write-Host "  Claude Code login:" -ForegroundColor White
    Write-Host "    claude auth login" -ForegroundColor Yellow
    Write-Host "  Opens a browser to authenticate with your Anthropic account." -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "  Claude Code CLI not installed -- install it first:" -ForegroundColor Yellow
    Write-Host "    npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
    Write-Host "    claude auth login" -ForegroundColor Yellow
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

$readyToRun = $hasPython -and $hasGit -and $hasSupportedNode -and $hasNpm -and $allNpmToolsReady

if ($hasPython) { Write-Host "  [x] Python"   -ForegroundColor Green  } else { Write-Host "  [ ] Python 3.10+  --  https://www.python.org/downloads/"  -ForegroundColor Yellow }
if ($hasGit)    { Write-Host "  [x] Git"      -ForegroundColor Green  } else { Write-Host "  [ ] Git           --  https://git-scm.com/download/win"    -ForegroundColor Yellow }
if ($hasSupportedNode) {
    Write-Host "  [x] Node.js 18+" -ForegroundColor Green
} elseif ($hasNode) {
    Write-Host "  [ ] Node.js 18+   --  upgrade from detected major version $nodeVersionMajor" -ForegroundColor Yellow
} else {
    Write-Host "  [ ] Node.js 18+   --  https://nodejs.org/" -ForegroundColor Yellow
}

if ($hasNpm) { Write-Host "  [x] npm" -ForegroundColor Green } else { Write-Host "  [ ] npm           --  installed with Node.js" -ForegroundColor Yellow }

foreach ($tool in $npmToolList) {
    $ok = $toolStatus[$tool.Command] -eq $true
    if ($ok) {
        Write-Host "  [x] $($tool.Description)" -ForegroundColor Green
    } else {
        Write-Host "  [ ] $($tool.Description)  --  npm install -g $($tool.Package)" -ForegroundColor Yellow
    }
}

Write-Host "  [i] Auth: run 'claude auth login' once to authenticate (no API keys needed)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Optional CLI tools (no admin required):" -ForegroundColor DarkGray
if (Find-Command "jq")                                         { Write-Host "  [x] jq"     -ForegroundColor Green  } else { Write-Host "  [ ] jq      --  winget install jqlang.jq"              -ForegroundColor DarkGray }
if (Find-Command "pandoc")                                     { Write-Host "  [x] pandoc" -ForegroundColor Green  } else { Write-Host "  [ ] pandoc  --  winget install JohnMacFarlane.Pandoc"  -ForegroundColor DarkGray }
$ghReady = (Find-Command "gh") -or (Test-Path (Join-Path $Root "bin\gh.exe"))
if ($ghReady)                                                  { Write-Host "  [x] gh      --  run 'gh auth login' to connect GitHub" -ForegroundColor Green   } else { Write-Host "  [ ] gh      --  portable ZIP, see setup output above"    -ForegroundColor DarkGray }
$azReady = (Find-Command "az") -or (Test-Path (Join-Path $VenvPath "Scripts\az.cmd")) -or (Test-Path (Join-Path $VenvPath "Scripts\az.bat")) -or (Test-Path (Join-Path $VenvPath "Scripts\az"))
if ($azReady)                                                  { Write-Host "  [x] az      --  run 'az login' to connect Microsoft account" -ForegroundColor Green } else { Write-Host "  [ ] az      --  winget install Microsoft.AzureCLI"       -ForegroundColor DarkGray }

Write-Host ""

if ($readyToRun) {
    Write-Host "  Alfred is ready to run." -ForegroundColor Green
} else {
    Write-Host "  Fix the items above, then re-run Install-Alfred.bat." -ForegroundColor DarkYellow
}

Write-Host ""

# Exit codes (read by Install-Alfred.bat and run-alfred.bat)
if (-not $hasPython) { exit 2 }
if (-not $hasGit -or -not $hasSupportedNode -or -not $hasNpm -or -not $allNpmToolsReady) { exit 3 }
exit 0
