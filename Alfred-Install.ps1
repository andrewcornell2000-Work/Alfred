#Requires -Version 5.1
<#
.SYNOPSIS
    One-file Alfred bootstrapper. Download and run — no admin required if tools already exist.
.DESCRIPTION
    - Checks for Git, Python 3.13, Node.js — installs via winget (admin) or scoop (no admin)
    - Clones https://github.com/andrewcornell2000-Work/Alfred (or pulls updates)
    - Creates .venv and installs all Python packages
    - Installs Claude Code and Codex CLIs (user-level, no admin)
    - Runs claude auth login and codex login (browser OAuth)
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
    [switch]$NoWizard
)

$script:AlfredRunningAsExe = $false
if ($MyInvocation.MyCommand.Path -match '(?i)Alfred-Install\.exe$') {
    $script:AlfredRunningAsExe = $true
} else {
    try {
        $exePath = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if ($exePath -match '(?i)Alfred-Install\.exe$') { $script:AlfredRunningAsExe = $true }
    } catch { }
}

$ErrorActionPreference = "Continue"

function Show-InstallerFatalError([string]$Message) {
    $logPath = $script:AlfredInstallLogPath
    if ($logPath) { Write-AlfredInstallLog -LogPath $logPath -Level 'ERROR' -Message $Message }
    if ($script:InstallProgress -and (Get-Command Show-AlfredInstallError -ErrorAction SilentlyContinue)) {
        Show-AlfredInstallError -Message $Message -LogPath $logPath
        return
    }
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            'Alfred Installer',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } catch {
        Write-Host $Message -ForegroundColor Red
        Read-Host 'Press Enter to close'
    }
}

trap {
    if ($script:InstallProgress) { $script:InstallProgress.Close() }
    Show-InstallerFatalError "Alfred installer failed:`n`n$($_.Exception.Message)"
    exit 1
}

function Get-AlfredInstallerRoot {
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe) -and $exe -like '*.exe') {
            $parent = Split-Path -Parent $exe
            if ($parent) { return $parent }
        }
    } catch { }
    if ($PSScriptRoot) { return $PSScriptRoot }
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath)) {
        $parent = Split-Path -Parent $cmdPath
        if ($parent) { return $parent }
    }
    return (Get-Location).Path
}

$ScriptRoot = Get-AlfredInstallerRoot

function Import-AlfredInstallerModules([string]$Root) {
    if ([string]::IsNullOrWhiteSpace($Root)) { $Root = Get-AlfredInstallerRoot }
    foreach ($rel in @(
        'installer\Alfred-UiCommon.ps1',
        'installer\Install-Progress.ps1',
        'installer\Install-Wizard.ps1',
        'installer\Update-Alert.ps1'
    )) {
        $path = Join-Path $Root $rel
        if (Test-Path $path) { . $path }
    }
}
Import-AlfredInstallerModules $ScriptRoot
$repoToolsBootstrap = Join-Path $ScriptRoot 'installer\Install-RepoTools.ps1'
if (Test-Path $repoToolsBootstrap) { . $repoToolsBootstrap }
if ($script:AlfredRunningAsExe -and (Get-Command Hide-AlfredConsole -ErrorAction SilentlyContinue)) {
    Hide-AlfredConsole
}

function Write-Banner([string]$Text) {
    Write-Host ""
    Write-Host ("=" * 50) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor Cyan
}
function Test-AlfredGuiInstall {
    if ($script:InstallProgress) { return $true }
    if ($script:AlfredGuiInstallMode) { return $true }
    return [bool]$script:AlfredRunningAsExe
}

function Get-InstallDefaultYes([string]$Prompt) {
    if (Test-AlfredGuiInstall) { return $true }
    return -not ((Read-Host $Prompt) -match '^[Nn]')
}

function Write-Step([string]$Msg) {
    if (Test-AlfredGuiInstall) {
        if ($script:InstallProgress) { $script:InstallProgress.SetDetail($Msg) }
        return
    }
    Write-Host ""
    Write-Host $Msg -ForegroundColor Cyan
}

function Confirm-AlfredAuthLogin([string]$Title, [string]$Message) {
    if (-not (Test-AlfredGuiInstall)) { return $true }
    # GUI install: launch auth automatically — no blocking confirm dialog.
    return $true
}

function Set-InstallStage([string]$StageId, [string]$Detail) {
    if (-not $script:InstallProgress) { return }
    $script:InstallProgress.SetStage($StageId)
    if ($Detail) { $script:InstallProgress.SetDetail($Detail) }
}

function Complete-InstallStage([string]$StageId) {
    if ($script:InstallProgress) { $script:InstallProgress.CompleteStage($StageId) }
}

function Write-InstallLogOnly([string]$Msg) {
    if ($script:AlfredInstallLogPath -and (Get-Command Write-AlfredInstallLog -ErrorAction SilentlyContinue)) {
        Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Message $Msg
    }
}

function Start-AlfredCliAuth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Exe,
        [string[]]$ArgumentList = @()
    )

    if (-not (Test-Path $Exe)) { return }
    $argText = ($ArgumentList -join ' ')

    if (Test-AlfredGuiInstall -or $script:AlfredRunningAsExe) {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        if ($Exe -like '*.cmd' -or $Exe -like '*.bat') {
            $psi.FileName = 'cmd.exe'
            $psi.Arguments = "/c `"$Exe`" $argText"
        } else {
            $psi.FileName = $Exe
            $psi.Arguments = $argText
        }
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        Write-InstallLogOnly ('Started auth (no window): ' + $Exe + ' ' + $argText)
    } else {
        Start-Process 'cmd.exe' -ArgumentList @('/k', "`"$Exe`" $argText")
    }
}

function Invoke-InstallExternal {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$StatusMessage,
        [int]$TimeoutSec = 0
    )

    if (Test-AlfredGuiInstall -and $StatusMessage -and $script:InstallProgress) {
        $script:InstallProgress.SetDetail($StatusMessage)
    }

    $logPath = $script:AlfredInstallLogPath
    if (Test-AlfredGuiInstall -and $logPath) {
        Write-InstallLogOnly "Running: $FilePath $($ArgumentList -join ' ')"
        try {
            $tag = "$PID-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
            $outF = Join-Path $env:TEMP "alfred_out_$tag.log"
            $errF = Join-Path $env:TEMP "alfred_err_$tag.log"
            $p = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -NoNewWindow -PassThru `
                -RedirectStandardOutput $outF -RedirectStandardError $errF
            $waitMs = if ($TimeoutSec -gt 0) { $TimeoutSec * 1000 } else { [int]::MaxValue }
            if (-not $p.WaitForExit($waitMs)) {
                & taskkill /PID $p.Id /T /F 2>&1 | Out-Null
                Write-InstallLogOnly "Timed out after ${TimeoutSec}s"
                Remove-Item $outF, $errF -Force -ErrorAction SilentlyContinue
                return 1
            }
            if (Test-Path $outF) { Get-Content $outF | Add-Content $logPath }
            if (Test-Path $errF) { Get-Content $errF | Add-Content $logPath }
            Remove-Item $outF, $errF -Force -ErrorAction SilentlyContinue
            return $p.ExitCode
        } catch {
            Write-InstallLogOnly "ERROR: $($_.Exception.Message)"
            return 1
        }
    }

    & $FilePath @ArgumentList
    return $LASTEXITCODE
}

function Write-OK([string]$Msg) {
    if (Test-AlfredGuiInstall) { Write-InstallLogOnly "[OK] $Msg"; return }
    Write-Host "  [OK]     $Msg" -ForegroundColor Green
}
function Write-Done([string]$Msg) {
    if (Test-AlfredGuiInstall) { Write-InstallLogOnly "[DONE] $Msg"; return }
    Write-Host "  [DONE]   $Msg" -ForegroundColor Green
}
function Write-Warn([string]$Msg) {
    if (Test-AlfredGuiInstall) { Write-InstallLogOnly "[WARN] $Msg"; return }
    Write-Host "  [WARN]   $Msg" -ForegroundColor Yellow
}
function Write-Fail([string]$Msg) {
    if (Test-AlfredGuiInstall) { Write-InstallLogOnly "[FAIL] $Msg"; return }
    Write-Host "  [FAIL]   $Msg" -ForegroundColor Red
}

function Write-CommandOutput {
    process {
        if ($null -eq $_ -or -not "$_".Trim()) { return }
        if (Test-AlfredGuiInstall) { Write-InstallLogOnly "$_" }
        else { Write-Host "  $_" -ForegroundColor DarkGray }
    }
}

function Invoke-PipInstall([string[]]$Packages) {
    & $PipExe install --quiet --disable-pip-version-check @Packages
}

function Find-Command([string]$Name) {
    foreach ($candidate in @("$Name.cmd", "$Name.exe", "$Name.bat", $Name)) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandType -ne "Alias" } |
            Select-Object -First 1
        if ($found) { return $found.Source }
    }
    return $null
}

function Get-PythonExe {
    $candidatePaths = @()
    foreach ($candidate in @("py.exe", "python.exe", "python3.exe", "py", "python", "python3")) {
        $cmd = Find-Command $candidate
        if ($cmd) { $candidatePaths += $cmd }
    }
    foreach ($root in @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles",
        "${env:ProgramFiles(x86)}"
    )) {
        if ($root -and (Test-Path $root)) {
            $candidatePaths += @(
                Get-ChildItem -Path $root -Directory -Filter "Python3*" -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending |
                    ForEach-Object {
                        $exe = Join-Path $_.FullName "python.exe"
                        if (Test-Path $exe) { $exe }
                    }
            )
        }
    }
    foreach ($regRoot in @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )) {
        if (Test-Path $regRoot) {
            $candidatePaths += @(
                Get-ChildItem $regRoot -ErrorAction SilentlyContinue |
                    Sort-Object PSChildName -Descending |
                    ForEach-Object {
                        $install = Get-ItemProperty "$($_.PSPath)\InstallPath" -ErrorAction SilentlyContinue
                        $exes = @()
                        if ($install.ExecutablePath) { $exes += $install.ExecutablePath }
                        if ($install.'(default)') { $exes += (Join-Path $install.'(default)' "python.exe") }
                        foreach ($exe in $exes) {
                            if ($exe -and (Test-Path $exe)) { $exe }
                        }
                    }
            )
        }
    }

    $orderedCandidates = @($candidatePaths | Where-Object { $_ -notlike "*\Microsoft\WindowsApps\*" } | Select-Object -Unique)
    $orderedCandidates += @($candidatePaths | Where-Object { $_ -like "*\Microsoft\WindowsApps\*" } | Select-Object -Unique)
    foreach ($cmd in $orderedCandidates) {
        if (-not $cmd) { continue }
        $isLauncher = [IO.Path]::GetFileNameWithoutExtension($cmd) -eq "py"
        $args = if ($isLauncher) { @("-3", "--version") } else { @("--version") }
        $output = & $cmd @args 2>&1 | Select-Object -First 1
        if ("$output" -match "^Python\s+3\.(1[0-9])\.") {
            return [PSCustomObject]@{
                Exe      = $cmd
                VenvArgs = if ($isLauncher) { @("-3", "-m", "venv") } else { @("-m", "venv") }
                Version  = "$output"
            }
        }
    }
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
        Write-Host ('  Installing ' + $DisplayName + ' via winget (user scope, no admin)...') -ForegroundColor Cyan
        winget install --id $WingetId --scope user --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if ($LASTEXITCODE -eq 0) { return $true }
        # Some packages only support machine scope — try without --scope as fallback
        winget install --id $WingetId --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if ($LASTEXITCODE -eq 0) { return $true }
    }

    # Fall back to scoop (no admin required)
    Write-Warn 'winget unavailable or failed — trying scoop (no admin required)...'
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
    $pyVer = "3.13.7"
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
        if ($proc.ExitCode -eq 0 -and (Get-PythonExe)) { return $true }
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
        Write-Warn ('Portable Node.js download failed: ' + $_)
        return $false
    }
}

function Install-Uv {
    # Installs uv (Astral) — provides the `uvx` launcher used by the markitdown,
    # fetch, time, sqlite, and duckdb MCP servers. Without uv those 5 MCPs are
    # silently skipped by Provision-Cursor.ps1 (_requiresCommand: "uvx").
    # Official standalone installer — per-user, no admin, lands in %USERPROFILE%\.local\bin.
    Write-Host "  Installing uv (Astral) for uvx-based MCP servers..." -ForegroundColor Cyan
    try {
        powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    } catch {
        Write-Warn "uv install script failed: $_"
    }
    # Installer writes to %USERPROFILE%\.local\bin and updates the user PATH, but the
    # current process needs it on PATH so Step 10's provisioning detects uvx now.
    Add-PathEntry (Join-Path $env:USERPROFILE ".local\bin")
    Refresh-Path
    return [bool](Find-Command "uvx")
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

# ALFRED_INSTALLER_WIZARD_START
# ── Install wizard ────────────────────────────────────────────────────────────

if (-not $NoWizard -and (Get-Command Show-AlfredInstallWizard -ErrorAction SilentlyContinue)) {
    try {
        $wizard = Show-AlfredInstallWizard -DefaultInstallPath $InstallPath -RepoUrl $RepoUrl -AssetsRoot $ScriptRoot
    } catch {
        Show-InstallerFatalError "Could not open the install wizard:`n`n$($_.Exception.Message)"
        exit 1
    }
    if (-not $wizard.Confirmed) { exit 0 }
    $InstallPath = $wizard.InstallPath
    Enable-AlfredGuiInstallOutput -Progress (Start-AlfredInstallProgress -InstallPath $InstallPath -AssetsRoot $ScriptRoot)
    Complete-InstallStage 'prepare'
} elseif ($NoWizard -and (Get-Command Start-AlfredInstallProgress -ErrorAction SilentlyContinue) -and $script:AlfredRunningAsExe) {
    Enable-AlfredGuiInstallOutput -Progress (Start-AlfredInstallProgress -InstallPath $InstallPath -AssetsRoot $ScriptRoot)
    Complete-InstallStage 'prepare'
} elseif ($script:AlfredRunningAsExe -and (Get-Command Start-AlfredInstallProgress -ErrorAction SilentlyContinue)) {
    Enable-AlfredGuiInstallOutput -Progress (Start-AlfredInstallProgress -InstallPath $InstallPath -AssetsRoot $ScriptRoot)
    Complete-InstallStage 'prepare'
} elseif ($NoWizard) {
    if (Get-Command Get-AlfredInstallLogPath -ErrorAction SilentlyContinue) {
        $script:AlfredInstallLogPath = Get-AlfredInstallLogPath -InstallPath $InstallPath
        Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Message 'Installer started.'
    }
} else {
    Write-Banner "Alfred Installer"
    Write-Host ""
    Write-Host "  Install path : $InstallPath" -ForegroundColor White
    Write-Host "  Repository   : $RepoUrl" -ForegroundColor White
    Write-Host "  No admin required - falls back to portable/user installs automatically." -ForegroundColor DarkGray
    Write-Host ""
    $confirm = Read-Host "  Install / update Alfred here? (Y/n)"
    if ($confirm -match "^[Nn]") { Write-Host "Cancelled."; exit 0 }
}

# ── Step 1: Git ───────────────────────────────────────────────────────────────

Set-InstallStage 'requirements' 'Checking Git...'
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

Complete-InstallStage 'requirements'
Set-InstallStage 'core' 'Syncing Alfred repository...'
Write-Step "Step 2: Alfred repository"

if (Test-Path (Join-Path $InstallPath ".git")) {
    Write-OK "Existing checkout found — checking for updates..."
    & git -C $InstallPath fetch origin $Branch 2>&1 | Write-CommandOutput
    $fetchExitCode = $LASTEXITCODE
    if ($fetchExitCode -ne 0) {
        Write-Warn "Could not fetch latest Alfred — continuing with local version."
    } else {
        $localHead  = (git -C $InstallPath rev-parse HEAD 2>&1).Trim()
        $remoteHead = (git -C $InstallPath rev-parse "origin/$Branch" 2>&1).Trim()
        if ($localHead -ne $remoteHead) {
            $behind = (git -C $InstallPath rev-list --count "HEAD..origin/$Branch" 2>&1).Trim()
            $commitLog = @(git -C $InstallPath log --oneline "HEAD..origin/$Branch" 2>&1)
            $applyUpdate = $true
            if (Test-AlfredGuiInstall) {
                Write-OK "Updates available — pulling latest ($behind commit(s))."
            } elseif ((Get-Command Show-AlfredUpdateAlert -ErrorAction SilentlyContinue) -and -not $NoWizard) {
                Import-AlfredInstallerModules $InstallPath
                $choice = Show-AlfredUpdateAlert -BehindCount ([int]$behind) -CommitLines $commitLog -Root $InstallPath
                $applyUpdate = ($choice -eq 'update')
            } else {
                Write-Host ""
                Write-Host "  Updates available: $behind new commit(s) on origin/$Branch." -ForegroundColor Yellow
                $commitLog | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkYellow }
                $response = Read-Host "  Pull updates now? [Y/N]"
                $applyUpdate = ($response -match "^[Yy]")
            }
            if ($applyUpdate) {
                & git -C $InstallPath reset --hard "origin/$Branch" 2>&1 | Write-CommandOutput
                if ($LASTEXITCODE -ne 0) {
                    Write-Warn "Update could not be applied automatically — continuing with local version."
                } else {
                    Write-Done "Repository updated to origin/$Branch."
                }
            } else {
                Write-Host "  Skipping update — continuing with local version." -ForegroundColor DarkGray
            }
        } else {
            Write-OK "Alfred is already up to date."
        }
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

Import-AlfredInstallerModules $InstallPath
$repoToolsPath = Join-Path $InstallPath 'installer\Install-RepoTools.ps1'
if (Test-Path $repoToolsPath) { . $repoToolsPath }

# ── Step 3: Python ────────────────────────────────────────────────────────────

Set-InstallStage 'core' 'Setting up Python environment...'
Write-Step "Step 3: Python"

$PythonInfo = Get-PythonExe
if ($PythonInfo) {
    Write-OK "Python — $($PythonInfo.Version)"
} else {
    $ok = Install-Tool "Python.Python.3.13" "python" "Python 3.13"
    $PythonInfo = Get-PythonExe
    if (-not $PythonInfo) {
        Write-Warn 'winget/scoop failed — trying direct Python download (no admin)...'
        $ok = Install-Python-NoAdmin
        $PythonInfo = Get-PythonExe
    }
    if (-not $PythonInfo) {
        Write-Fail "Python is required. Install from https://www.python.org/downloads/ then re-run."
        exit 2
    }
    Write-OK "Python — $($PythonInfo.Version)"
}

$VenvPath = Join-Path $InstallPath ".venv"
$PipExe   = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    & $PythonInfo.Exe @($PythonInfo.VenvArgs + @($VenvPath))
    if ($LASTEXITCODE -eq 0) {
        Write-Done ".venv created."
    } else {
        Write-Fail "Could not create .venv."
    }
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
    Install-AlfredVenvPostSetup -VenvPath $VenvPath
} else {
    Write-Fail "pip not found in .venv — package install skipped."
}

# ── Step 4: Node.js + CLIs ────────────────────────────────────────────────────

Refresh-Path

Set-InstallStage 'core' 'Installing Node.js and AI CLIs...'
Write-Step "Step 4: Node.js"

if (Find-Command "node") {
    Write-OK ("Node.js — " + (& node --version 2>&1 | Select-Object -First 1))
} else {
    $ok = Install-Tool "OpenJS.NodeJS.LTS" "nodejs" "Node.js LTS"
    if (-not $ok -and -not (Find-Command "node")) {
        Write-Warn 'winget/scoop failed — downloading portable Node.js (no admin)...'
        Install-Node-Portable $InstallPath | Out-Null
        Refresh-Path
    }
}

if (Find-Command "node") {
    $nodeVerStr = & node --version 2>&1 | Select-Object -First 1
    $nodeMajor = ($nodeVerStr -replace 'v', '').Split('.')[0] -as [int]
    Write-OK "Node.js — $nodeVerStr"
    if ($nodeMajor -lt 18) {
        Write-Warn "Node.js $nodeMajor is below MCP minimum (18+). Upgrade at https://nodejs.org/"
    }

    $npmToolStatus = Install-AlfredNpmTools -RepoRoot $InstallPath
    if ($npmToolStatus['claude'] -ne $true) {
        Write-Warn "Claude Code CLI missing — MCP features unavailable until installed."
    }
    if ($npmToolStatus['codex'] -ne $true) {
        Write-Warn "Codex CLI missing — install via requirements/npm-tools.txt."
    }
    if ($npmToolStatus['lean-ctx'] -ne $true) {
        Write-Warn "lean-ctx missing — LeanCTX compression layer skipped until lean-ctx-bin is installed."
    }
} else {
    Write-Warn "Node.js not found — Claude Code, Codex, and lean-ctx CLIs skipped. Re-run after installing Node.js."
}

Complete-InstallStage 'core'

# ── Step 5: Claude login ──────────────────────────────────────────────────────

Set-InstallStage 'configure' 'Setting up Claude authentication...'
Write-Step "Step 5: Claude login (Anthropic account — browser, no API key)"
Write-Host ""

# Find claude.cmd by PATH or directly in npm global bin
$NpmExe = Find-Command "npm"
$npmPrefix = if ($NpmExe) { & $NpmExe prefix -g 2>$null | Select-Object -First 1 } else { $null }
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
    $doLogin = $true
    if (-not (Test-AlfredGuiInstall)) {
        $doLogin = -not ((Read-Host '  Run claude auth login now? (Y/n)') -match '^[Nn]')
    }
    if ($doLogin) {
        if (Test-AlfredGuiInstall) {
            $script:InstallProgress.SetDetail('Opening Claude sign-in in your browser...')
        } else {
            Write-Host '  Opening a new terminal for Claude authentication...' -ForegroundColor Cyan
            Write-Host '  Sign in via the browser that opens, then close the new window.' -ForegroundColor DarkGray
        }
        Start-AlfredCliAuth -Exe $claudeExe -ArgumentList @('auth', 'login')
        if (-not (Test-AlfredGuiInstall)) {
            Read-Host '  Press Enter here once you have finished authenticating'
        }
    }
} else {
    Write-Warn "Claude Code CLI not found on PATH. Open a new terminal and run 'claude auth login' to authenticate."
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
    $doCodex = $true
    if (-not (Test-AlfredGuiInstall)) {
        $doCodex = -not ((Read-Host '  Run codex login now? (Y/n)') -match '^[Nn]')
    }
    if ($doCodex) {
        if (Test-AlfredGuiInstall) {
            $script:InstallProgress.SetDetail('Opening Codex sign-in in your browser...')
        } else {
            Write-Host '  Opening a new terminal for Codex authentication...' -ForegroundColor Cyan
            Write-Host '  Sign in via the browser that opens, then close the new window.' -ForegroundColor DarkGray
        }
        Start-AlfredCliAuth -Exe $codexExe -ArgumentList @('login')
        if (-not (Test-AlfredGuiInstall)) {
            Read-Host '  Press Enter here once you have finished authenticating'
        }
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
} elseif (Test-AlfredGuiInstall) {
    Write-Warn "Tavily key not set — add TAVILY_API_KEY to .env later for live web research."
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
} elseif (Test-AlfredGuiInstall) {
    Write-Warn "Anthropic API key not set — Alfred will use Claude CLI (slower). Add to .env later."
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
} elseif (Test-AlfredGuiInstall) {
    Write-Warn "GitHub token not set — GitHub MCP skipped. Add GITHUB_TOKEN to .env later."
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

Complete-InstallStage 'configure'

# ── Step 9: MCP Tools ────────────────────────────────────────────────────────

Set-InstallStage 'mcps' 'Configuring Power BI, Excel, and browser MCPs...'
Write-Step "Step 9: MCP Tools (Power BI + Excel)"

Install-AlfredOptionalCliTools -InstallPath $InstallPath -VenvPath $VenvPath

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
    $installVSCode = if (Test-AlfredGuiInstall) { $true } else {
        -not ((Read-Host '  Install VS Code now (user install, no admin)? (Y/n)') -match '^[Nn]')
    }
    if ($installVSCode) {
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
$pyForMcp = if (Test-Path $venvPython) { $venvPython } elseif ($PythonInfo) { $PythonInfo.Exe } else { "python" }

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

$NpxExe = Find-Command "npx"

if ($githubToken -and $NpxExe) {
    $mcpServers["github"] = [ordered]@{
        command = $NpxExe
        args    = @("-y", "@modelcontextprotocol/server-github")
        env     = [ordered]@{ GITHUB_PERSONAL_ACCESS_TOKEN = $githubToken }
    }
    Write-OK "GitHub MCP configured — PR creation, issue management, repo search enabled."
} elseif ($githubToken) {
    Write-Warn "GitHub MCP skipped (npx not found — install Node.js first)."
} else {
    Write-Warn 'GitHub MCP skipped (no token). Re-run installer to add it.'
}

# ── Playwright MCP ────────────────────────────────────────────────────────────

if ($NpxExe) {
    $mcpServers["playwright"] = [ordered]@{
        command = $NpxExe
        args    = @("-y", "@playwright/mcp", "--browser", "chromium")
    }
    Write-OK "Playwright MCP configured — browser automation enabled."
} else {
    Write-Warn "Playwright MCP skipped (npx not found — install Node.js first)."
}

# ── uv / uvx (markitdown, fetch, time, sqlite, duckdb MCPs) ───────────────────
# These 3 MCP servers launch via `uvx`. Provision-Cursor.ps1 auto-skips them when
# uvx is missing (_requiresCommand: "uvx" in cursor/mcp.json), so install uv here
# before Step 10 runs — otherwise part of the stack silently never registers.

$uvxReady = $false
if (Find-Command "uvx") {
    Write-OK "uv / uvx already present — markitdown, fetch, duckdb MCPs enabled."
    $uvxReady = $true
} else {
    if (Install-Uv) {
        Write-Done "uv installed — markitdown, fetch, duckdb MCPs enabled."
        $uvxReady = $true
    } else {
        Write-Warn "uv install failed — markitdown, fetch, duckdb MCPs will be skipped."
        Write-Host "  Install manually: irm https://astral.sh/uv/install.ps1 | iex   then re-run this installer." -ForegroundColor DarkGray
    }
}

# Pre-warm the uvx package cache. The first launch of each uvx MCP downloads its
# dependency tree (markitdown pulls a large set), which otherwise overruns the MCP
# client's startup health-check timeout and shows the server as "Failed to connect"
# until a later restart. Fetching now makes the first real launch instant.
if ($uvxReady) {
    $uvxExe = Find-Command "uvx"
    $uvxPkgs = @("markitdown-mcp", "mcp-server-fetch", "mcp-server-duckdb")
    Write-Host "  Pre-fetching uvx MCP packages (first run only — may take a minute)..." -ForegroundColor Cyan
    foreach ($pkg in $uvxPkgs) {
        try {
            if (Test-AlfredGuiInstall -and $script:AlfredInstallLogPath) {
                Write-InstallLogOnly "Pre-fetching uvx package: $pkg"
                $tag = "$PID-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
                $outF = Join-Path $env:TEMP "alfred_uvx_$tag.out"
                $errF = Join-Path $env:TEMP "alfred_uvx_$tag.err"
                $p = Start-Process -FilePath $uvxExe -ArgumentList @($pkg, '--help') `
                    -NoNewWindow -PassThru -RedirectStandardOutput $outF -RedirectStandardError $errF
            } else {
                $p = Start-Process -FilePath $uvxExe -ArgumentList @($pkg, '--help') `
                    -NoNewWindow -PassThru -RedirectStandardOutput $env:TEMP\uvx-warm.out -RedirectStandardError $env:TEMP\uvx-warm.err
            }
            if (-not $p.WaitForExit(180000)) { $p.Kill() }  # 3-min cap per package
            if (Test-AlfredGuiInstall -and $script:AlfredInstallLogPath) {
                if (Test-Path $outF) { Get-Content $outF | Add-Content $script:AlfredInstallLogPath }
                if (Test-Path $errF) { Get-Content $errF | Add-Content $script:AlfredInstallLogPath }
                Remove-Item $outF, $errF -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
    if (-not (Test-AlfredGuiInstall)) {
        Remove-Item "$env:TEMP\uvx-warm.out","$env:TEMP\uvx-warm.err" -ErrorAction SilentlyContinue
    }
    Write-Done "uvx MCP packages cached — markitdown, fetch, duckdb will connect on first launch."
}

# ── Write settings.json (permissions only — MCPs come from Provision-Cursor.ps1) ──
# Provision-Cursor.ps1 is the single source of truth for MCP servers across
# Cursor, Claude Code (user scope), and Codex. Writing a partial mcpServers block
# here would shadow the global registry and miss servers on fresh installs.

$settingsPath = Join-Path $ClaudeSettingsDir "settings.json"
$settingsObj = [ordered]@{
    permissions = [ordered]@{
        allow = @(
            "Bash(pbi*)", "Bash(python*)", "Bash(git *)", "Bash(git)",
            "Bash(npm *)", "Bash(npx *)", "Bash(node *)", "Bash(pip *)",
            "Bash(powershell *)", "Bash(uvx*)", "Bash(gh*)", "Bash(jq*)",
            "Bash(pandoc*)", "Bash(az*)", "Bash(xlwings*)", "Bash(vd*)",
            "Bash(in2csv*)", "Bash(csvsql*)", "Bash(csvstat*)",
            "Bash(csvjoin*)", "Bash(csvcut*)"
        )
        deny  = @()
    }
    # Continuous-learning + guardrail hooks (scripts live in the repo; $CLAUDE_PROJECT_DIR
    # resolves to the repo root when working in Alfred). Python, stdlib-only, fail-safe.
    hooks = [ordered]@{
        SessionStart = @(
            [ordered]@{ hooks = @(
                [ordered]@{ type = "command"; command = 'python "$CLAUDE_PROJECT_DIR/scripts/hooks/session-start-instincts.py"' }
            ) }
        )
        PreToolUse = @(
            [ordered]@{ matcher = "Edit|Write|MultiEdit"; hooks = @(
                [ordered]@{ type = "command"; command = 'python "$CLAUDE_PROJECT_DIR/scripts/hooks/config-protection.py"' }
            ) }
            [ordered]@{ matcher = "Bash"; hooks = @(
                [ordered]@{ type = "command"; command = 'python "$CLAUDE_PROJECT_DIR/scripts/hooks/pre-commit-quality.py"' }
            ) }
        )
        Stop = @(
            [ordered]@{ hooks = @(
                [ordered]@{ type = "command"; command = 'python "$CLAUDE_PROJECT_DIR/scripts/hooks/observe-session.py"' }
            ) }
        )
    }
}
$settingsJson = $settingsObj | ConvertTo-Json -Depth 10
Set-Content $settingsPath $settingsJson -Encoding UTF8
Write-Done ".claude\settings.json written (permissions + continuous-learning/guardrail hooks; MCPs in Step 10)."
if ($mcpServers.Count -gt 0) {
    Write-Host "  Detected $($mcpServers.Count) local MCP prerequisite(s) — full stack registered via Provision-Cursor.ps1" -ForegroundColor DarkGray
} else {
    Write-Warn "Some MCP prerequisites missing (VS Code / Node / excellm) — Step 10 will register what it can."
}

# ── Playwright Chromium browser ───────────────────────────────────────────────

if ($mcpServers.Keys -contains 'playwright') {
    if (-not (Test-AlfredGuiInstall)) {
        Write-Host ''
        Write-Host '  Playwright needs a Chromium browser to run (~150 MB download).' -ForegroundColor White
    }
    $doChrome = if (Test-AlfredGuiInstall) { $true } else {
        -not ((Read-Host '  Download Chromium now for browser automation? (Y/n)') -match '^[Nn]')
    }
    if ($doChrome) {
        if (Test-AlfredGuiInstall) {
            $script:InstallProgress.SetDetail('Downloading Chromium (~150 MB)...')
        } else {
            Write-Host "  Installing Chromium — this may take a few minutes..." -ForegroundColor Cyan
        }
        $chromeExit = Invoke-InstallExternal -FilePath $NpxExe `
            -ArgumentList @('-y', 'playwright', 'install', 'chromium') `
            -StatusMessage 'Downloading Chromium (~150 MB)...'
        if ($chromeExit -eq 0) {
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

# Always install/upgrade pbi-cli-tool to the required version (>=3.11.1), even if an
# older copy already exists. pip handles its pre-release dependency (pythonnet==3.1.0rc0);
# a bare `uv tool install` would silently fall back to 1.0.6 without `--prerelease allow`.
Write-Host "  Installing/upgrading pbi-cli-tool (>=3.11.1) into venv..." -ForegroundColor Cyan
Invoke-PipInstall @("--upgrade", "pbi-cli-tool>=3.11.1") 2>$null

# 3.11.x installs both 'pbi' and 'pbi-cli' executables.
$pbiCliExe = $null
foreach ($candidate in @("pbi.exe", "pbi-cli.exe", "pbi.cmd", "pbi-cli.cmd", "pbi", "pbi-cli")) {
    $path = Join-Path $InstallPath ".venv\Scripts\$candidate"
    if (Test-Path $path) { $pbiCliExe = $path; break }
}

if ($pbiCliExe) {
    Write-Host "  Verifying pbi-cli env + registering Power BI skills with Claude Code..." -ForegroundColor Cyan
    & $pbiCliExe setup 2>$null   # 3.11.x: 'setup' verifies the env AND installs Claude Code skills (replaces 'skills install')
    if ($LASTEXITCODE -eq 0) {
        Write-Done "pbi-cli 3.11+ ready — environment verified, Power BI skills registered with Claude Code."
    } else {
        Write-Warn "pbi-cli setup returned non-zero. Run manually: .venv\Scripts\pbi setup"
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

Complete-InstallStage 'mcps'

# ── Step 10: Cursor + Claude Code provisioning (shared MCPs + skills) ──────────

Set-InstallStage 'verify' 'Provisioning MCPs, skills, and rules for Cursor and Claude Code...'
Write-Step "Step 10: Provisioning MCPs + skills + LeanCTX for Cursor, Claude Code, and Codex"

$provisionScript = Join-Path $InstallPath "Provision-Cursor.ps1"
if (Test-Path $provisionScript) {
    try {
        $provisionParams = @{ ProjectPath = $InstallPath }
        if (Test-AlfredGuiInstall) { $provisionParams.InstallerMode = $true }
        & $provisionScript @provisionParams
    } catch {
        Write-Warn "Cursor/Claude provisioning failed: $_"
        Write-Host "  Re-run later: powershell -ExecutionPolicy Bypass -File `"$provisionScript`"" -ForegroundColor DarkGray
    }
} else {
    Write-Warn "Provision-Cursor.ps1 not found — update Alfred (git pull) and re-run the installer."
}

Complete-InstallStage 'verify'

# ── Step 8: Desktop shortcut ──────────────────────────────────────────────────

Set-InstallStage 'finalize' 'Creating desktop shortcut...'
Write-Step "Step 8: Desktop shortcut"

$Desktop    = [System.Environment]::GetFolderPath("Desktop")
$Shortcut   = Join-Path $Desktop "Alfred.lnk"
$LauncherPs = Join-Path $InstallPath "run-alfred.bat"
$IconPath   = Join-Path $InstallPath "assets\alfred.ico"

try {
    $existed = Test-Path $Shortcut
    $wsh = New-Object -ComObject WScript.Shell
    $lnk = $wsh.CreateShortcut($Shortcut)
    $lnk.TargetPath       = "cmd.exe"
    $lnk.Arguments        = "/c `"$LauncherPs`""
    $lnk.WorkingDirectory = $InstallPath
    $lnk.Description      = "Alfred AI Assistant"
    if (Test-Path $IconPath) { $lnk.IconLocation = "$IconPath,0" } else { $lnk.IconLocation = "cmd.exe,0" }
    $lnk.Save()
    if ($existed) { Write-OK 'Desktop shortcut refreshed — Alfred.lnk (custom icon)' }
    else { Write-Done 'Desktop shortcut created — Alfred.lnk (custom icon)' }
} catch {
    Write-Warn "Could not create desktop shortcut: $_"
}

Complete-InstallStage 'finalize'
if ($script:AlfredInstallLogPath) {
    Write-AlfredInstallLog -LogPath $script:AlfredInstallLogPath -Message 'Alfred installed successfully.'
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Banner "Alfred is ready"
Write-Host ""
Write-Host "  Launch: double-click Alfred on your desktop" -ForegroundColor Green
Write-Host "  Or run: $LauncherPs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Optional: Quant plugin — pip install -r plugins\quant\requirements.txt" -ForegroundColor DarkGray
Write-Host "  Optional: add API keys to .env (Tavily, Anthropic, GitHub) for full MCP stack" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To update Alfred in future: re-run this installer." -ForegroundColor DarkGray
Write-Host ""

$completeSummary = @(
    'Alfred core files and Python environment'
    'npm tools from requirements/npm-tools.txt (Claude, Codex, lean-ctx)'
    'Optional CLIs: gh, jq, pandoc, excel-mcp, Azure CLI when available'
    'Cursor / Claude Code / Codex skills, rules and MCPs'
    'Desktop shortcut (Alfred.lnk)'
)
if (-not (Test-Path (Join-Path $InstallPath '.env'))) {
    $completeSummary += 'Optional: add .env keys later for Tavily, Anthropic API, GitHub MCP'
}

if (-not $NoWizard -and (Get-Command Show-AlfredInstallComplete -ErrorAction SilentlyContinue)) {
    Show-AlfredInstallComplete -InstallPath $InstallPath -SummaryItems $completeSummary
} elseif ($script:InstallProgress) {
    $script:InstallProgress.Close()
}
