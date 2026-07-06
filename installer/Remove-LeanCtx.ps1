#Requires -Version 5.1
<#
.SYNOPSIS
    Remove lean-ctx MCP, hooks, rules, and skills from Alfred-provisioned agent configs.
.DESCRIPTION
    Called from Provision-Cursor.ps1 and Alfred-Install.ps1. Does not require Cursor to be closed.
#>
param(
    [string]$RepoRoot,
    [string]$ProjectPath,
    [switch]$Quiet
)

function Write-RemoveMsg {
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

function Remove-LeanCtxFromMcpJson {
    param([string]$McpPath, [string]$Label)

    if (-not (Test-Path $McpPath)) { return $false }
    try {
        $mcp = Get-Content $McpPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $mcp.mcpServers.'lean-ctx') { return $false }
        $mcp.mcpServers.PSObject.Properties.Remove('lean-ctx')
        Write-TextNoBom $McpPath ($mcp | ConvertTo-Json -Depth 30)
        Write-RemoveMsg ok "$Label : removed lean-ctx from MCP config"
        return $true
    } catch {
        Write-RemoveMsg warn "$Label MCP cleanup failed: $($_.Exception.Message)"
        return $false
    }
}

function Remove-LeanCtxCursorHooks {
    param([string]$HooksPath = (Join-Path $HOME '.cursor\hooks.json'))

    if (-not (Test-Path $HooksPath)) { return $true }
    $raw = Get-Content $HooksPath -Raw -Encoding UTF8
    if ($raw -notmatch 'lean-ctx') { return $true }

    try {
        $hooks = $raw | ConvertFrom-Json
        if (-not $hooks.hooks) { return $true }

        $newHookGroups = [ordered]@{}
        $removed = 0
        foreach ($prop in @($hooks.hooks.PSObject.Properties)) {
            $kept = @()
            foreach ($entry in @($prop.Value)) {
                if ([string]$entry.command -match 'lean-ctx') {
                    $removed++
                    continue
                }
                $kept += $entry
            }
            if ($kept.Count -gt 0) { $newHookGroups[$prop.Name] = @($kept) }
        }

        $output = [ordered]@{
            version = if ($null -ne $hooks.version) { $hooks.version } else { 1 }
            hooks   = [pscustomobject]$newHookGroups
        }
        Write-TextNoBom $HooksPath ($output | ConvertTo-Json -Depth 30)
        if ($removed -gt 0) {
            Write-RemoveMsg ok "Cursor hooks.json : removed $removed lean-ctx hook(s)"
        }
        return $true
    } catch {
        Write-RemoveMsg warn "Cursor hooks cleanup failed: $($_.Exception.Message)"
        return $false
    }
}

function Remove-LeanCtxNestedHooks {
    param(
        [Parameter(Mandatory = $true)][string]$HooksFilePath,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$HooksProperty = 'hooks'
    )

    if (-not (Test-Path $HooksFilePath)) { return $true }
    $raw = Get-Content $HooksFilePath -Raw -Encoding UTF8
    if ($raw -notmatch 'lean-ctx') { return $true }

    try {
        $doc = $raw | ConvertFrom-Json
        $hooksNode = $doc.$HooksProperty
        if (-not $hooksNode) { return $true }

        $removed = 0
        $newEvents = [ordered]@{}
        foreach ($eventProp in @($hooksNode.PSObject.Properties)) {
            $keptGroups = @()
            foreach ($group in @($eventProp.Value)) {
                $keptInner = @()
                foreach ($inner in @($group.hooks)) {
                    if ([string]$inner.command -match 'lean-ctx') {
                        $removed++
                        continue
                    }
                    $keptInner += $inner
                }
                if ($keptInner.Count -gt 0) {
                    $group.hooks = @($keptInner)
                    $keptGroups += $group
                }
            }
            if ($keptGroups.Count -gt 0) { $newEvents[$eventProp.Name] = @($keptGroups) }
        }

        $doc.PSObject.Properties.Remove($HooksProperty)
        $doc | Add-Member -NotePropertyName $HooksProperty -NotePropertyValue ([pscustomobject]$newEvents)
        Write-TextNoBom $HooksFilePath ($doc | ConvertTo-Json -Depth 30)
        if ($removed -gt 0) {
            Write-RemoveMsg ok "$Label : removed $removed lean-ctx hook(s)"
        }
        return $true
    } catch {
        Write-RemoveMsg warn "$Label hook cleanup failed: $($_.Exception.Message)"
        return $false
    }
}

function Remove-LeanCtxMarkedBlock {
    param([Parameter(Mandatory = $true)][string]$FilePath, [Parameter(Mandatory = $true)][string]$Label)

    if (-not (Test-Path $FilePath)) { return $true }
    $raw = Get-Content $FilePath -Raw -Encoding UTF8
    if ($raw -notmatch '<!--\s*lean-ctx') { return $true }

    $pattern = '(?s)\r?\n?<!--\s*lean-ctx\s*-->.*?<!--\s*/lean-ctx\s*-->\r?\n?'
    $updated = [regex]::Replace($raw, $pattern, "`n")
    if ($updated -ne $raw) {
        Write-TextNoBom $FilePath $updated.TrimEnd() + "`n"
        Write-RemoveMsg ok "$Label : removed lean-ctx block"
    }
    return $true
}

function Remove-LeanCtxPath {
    param([string]$Path, [string]$Label)

    if (-not (Test-Path $Path)) { return }
    try {
        Remove-Item $Path -Recurse -Force
        Write-RemoveMsg ok "$Label : removed $Path"
    } catch {
        Write-RemoveMsg warn "Could not remove $Path : $($_.Exception.Message)"
    }
}

function Remove-LeanCtxHookScripts {
    $hookDir = Join-Path $HOME '.cursor\hooks'
    if (-not (Test-Path $hookDir)) { return }
    Get-ChildItem $hookDir -Filter 'lean-ctx-*' -File -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            Remove-Item $_.FullName -Force
            Write-RemoveMsg ok "Removed stale hook script: $($_.Name)"
        } catch { }
    }
}

function Invoke-LeanCtxUninstall {
    if (-not (Get-Command lean-ctx -ErrorAction SilentlyContinue)) { return }
    Write-RemoveMsg info 'Running lean-ctx uninstall (non-blocking)...'
    try {
        $p = Start-Process -FilePath (Get-Command lean-ctx).Source -ArgumentList @('uninstall') `
            -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $env:TEMP "lean-ctx-uninstall.out") `
            -RedirectStandardError (Join-Path $env:TEMP "lean-ctx-uninstall.err")
        if (-not $p.WaitForExit(60000)) {
            & taskkill /PID $p.Id /T /F 2>&1 | Out-Null
            Write-RemoveMsg warn 'lean-ctx uninstall timed out — config files were still cleaned manually.'
        } elseif ($p.ExitCode -eq 0) {
            Write-RemoveMsg ok 'lean-ctx uninstall completed'
        }
    } catch {
        Write-RemoveMsg warn "lean-ctx uninstall skipped: $($_.Exception.Message)"
    }
}

function Invoke-RemoveLeanCtxFromMachine {
    param(
        [string]$SourceRoot = $RepoRoot,
        [string]$Project = $ProjectPath
    )

    $removedAny = $false

    if (Remove-LeanCtxFromMcpJson (Join-Path $HOME '.cursor\mcp.json') 'Cursor') { $removedAny = $true }
    if (Remove-LeanCtxFromMcpJson (Join-Path $HOME '.claude.json') 'Claude Code') { $removedAny = $true }

    $desktopMcp = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    if (Remove-LeanCtxFromMcpJson $desktopMcp 'Claude Desktop') { $removedAny = $true }

    [void](Remove-LeanCtxCursorHooks)
    [void](Remove-LeanCtxNestedHooks -HooksFilePath (Join-Path $HOME '.claude\settings.json') -Label 'Claude Code settings.json')
    [void](Remove-LeanCtxNestedHooks -HooksFilePath (Join-Path $HOME '.codex\hooks.json') -Label 'Codex hooks.json')

    $claudeSettings = Join-Path $HOME '.claude\settings.json'
    if (Test-Path $claudeSettings) {
        try {
            $cs = Get-Content $claudeSettings -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($cs.permissions -and $cs.permissions.allow) {
                $kept = @($cs.permissions.allow | Where-Object { $_ -notmatch 'mcp__lean-ctx__' })
                if ($kept.Count -ne @($cs.permissions.allow).Count) {
                    $cs.permissions.allow = @($kept)
                    Write-TextNoBom $claudeSettings ($cs | ConvertTo-Json -Depth 30)
                    Write-RemoveMsg ok 'Claude Code settings.json : removed lean-ctx MCP permissions'
                }
            }
        } catch { }
    }

    Remove-LeanCtxPath (Join-Path $HOME '.cursor\rules\lean-ctx.mdc') 'Cursor rule'
    Remove-LeanCtxPath (Join-Path $HOME '.claude\rules\lean-ctx.md') 'Claude rule'
    Remove-LeanCtxPath (Join-Path $HOME '.codex\LEAN-CTX.md') 'Codex LEAN-CTX.md'
    Remove-LeanCtxPath (Join-Path $HOME '.cursor\skills\lean-ctx') 'Cursor lean-ctx skill'
    Remove-LeanCtxPath (Join-Path $HOME '.claude\skills\lean-ctx') 'Claude lean-ctx skill'
    Remove-LeanCtxPath (Join-Path $HOME '.codex\skills\lean-ctx') 'Codex lean-ctx skill'

    [void](Remove-LeanCtxMarkedBlock -FilePath (Join-Path $HOME '.claude\CLAUDE.md') -Label 'Claude CLAUDE.md')
    [void](Remove-LeanCtxMarkedBlock -FilePath (Join-Path $HOME '.codex\AGENTS.md') -Label 'Codex AGENTS.md')

    Remove-LeanCtxHookScripts

    if ($Project -and (Test-Path $Project)) {
        Remove-LeanCtxFromMcpJson (Join-Path $Project '.cursor\mcp.json') 'Project Cursor' | Out-Null
        Remove-LeanCtxPath (Join-Path $Project '.cursor\rules\lean-ctx.mdc') 'Project Cursor rule'
        Remove-LeanCtxPath (Join-Path $Project 'LEAN-CTX.md') 'Project LEAN-CTX.md'
    }

    if ($SourceRoot -and (Test-Path $SourceRoot)) {
        Remove-LeanCtxPath (Join-Path $SourceRoot 'LEAN-CTX.md') 'Repo LEAN-CTX.md'
        Remove-LeanCtxPath (Join-Path $SourceRoot '.claude\rules\lean-ctx.md') 'Repo Claude lean-ctx rule'
    }

    Invoke-LeanCtxUninstall

    if (-not $Quiet) {
        Write-RemoveMsg ok 'lean-ctx removed from Alfred agent configs (native Read/Grep/Shell default)'
    }
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    Invoke-RemoveLeanCtxFromMachine -SourceRoot $RepoRoot -Project $ProjectPath | Out-Null
    exit 0
}
