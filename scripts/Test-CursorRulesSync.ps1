#Requires -Version 5.1
<#
.SYNOPSIS
    Fail if cursor/rules and .cursor/rules are out of sync.
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$src = Join-Path $Root 'cursor\rules'
$dest = Join-Path $Root '.cursor\rules'

if (-not (Test-Path $src)) { Write-Error "Missing $src" }
if (-not (Test-Path $dest)) { Write-Error "Missing $dest - run scripts/sync-cursor-rules.ps1" }

$srcFiles = Get-ChildItem $src -Filter '*.mdc' | Sort-Object Name
$destFiles = Get-ChildItem $dest -Filter '*.mdc' | Sort-Object Name
$srcNames = @($srcFiles.Name)
$destNames = @($destFiles.Name)

# graphify.mdc is written by `graphify install --platform cursor` (not Alfred's cursor/rules template).
$allowedExtra = @('graphify.mdc')
$missing = $srcNames | Where-Object { $_ -notin $destNames }
$extra = $destNames | Where-Object { $_ -notin $srcNames -and $_ -notin $allowedExtra }
if ($missing.Count -gt 0) { Write-Error "Missing in .cursor/rules: $($missing -join ', ')" }
if ($extra.Count -gt 0) { Write-Error "Extra in .cursor/rules: $($extra -join ', ')" }

foreach ($name in $srcNames) {
    $a = Get-Content (Join-Path $src $name) -Raw
    $b = Get-Content (Join-Path $dest $name) -Raw
    if ($a -ne $b) {
        Write-Error "Out of sync: $name - run scripts/sync-cursor-rules.ps1"
    }
}

Write-Host '[OK] cursor/rules and .cursor/rules are in sync' -ForegroundColor Green
