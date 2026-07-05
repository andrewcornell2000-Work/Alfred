#Requires -Version 5.1
<#
.SYNOPSIS
    Smoke test for cursor/mcp.json — no MCP health checks, no secrets written.
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$templatePath = Join-Path $Root 'cursor\mcp.json'
if (-not (Test-Path $templatePath)) {
    Write-Error "Missing template: $templatePath"
}

$tpl = Get-Content $templatePath -Raw | ConvertFrom-Json
if (-not $tpl.mcpServers) {
    Write-Error 'cursor/mcp.json has no mcpServers block'
}

$required = @('excel', 'excel-mcp', 'github', 'filesystem', 'fetch', 'duckdb', 'playwright', 'context7', 'markitdown', 'powerbi-modeling-mcp')
$retired = @('time', 'sqlite', 'sequential-thinking', 'memory', 'codegraph', 'powerbi')
$names = @($tpl.mcpServers.PSObject.Properties.Name)
$missing = $required | Where-Object { $_ -notin $names }
if ($missing.Count -gt 0) {
    Write-Error "Template missing expected servers: $($missing -join ', ')"
}
$presentRetired = $retired | Where-Object { $_ -in $names }
if ($presentRetired.Count -gt 0) {
    Write-Error "Retired servers must not be in mcpServers: $($presentRetired -join ', ')"
}
if (-not $tpl._retiredServers) {
    Write-Error 'cursor/mcp.json must define _retiredServers'
}

foreach ($prop in $tpl.mcpServers.PSObject.Properties) {
    $def = $prop.Value
    if (-not $def.command -and -not $def.url) {
        Write-Error "Server '$($prop.Name)' has no command or url"
    }
    if ($prop.Name -in @('sqlite', 'duckdb', 'fetch', 'time', 'markitdown')) {
        if ($def.command -ne 'uvx') {
            Write-Error "Server '$($prop.Name)' should use uvx, got '$($def.command)'"
        }
    }
}

Write-Host "[OK] Provision template smoke test passed ($($names.Count) servers defined)." -ForegroundColor Green
