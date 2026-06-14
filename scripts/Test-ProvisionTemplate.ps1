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

$required = @('excel', 'github', 'filesystem', 'fetch', 'time', 'sqlite', 'duckdb')
$names = @($tpl.mcpServers.PSObject.Properties.Name)
$missing = $required | Where-Object { $_ -notin $names }
if ($missing.Count -gt 0) {
    Write-Error "Template missing expected servers: $($missing -join ', ')"
}

foreach ($prop in $tpl.mcpServers.PSObject.Properties) {
    $def = $prop.Value
    if (-not $def.command) {
        Write-Error "Server '$($prop.Name)' has no command"
    }
    if ($prop.Name -in @('sqlite', 'duckdb', 'fetch', 'time', 'markitdown')) {
        if ($def.command -ne 'uvx') {
            Write-Error "Server '$($prop.Name)' should use uvx, got '$($def.command)'"
        }
    }
}

Write-Host "[OK] Provision template smoke test passed ($($names.Count) servers defined)." -ForegroundColor Green
