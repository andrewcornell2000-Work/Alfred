# Alfred Install Guide

Alfred is a **global AI capability installer and updater** for Windows. It provisions skills, rules, MCP configs, and workflows to supported AI tools on your machine — without admin privileges.

## What Alfred installs

| Capability | Source in repo | Global install location |
|------------|----------------|-------------------------|
| MCP servers | `cursor/mcp.json` | Cursor: `~/.cursor/mcp.json` |
| | | Claude Code: `claude mcp add --scope user` |
| | | Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` |
| | | Codex: `codex mcp add` |
| Skills | `skills/*.md`, `_packs/`, `_vendor/` | `~/.cursor/skills/alfred-*/` |
| | | `~/.claude/skills/` |
| | | `~/.codex/skills/` |
| Cursor rules | `cursor/rules/*.mdc` | `~/.cursor/rules/` |
| lean-ctx | npm `lean-ctx-bin` + onboard | Merged into each tool's MCP config |
| Alfred repo | git clone | `%USERPROFILE%\Alfred` (default) |

**Security:** configs are user-scoped. Secrets live in `%USERPROFILE%\Alfred\.env` — never committed.

## Install methods

### Recommended: Alfred-Install.exe

1. Download from [GitHub Releases](https://github.com/andrewcornell2000-Work/Alfred/releases/latest/download/Alfred-Install.exe)
2. Run (no admin required for typical setups)
3. Confirm install path (default `%USERPROFILE%\Alfred`)
4. Follow prompts for optional API keys and CLI login
5. Success message confirms Cursor, Claude, and Codex targets

Install log: `%USERPROFILE%\Alfred\logs\install-*.log`

### Developer: Install-Alfred.bat

From a cloned repo:

```powershell
Install-Alfred.bat
```

Runs `setup.ps1` → provisions globally → validates.

## Post-install validation

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Validate-Install.ps1
```

Checks: MCP JSON validity, skill folders, Cursor rules, Claude/Codex skill sync, catalog dedup.

## Updates

```powershell
# Safe update with config backup
powershell -ExecutionPolicy Bypass -File scripts\Alfred-Update.ps1
```

Or re-run `Alfred-Install.exe`. Updates require your approval before `git pull`.

**Backup location:** `%USERPROFILE%\Alfred\logs\backups\<timestamp>\`

**Rollback:** copy backup files over current configs, then restart AI apps:

```powershell
$bak = "$env:USERPROFILE\Alfred\logs\backups\<timestamp>"
Copy-Item "$bak\mcp.json" "$env:USERPROFILE\.cursor\mcp.json" -Force
# Repeat for claude_desktop_config.json, .claude.json as needed
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| MCPs missing in Cursor | Re-run `Provision-Cursor.ps1`; restart Cursor |
| Claude Desktop Connectors empty | Re-run provision; restart Claude app |
| Skills not showing | Check `~/.cursor/skills/alfred-*`; re-provision |
| GitHub MCP skipped | Add `GITHUB_TOKEN` to `.env`; re-provision |
| lean-ctx errors | `lean-ctx doctor --fix`; re-run provision |
| Partial install | Re-run installer (idempotent) |

## Adding support for another AI app

1. Add a provision block in `Provision-Cursor.ps1` (or new `Provision-<App>.ps1`)
2. Document install paths in `requirements/capability-registry.json`
3. Extend `scripts/Validate-Install.ps1` with target checks
4. Update this guide

## Security principles

- Per-user install paths only (`%USERPROFILE%`, `%APPDATA%`)
- No auto-install of untrusted packages
- Review queue: `requirements/review-queue.json`
- Candidate validation: `python .github/scripts/review_candidate.py <candidate.json>`

See `docs/LEARNING-WORKFLOW.md` for how new capabilities are reviewed before install.
