<#
.SYNOPSIS
  Optionally import selected VoltAgent subagents into Alfred/agents/ with bucket tags.

  Source: https://github.com/VoltAgent/awesome-claude-code-subagents
  License: MIT (see upstream repo)

  Default catalog is EMPTY — Alfred ships a small native roster only.
  Add entries to $Catalog below if you explicitly want VoltAgent personas back,
  then run with -Force and re-provision.
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent),
    [switch]$Force
)

$Base = 'https://raw.githubusercontent.com/VoltAgent/awesome-claude-code-subagents/main/categories'
$AgentsDir = Join-Path $Root 'agents'
if (-not (Test-Path $AgentsDir)) { New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null }

# name -> @{ path = category/file.md; bucket = alfred-bucket }
# Examples (uncomment / add as needed):
#   'nextjs-developer' = @{ path = '02-language-specialists/nextjs-developer.md'; bucket = 'cloud' }
#   'code-reviewer'    = @{ path = '04-quality-security/code-reviewer.md'; bucket = 'core' }
$Catalog = [ordered]@{}

$AlfredPreamble = @'

## Alfred toolchain

When the workspace has `graphify-out/graph.json`, run `graphify query "<question>"` before broad Read/Grep exploration. After code changes, run `graphify update .` to refresh the graph.

Use Alfred MCP buckets as configured on this machine (see `Alfred/cursor/mcp.json` `_buckets`). Prefer native repo tools for code; use MCPs for external systems (Supabase, Vercel, Excel, DuckDB, etc.).

'@

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Add-BucketToFrontmatter([string]$Content, [string]$Bucket) {
    if ($Content -match '(?ms)^---\s*\r?\n(.*?\r?\n)---') {
        $fm = $Matches[1]
        if ($fm -match '(?m)^\s*bucket:\s*') {
            $fm = $fm -replace '(?m)^\s*bucket:\s*.*$', "bucket: $Bucket"
        } else {
            $fm = $fm.TrimEnd() + "`nbucket: $Bucket`n"
        }
        return $Content -replace '(?ms)^---\s*\r?\n.*?\r?\n---', "---`n$fm---"
    }
    return "---`nbucket: $Bucket`n---`n`n" + $Content
}

if ($Catalog.Count -eq 0) {
    Write-Host "Catalog is empty (Alfred default). Add agents to `$Catalog in this script, then re-run with -Force." -ForegroundColor Yellow
    Write-Host "Native roster lives in agents/ — see agents/README.md." -ForegroundColor DarkGray
    exit 0
}

$imported = 0
$skipped = 0
foreach ($name in $Catalog.Keys) {
    $meta = $Catalog[$name]
    $dest = Join-Path $AgentsDir "$name.md"
    if ((Test-Path $dest) -and -not $Force) {
        Write-Host "  skip $name (exists; use -Force)" -ForegroundColor DarkGray
        $skipped++
        continue
    }
    $url = "$Base/$($meta.path)"
    try {
        $raw = (Invoke-WebRequest -Uri $url -UseBasicParsing).Content
    } catch {
        Write-Warning "Failed to fetch $name from $url : $_"
        continue
    }
    if (-not $raw -or $raw.Length -lt 50) {
        Write-Warning "Empty response for $name"
        continue
    }
    $withBucket = Add-BucketToFrontmatter $raw $meta.bucket
    if ($withBucket -notmatch '## Alfred toolchain') {
        $withBucket = $withBucket.TrimEnd() + "`n" + $AlfredPreamble
    }
    Write-Utf8NoBom $dest $withBucket
    Write-Host "  OK $name -> bucket:$($meta.bucket)" -ForegroundColor Green
    $imported++
}

Write-Host "`nImported $imported agent(s), skipped $skipped." -ForegroundColor Cyan
