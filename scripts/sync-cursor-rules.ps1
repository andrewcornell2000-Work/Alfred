#Requires -Version 5.1
<#
.SYNOPSIS
    Sync canonical cursor/rules/*.mdc into .cursor/rules/ for this workspace.
.DESCRIPTION
    Source of truth: cursor/rules/ (provisioned globally by Provision-Cursor.ps1).
    Run after editing rules in cursor/rules/ so Cursor loads them in-repo too.
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$src = Join-Path $Root 'cursor\rules'
$dest = Join-Path $Root '.cursor\rules'

if (-not (Test-Path $src)) {
    Write-Error "Missing canonical rules directory: $src"
}

New-Item -ItemType Directory -Path $dest -Force | Out-Null
$files = Get-ChildItem $src -Filter '*.mdc'
if ($files.Count -eq 0) {
    Write-Error "No .mdc files in $src"
}

foreach ($file in $files) {
    Copy-Item -Path $file.FullName -Destination (Join-Path $dest $file.Name) -Force
}

Write-Host "[OK] Synced $($files.Count) rule(s) from cursor/rules to .cursor/rules" -ForegroundColor Green
