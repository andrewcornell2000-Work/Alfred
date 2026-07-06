# Repro/regression test: the build-installer module-body extractor must strip
# script-level param blocks but never function-level ones.
function Get-InstallerModuleBody([string]$Path) {
    $content = Get-Content $Path -Raw
    $content = ($content -replace '(?m)^#Requires[^\r\n]*\r?\n', '').Trim()
    $tokens = $null
    $parseErrors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseInput($content, [ref]$tokens, [ref]$parseErrors)
    if (-not $parseErrors -and $ast.ParamBlock) {
        $start = $ast.ParamBlock.Extent.StartOffset
        $end = $ast.ParamBlock.Extent.EndOffset
        $content = ($content.Substring(0, $start) + $content.Substring($end)).Trim()
    }
    return $content
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$failures = 0

# 1. Function-level param blocks must survive untouched.
foreach ($rel in @('installer\Alfred-UiCommon.ps1', 'installer\Install-Progress.ps1', 'installer\Install-Wizard.ps1')) {
    $path = Join-Path $repoRoot $rel
    $raw = (Get-Content $path -Raw) -replace '(?m)^#Requires[^\r\n]*\r?\n', ''
    $before = ([regex]::Matches($raw, '(?m)^\s*param\s*\(')).Count
    $body = Get-InstallerModuleBody $path
    $after = ([regex]::Matches($body, '(?m)^\s*param\s*\(')).Count
    $status = if ($after -eq $before) { 'OK' } else { $failures++; 'FAIL' }
    Write-Output ("[{0}] {1}: param blocks {2} -> {3}" -f $status, $rel, $before, $after)
}

# 2. A script-level param block must be removed.
$tmp = Join-Path $env:TEMP 'alfred-param-strip-test.ps1'
@'
param(
    [string]$RepoRoot,
    [switch]$Quiet
)
function Test-Inner {
    param([int]$Value = 1)
    return $Value
}
'@ | Set-Content $tmp -Encoding UTF8
$body = Get-InstallerModuleBody $tmp
Remove-Item $tmp -Force
$scriptParamGone = $body -notmatch '\$RepoRoot'
$innerParamKept = $body -match 'param\(\[int\]\$Value'
$status = if ($scriptParamGone -and $innerParamKept) { 'OK' } else { $failures++; 'FAIL' }
Write-Output ("[{0}] script-level param stripped: {1}; function param kept: {2}" -f $status, $scriptParamGone, $innerParamKept)

if ($failures -gt 0) { exit 1 }
Write-Output 'All param-strip checks passed.'
