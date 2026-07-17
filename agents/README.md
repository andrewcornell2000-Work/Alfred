# Alfred subagents

Canonical subagent definitions for Cursor, Claude Code, and Codex.

**Design rule:** keep this list tiny. Prefer skills for workflows; use a subagent only when isolation or destructive work needs a hard boundary. Cursor/Claude Plan Mode covers planning — do not add planner personas.

## Bucket guide

| Bucket | Who it's for |
|--------|----------------|
| **core** | Universal day-to-day |
| **powerbi** | Power BI + DLP Doctor |
| **cloud / data / web / office365** | Skills + MCPs (no extra subagents required) |

`core` is always installed. Other buckets follow `ALFRED_BUCKETS` in `.env`.

## Active roster (3)

| Agent | Bucket | Role |
|-------|--------|------|
| design-agent | core | Jean Paul — UI design isolation |
| janitor | core | Folder clutter cleanup (delete to Recycle Bin) |
| dlp-doctor | powerbi | DLP / Labour Planning Power BI diagnostics |

## Skills that replaced subagents

| Former agents | Use instead |
|---------------|-------------|
| Repo A-Team (6) | [`skills/repo-scout.md`](../skills/repo-scout.md) in the **current** agent |
| mr-smith | [`skills/prompt-handoff.md`](../skills/prompt-handoff.md); Plan Mode for ordinary plans |

GitHub URL triage auto-route: `.cursor/rules/repo-scout-routing.mdc` → skill only, no Task fan-out.

## VoltAgent imports (optional — not installed)

```powershell
.\tools\Import-VoltAgentAgents.ps1 -Force   # catalog empty by default
.\Provision-Cursor.ps1 -SyncOnly
```

## Install paths (after provision)

- `~/.cursor/agents/*.md` — Cursor
- `~/.claude/agents/*.md` — Claude Code
- `~/.codex/agents/*.toml` — Codex CLI

Project-only agents (e.g. Boostl `competitive-analyst`, `session-hub`) live in each repo's `.cursor/agents/`.
