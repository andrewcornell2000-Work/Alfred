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

# ── Claude Code / Codex: nested hook format ({hooks:[{command}], matcher}) ────

function Repair-CooperativeNestedHooks {
    param(
        [Parameter(Mandatory = $true)][string]$HooksFilePath,
        [Parameter(Mandatory = $true)][string]$Label,
        # settings.json keeps sibling keys (env, permissions, theme); hooks.json is hooks-only.
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
            if ($keptGroups.Count -gt 0) {
                $newEvents[$eventProp.Name] = @($keptGroups)
            }
        }

        $doc.PSObject.Properties.Remove($HooksProperty)
        $doc | Add-Member -NotePropertyName $HooksProperty -NotePropertyValue ([pscustomobject]$newEvents)
        Write-TextNoBom $HooksFilePath ($doc | ConvertTo-Json -Depth 30)

        $verify = Get-Content $HooksFilePath -Raw -Encoding UTF8
        # MCP allowlist entries (mcp__lean-ctx__ctx_*) are fine; only hook commands matter.
        $hookCmdsLeft = ($verify | ConvertFrom-Json).$HooksProperty
        $stillAggressive = $false
        if ($hookCmdsLeft) {
            foreach ($eventProp in @($hookCmdsLeft.PSObject.Properties)) {
                foreach ($group in @($eventProp.Value)) {
                    foreach ($inner in @($group.hooks)) {
                        if ([string]$inner.command -match 'lean-ctx') { $stillAggressive = $true }
                    }
                }
            }
        }
        if ($stillAggressive) {
            Write-RepairMsg warn "$Label : lean-ctx hooks remain after repair."
            return $false
        }
        if ($removed -gt 0) {
            Write-RepairMsg ok "$Label : removed $removed lean-ctx hook(s)"
        }
        return $true
    } catch {
        Write-RepairMsg warn ("$Label hook repair failed: " + $_.Exception.Message)
        return $false
    }
}

# ── Cooperative content blocks ────────────────────────────────────────────────

$script:CooperativeLeanCtxBlock = @'
<!-- lean-ctx -->
## lean-ctx

Optional token saver for large reads, re-reads, and `ctx_knowledge`. **Native Read/Grep/Shell remain the default.**

If lean-ctx MCP errors or hangs (>5s), use native tools for the rest of the turn.
NEVER run `lean-ctx onboard`, `lean-ctx setup`, or `lean-ctx doctor --fix` — they reinstall aggressive
always-on rules and Read/Grep/Shell redirect hooks. To repair lean-ctx, re-run Alfred's Provision-Cursor.ps1.
<!-- /lean-ctx -->
'@

function Repair-CooperativeMarkedBlock {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path $FilePath)) { return $true }
    $raw = Get-Content $FilePath -Raw -Encoding UTF8
    if ($raw -notmatch '<!-- lean-ctx') { return $true }
    if ($raw -match 'NEVER run `lean-ctx onboard`') { return $true }

    $pattern = '(?s)<!--\s*lean-ctx\s*-->.*?<!--\s*/lean-ctx\s*-->'
    if ($raw -match $pattern) {
        $updated = [regex]::Replace($raw, $pattern, { $script:CooperativeLeanCtxBlock.Trim() })
        Write-TextNoBom $FilePath $updated
        Write-RepairMsg ok "$Label : replaced aggressive lean-ctx block with cooperative version"
    }
    return $true
}

function Repair-CooperativeClaudeRule {
    param([string]$RulePath = (Join-Path $HOME '.claude\rules\lean-ctx.md'))

    if (-not (Test-Path (Split-Path $RulePath -Parent))) { return $true }
    $existing = if (Test-Path $RulePath) { Get-Content $RulePath -Raw -Encoding UTF8 } else { '' }
    if ($existing -match 'alfred-provision:\s*cooperative' -and $existing -notmatch 'MANDATORY') { return $true }

    Write-TextNoBom $RulePath @'
# lean-ctx — optional (Alfred cooperative mode)
<!-- alfred-provision: cooperative — do not replace with lean-ctx onboard defaults -->

Native Read/Grep/Shell/Edit are the default. Use lean-ctx only for large file maps,
compressed shell output, or `ctx_knowledge` session memory.

If lean-ctx MCP errors or hangs (>5s), stop using it for the rest of the turn.
NEVER run `lean-ctx onboard`, `lean-ctx setup`, or `lean-ctx doctor --fix` — they reinstall
aggressive always-on rules and redirect hooks. Repair via Alfred's Provision-Cursor.ps1 instead.
'@
    Write-RepairMsg ok 'Claude rules: lean-ctx.md -> cooperative native-first'
    return $true
}

function Repair-CooperativeCodexLeanFile {
    param([string]$FilePath = (Join-Path $HOME '.codex\LEAN-CTX.md'))

    if (-not (Test-Path (Split-Path $FilePath -Parent))) { return $true }
    $existing = if (Test-Path $FilePath) { Get-Content $FilePath -Raw -Encoding UTF8 } else { '' }
    if ($existing -match 'alfred-provision:\s*cooperative') { return $true }
    if (-not (Test-Path $FilePath)) { return $true }

    Write-TextNoBom $FilePath @'
# lean-ctx — optional (Alfred cooperative mode)
<!-- alfred-provision: cooperative — do not replace with lean-ctx onboard defaults -->

Native shell, file reads, and search are the default. Use lean-ctx (`ctx_shell`, `ctx_read`,
`ctx_search` MCP tools or `lean-ctx -c "<cmd>"`) only for very large outputs or re-reads.

If lean-ctx errors or hangs (>5s), use native tools for the rest of the turn.
NEVER run `lean-ctx onboard`, `lean-ctx setup`, or `lean-ctx doctor --fix` — they reinstall
aggressive hooks. Repair via Alfred's Provision-Cursor.ps1 instead.
'@
    Write-RepairMsg ok 'Codex: LEAN-CTX.md -> cooperative native-first'
    return $true
}

function Repair-CooperativeLeanCtxSkill {
    # lean-ctx's own skill triggers on every read/shell/search and tells agents to run
    # `lean-ctx setup` (which reinstalls aggressive hooks). Replace with a cooperative skill.
    $skillBody = @'
---
name: lean-ctx
description: Optional lean-ctx context-compression helpers (Alfred cooperative mode). Use ONLY when the user explicitly asks for lean-ctx or token compression, or for mapping very large files. Native Read/Grep/Shell remain the default.
---

# lean-ctx — optional context compression (Alfred cooperative mode)

<!-- alfred-provision: cooperative — do not replace with lean-ctx onboard defaults -->

Native Read/Grep/Shell/Edit are the default. lean-ctx is an optional MCP for:

- Large file overviews: `ctx_read(path, "map")`
- Compressed shell output: `ctx_shell(command)` or `lean-ctx -c "<cmd>"`
- Session memory: `ctx_knowledge`, `ctx_session`

If any lean-ctx call errors or takes >5s, use native tools for the rest of the turn.

NEVER run `lean-ctx onboard`, `lean-ctx setup`, or `lean-ctx doctor --fix` — they overwrite
Alfred's cooperative config with aggressive always-on rules and Read/Grep/Shell redirect hooks.
If lean-ctx breaks, re-run Alfred's Provision-Cursor.ps1.
'@

    foreach ($dir in @(
        (Join-Path $HOME '.claude\skills\lean-ctx'),
        (Join-Path $HOME '.cursor\skills\lean-ctx'),
        (Join-Path $HOME '.codex\skills\lean-ctx')
    )) {
        $skillPath = Join-Path $dir 'SKILL.md'
        if (-not (Test-Path $skillPath)) { continue }
        $existing = Get-Content $skillPath -Raw -Encoding UTF8
        if ($existing -match 'alfred-provision:\s*cooperative') { continue }
        Write-TextNoBom $skillPath $skillBody
        Write-RepairMsg ok "Skill: $skillPath -> cooperative (no auto-setup trigger)"
    }
    return $true
}

function Remove-LeanCtxCursorHookScripts {
    # Stale redirect/rewrite scripts left by `lean-ctx onboard`. Inert once hooks.json is
    # clean, but removing them prevents any future re-activation.
    $hookDir = Join-Path $HOME '.cursor\hooks'
    if (-not (Test-Path $hookDir)) { return $true }
    $stale = Get-ChildItem $hookDir -Filter 'lean-ctx-*' -File -ErrorAction SilentlyContinue
    foreach ($f in $stale) {
        try {
            Remove-Item $f.FullName -Force
            Write-RepairMsg ok "Removed stale lean-ctx hook script: $($f.Name)"
        } catch {
            Write-RepairMsg warn "Could not remove $($f.Name): $($_.Exception.Message)"
        }
    }
    return $true
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

    $claudeOk = $true
    $claudeSettings = Join-Path $HOME '.claude\settings.json'
    if (Test-Path $claudeSettings) {
        try {
            $cs = Get-Content $claudeSettings -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($eventProp in @($cs.hooks.PSObject.Properties)) {
                foreach ($group in @($eventProp.Value)) {
                    foreach ($inner in @($group.hooks)) {
                        if ([string]$inner.command -match 'lean-ctx') { $claudeOk = $false }
                    }
                }
            }
        } catch { }
    }
    $claudeRule = Join-Path $HOME '.claude\rules\lean-ctx.md'
    if (Test-Path $claudeRule) {
        if ((Get-Content $claudeRule -Raw -Encoding UTF8) -match 'MANDATORY') { $claudeOk = $false }
    }

    $codexOk = $true
    $codexHooks = Join-Path $HOME '.codex\hooks.json'
    if (Test-Path $codexHooks) {
        if ((Get-Content $codexHooks -Raw -Encoding UTF8) -match 'lean-ctx') { $codexOk = $false }
    }

    return @{
        RuleOk   = $ruleOk
        HooksOk  = $hooksOk
        ClaudeOk = $claudeOk
        CodexOk  = $codexOk
        Ok       = ($ruleOk -and $hooksOk -and $claudeOk -and $codexOk)
    }
}

function Invoke-CooperativeLeanCtxRepair {
    param([string]$SourceRoot = $RepoRoot)

    if (-not $SkipCursor) {
        $rulesDest = Join-Path $HOME '.cursor\rules'
        [void](Repair-CooperativeLeanCtxRule -DestDir $rulesDest -SourceRoot $SourceRoot)

        if ($SourceRoot -and (Test-Path $SourceRoot)) {
            $projectRules = Join-Path $SourceRoot '.cursor\rules'
            if (Test-Path $projectRules) {
                [void](Repair-CooperativeLeanCtxRule -DestDir $projectRules -SourceRoot $SourceRoot)
            }
        }

        [void](Repair-CooperativeLeanCtxHooks)
        [void](Remove-LeanCtxCursorHookScripts)
    }

    # Claude Code: hooks in settings.json, global CLAUDE.md block, rules file.
    [void](Repair-CooperativeNestedHooks -HooksFilePath (Join-Path $HOME '.claude\settings.json') -Label 'Claude Code settings.json')
    [void](Repair-CooperativeMarkedBlock -FilePath (Join-Path $HOME '.claude\CLAUDE.md') -Label 'Claude Code CLAUDE.md')
    [void](Repair-CooperativeClaudeRule)

    # Codex: hooks.json, global AGENTS.md block, LEAN-CTX.md.
    [void](Repair-CooperativeNestedHooks -HooksFilePath (Join-Path $HOME '.codex\hooks.json') -Label 'Codex hooks.json')
    [void](Repair-CooperativeMarkedBlock -FilePath (Join-Path $HOME '.codex\AGENTS.md') -Label 'Codex AGENTS.md')
    [void](Repair-CooperativeCodexLeanFile)

    # Skills: neutralise lean-ctx's own aggressive skill in all agent skill dirs.
    [void](Repair-CooperativeLeanCtxSkill)

    $state = Test-CooperativeLeanCtxMode -SourceRoot $SourceRoot
    if ($state.Ok) {
        Write-RepairMsg ok 'Verified cooperative lean-ctx mode across Cursor, Claude Code, and Codex'
    } else {
        Write-RepairMsg warn 'lean-ctx is still in aggressive/hook mode after repair.'
        if (-not $state.RuleOk) { Write-RepairMsg info '- Rule: ~/.cursor/rules/lean-ctx.mdc should have alwaysApply: false' }
        if (-not $state.HooksOk) { Write-RepairMsg info '- Hooks: ~/.cursor/hooks.json should not contain lean-ctx entries' }
        if (-not $state.ClaudeOk) { Write-RepairMsg info '- Claude: ~/.claude/settings.json hooks + ~/.claude/rules/lean-ctx.md should be cooperative' }
        if (-not $state.CodexOk) { Write-RepairMsg info '- Codex: ~/.codex/hooks.json should not contain lean-ctx entries' }
    }
    return $state.Ok
}

if ($MyInvocation.InvocationName -ne '.') {
    $ok = Invoke-CooperativeLeanCtxRepair -SourceRoot $RepoRoot
    if ($ok) { exit 0 }
    exit 1
}
