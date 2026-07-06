#Requires -Version 5.1
<#
.SYNOPSIS
    Force cooperative lean-ctx rules and strip lean-ctx Cursor hooks.
.DESCRIPTION
    Callable from Provision-Cursor.ps1 and Alfred-Install.exe (Step 10 final pass).
#>
param(
    [string]$RepoRoot,
    [switch]$SkipCursor,
    [switch]$Quiet
)

if (-not $RepoRoot) {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

function Write-RepairMsg {
    param(
        [ValidateSet('ok', 'warn', 'info')]
        [string]$Level,
        [string]$Message
    )
    if ($Quiet) { return }
    switch ($Level) {
        'ok'   { if (Get-Command Write-OK -ErrorAction SilentlyContinue) { Write-OK $Message; return }; Write-Host "  [OK]    $Message" -ForegroundColor Green }
        'warn' { if (Get-Command Write-Warn2 -ErrorAction SilentlyContinue) { Write-Warn2 $Message; return }; Write-Host "  [WARN]  $Message" -ForegroundColor Yellow }
        'info' { if (Get-Command Write-Info -ErrorAction SilentlyContinue) { Write-Info $Message; return }; Write-Host "          $Message" -ForegroundColor DarkYellow }
    }
}

function Write-TextNoBom {
    param([string]$Path, [string]$Text)
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Repair-CooperativeLeanCtxRule {
    param(
        [Parameter(Mandatory = $true)][string]$DestDir,
        [string]$SourceRoot = $RepoRoot
    )

    $src = Join-Path $SourceRoot 'cursor\rules\lean-ctx.mdc'
    if (-not (Test-Path $src)) { return $false }
    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }

    $dest = Join-Path $DestDir 'lean-ctx.mdc'
    $cooperative = Get-Content $src -Raw -Encoding UTF8
    Write-TextNoBom $dest $cooperative

    $written = Get-Content $dest -Raw -Encoding UTF8
    return ($written -match 'alfred-provision:\s*cooperative') -and
           ($written -match 'alwaysApply:\s*false') -and
           ($written -notmatch 'MANDATORY')
}

function Repair-CooperativeLeanCtxHooks {
    param([string]$HooksPath = (Join-Path $HOME '.cursor\hooks.json'))

    if (-not (Test-Path $HooksPath)) { return $true }

    $raw = Get-Content $HooksPath -Raw -Encoding UTF8
    if ($raw -notmatch 'lean-ctx') { return $true }

    try {
        $hooks = $raw | ConvertFrom-Json
        if (-not $hooks.hooks) {
            Write-RepairMsg warn 'hooks.json has no hooks object - skipping lean-ctx strip.'
            return $false
        }

        $newHookGroups = [ordered]@{}
        $removed = 0
        foreach ($prop in @($hooks.hooks.PSObject.Properties)) {
            $kept = @()
            foreach ($entry in @($prop.Value)) {
                $cmd = [string]$entry.command
                if ($cmd -match 'lean-ctx') {
                    $removed++
                    continue
                }
                $kept += $entry
            }
            if ($kept.Count -gt 0) {
                $newHookGroups[$prop.Name] = @($kept)
            }
        }

        $output = [ordered]@{
            version = if ($null -ne $hooks.version) { $hooks.version } else { 1 }
            hooks   = [pscustomobject]$newHookGroups
        }
        Write-TextNoBom $HooksPath ($output | ConvertTo-Json -Depth 30)

        $verify = Get-Content $HooksPath -Raw -Encoding UTF8
        if ($verify -match 'lean-ctx') {
            Write-RepairMsg warn "lean-ctx entries remain in hooks.json after repair."
            return $false
        }

        if ($removed -gt 0) {
            Write-RepairMsg ok "Removed $removed lean-ctx Cursor hook(s) (cooperative native-first mode)"
        }
        return $true
    } catch {
        Write-RepairMsg warn ('Could not strip lean-ctx hooks from hooks.json: ' + $_.Exception.Message)
        return $false
    }
}

function Test-CooperativeLeanCtxMode {
    param([string]$SourceRoot = $RepoRoot)

    $rulesDest = Join-Path $HOME '.cursor\rules'
    $rulePath = Join-Path $rulesDest 'lean-ctx.mdc'
    $ruleOk = $false
    if (Test-Path $rulePath) {
        $ruleText = Get-Content $rulePath -Raw -Encoding UTF8
        $ruleOk = ($ruleText -match 'alfred-provision:\s*cooperative') -and
                  ($ruleText -match 'alwaysApply:\s*false') -and
                  ($ruleText -notmatch 'MANDATORY')
    }

    $hooksOk = $true
    $hooksPath = Join-Path $HOME '.cursor\hooks.json'
    if (Test-Path $hooksPath) {
        $hooksText = Get-Content $hooksPath -Raw -Encoding UTF8
        if ($hooksText -match 'lean-ctx') { $hooksOk = $false }
    }

    return @{
        RuleOk  = $ruleOk
        HooksOk = $hooksOk
        Ok      = ($ruleOk -and $hooksOk)
    }
}

function Invoke-CooperativeLeanCtxRepair {
    param([string]$SourceRoot = $RepoRoot)

    if ($SkipCursor) { return (Test-CooperativeLeanCtxMode).Ok }

    $rulesDest = Join-Path $HOME '.cursor\rules'
    [void](Repair-CooperativeLeanCtxRule -DestDir $rulesDest -SourceRoot $SourceRoot)

    if ($SourceRoot -and (Test-Path $SourceRoot)) {
        $projectRules = Join-Path $SourceRoot '.cursor\rules'
        if (Test-Path $projectRules) {
            [void](Repair-CooperativeLeanCtxRule -DestDir $projectRules -SourceRoot $SourceRoot)
        }
    }

    [void](Repair-CooperativeLeanCtxHooks)

    $state = Test-CooperativeLeanCtxMode -SourceRoot $SourceRoot
    if ($state.Ok) {
        Write-RepairMsg ok 'Verified cooperative lean-ctx mode (optional MCP, native tools default)'
    } else {
        Write-RepairMsg warn 'lean-ctx is still in aggressive/hook mode after repair.'
        if (-not $state.RuleOk) { Write-RepairMsg info '- Rule: ~/.cursor/rules/lean-ctx.mdc should have alwaysApply: false' }
        if (-not $state.HooksOk) { Write-RepairMsg info '- Hooks: ~/.cursor/hooks.json should not contain lean-ctx entries' }
    }
    return $state.Ok
}

if ($MyInvocation.InvocationName -ne '.') {
    $ok = Invoke-CooperativeLeanCtxRepair -SourceRoot $RepoRoot
    if ($ok) { exit 0 }
    exit 1
}
