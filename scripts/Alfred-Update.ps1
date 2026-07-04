#Requires -Version 5.1
<#
.SYNOPSIS
    Safe Alfred pack updater — backup, pull, re-provision, validate.
.DESCRIPTION
    User must approve the pull. Creates a timestamped backup of user-scope
    configs before applying updates. Never auto-installs untrusted packages.
.PARAMETER AlfredRoot
    Alfred repository root.
.PARAMETER SkipPull
    Re-provision only (no git pull).
#>
param(
    [string]$AlfredRoot = (Split-Path $PSScriptRoot -Parent),
    [switch]$SkipPull
)

$ErrorActionPreference = "Continue"
$LogDir = Join-Path $AlfredRoot "logs"
$BackupDir = Join-Path $LogDir "backups"
$LogFile = Join-Path $LogDir ("update-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

function Log([string]$Msg) {
    $line = "$(Get-Date -Format o) $Msg"
    $line | Add-Content -Path $LogFile -Encoding UTF8
    Write-Host $Msg
}

Log "Alfred update started — root: $AlfredRoot"

# ── Backup user configs ───────────────────────────────────────────────────────
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupTarget = Join-Path $BackupDir $stamp
New-Item -ItemType Directory -Path $backupTarget -Force | Out-Null

$backupPaths = @(
    (Join-Path $env:USERPROFILE ".cursor\mcp.json"),
    (Join-Path $env:USERPROFILE ".cursor\rules"),
    (Join-Path $env:APPDATA "Claude\claude_desktop_config.json"),
    (Join-Path $env:USERPROFILE ".claude.json")
)

foreach ($p in $backupPaths) {
    if (Test-Path $p) {
        $dest = Join-Path $backupTarget ((Split-Path $p -Leaf))
        if (Test-Path $p -PathType Container) {
            Copy-Item $p $dest -Recurse -Force
        } else {
            Copy-Item $p $dest -Force
        }
        Log "Backed up: $p"
    }
}
Log "Config backup: $backupTarget"

# ── Pull updates (with approval) ──────────────────────────────────────────────
if (-not $SkipPull) {
    $checkScript = Join-Path $AlfredRoot "check-updates.ps1"
    if (Test-Path $checkScript) {
        & $checkScript
        $pullExit = $LASTEXITCODE
        if ($pullExit -eq 1) {
            Log "Update pull failed."
            exit 1
        }
        if ($pullExit -ne 10) {
            Log "No updates applied (declined or already current)."
        } else {
            Log "Git pull applied — running setup..."
            $setup = Join-Path $AlfredRoot "setup.ps1"
            if (Test-Path $setup) {
                & $setup
            }
        }
    }
} else {
    Log "SkipPull — re-provisioning only."
    $provision = Join-Path $AlfredRoot "Provision-Cursor.ps1"
    if (Test-Path $provision) {
        & $provision
        if ($LASTEXITCODE -ne 0) { Log "Provision finished with errors."; exit 1 }
    }
}

# ── Validate ──────────────────────────────────────────────────────────────────
$validate = Join-Path $AlfredRoot "scripts\Validate-Install.ps1"
if (Test-Path $validate) {
    & $validate -AlfredRoot $AlfredRoot -LogFile $LogFile
    exit $LASTEXITCODE
}

Log "Update complete (validation script not found)."
exit 0
