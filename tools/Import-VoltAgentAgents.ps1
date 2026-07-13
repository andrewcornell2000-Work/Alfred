<#
.SYNOPSIS
  Import selected VoltAgent subagents into Alfred/agents/ with bucket tags.

  Source: https://github.com/VoltAgent/awesome-claude-code-subagents
  License: MIT (see upstream repo)
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent),
    [switch]$Force
)

$Base = 'https://raw.githubusercontent.com/VoltAgent/awesome-claude-code-subagents/main/categories'
$AgentsDir = Join-Path $Root 'agents'
if (-not (Test-Path $AgentsDir)) { New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null }

# name -> @{ path = category/file.md; bucket = alfred-bucket }
$Catalog = [ordered]@{
    # Game development
    'game-developer'        = @{ path = '07-specialized-domains/game-developer.md'; bucket = 'cloud' }

    # Web app development (Boostl / Next.js stack)
    'nextjs-developer'      = @{ path = '02-language-specialists/nextjs-developer.md'; bucket = 'cloud' }
    'typescript-pro'        = @{ path = '02-language-specialists/typescript-pro.md'; bucket = 'core' }
    'react-specialist'      = @{ path = '02-language-specialists/react-specialist.md'; bucket = 'cloud' }
    'postgres-pro'          = @{ path = '05-data-ai/postgres-pro.md'; bucket = 'cloud' }
    'api-designer'          = @{ path = '01-core-development/api-designer.md'; bucket = 'cloud' }
    'payment-integration'   = @{ path = '07-specialized-domains/payment-integration.md'; bucket = 'cloud' }
    'fintech-engineer'      = @{ path = '07-specialized-domains/fintech-engineer.md'; bucket = 'cloud' }
    'devops-engineer'       = @{ path = '03-infrastructure/devops-engineer.md'; bucket = 'cloud' }
    'seo-specialist'        = @{ path = '07-specialized-domains/seo-specialist.md'; bucket = 'cloud' }
    'test-automator'        = @{ path = '04-quality-security/test-automator.md'; bucket = 'core' }
    'performance-engineer'  = @{ path = '04-quality-security/performance-engineer.md'; bucket = 'cloud' }

    # Quality / core
    'code-reviewer'         = @{ path = '04-quality-security/code-reviewer.md'; bucket = 'core' }
    'security-auditor'      = @{ path = '04-quality-security/security-auditor.md'; bucket = 'core' }
    'error-detective'       = @{ path = '04-quality-security/error-detective.md'; bucket = 'core' }
    'debugger'              = @{ path = '04-quality-security/debugger.md'; bucket = 'core' }
    'powershell-7-expert'   = @{ path = '02-language-specialists/powershell-7-expert.md'; bucket = 'core' }

    # Commercial / analytical work
    'data-analyst'          = @{ path = '05-data-ai/data-analyst.md'; bucket = 'data' }
    'sql-pro'               = @{ path = '02-language-specialists/sql-pro.md'; bucket = 'data' }
    'business-analyst'      = @{ path = '08-business-product/business-analyst.md'; bucket = 'data' }
    'quant-analyst'         = @{ path = '07-specialized-domains/quant-analyst.md'; bucket = 'data' }
    'research-analyst'      = @{ path = '10-research-analysis/research-analyst.md'; bucket = 'web' }
    'ab-test-analysis'      = @{ path = '10-research-analysis/ab-test-analysis.md'; bucket = 'data' }
}

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
