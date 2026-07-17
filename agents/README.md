# Alfred subagents

Canonical subagent definitions for Cursor, Claude Code, and Codex.

**Design rule:** keep this list small. Prefer skills for workflows; use a subagent only when isolation or true parallelism pays for the extra context window.

## Bucket guide

| Bucket | Who it's for |
|--------|----------------|
| **core** | Universal day-to-day |
| **cloud** | Web / hosted backends (lane evals) |
| **data** | Commercial / analytical lens (lane evals) |
| **web** | (skills / MCP research — no subagents required) |
| **office365** | Excel + M365 (skills) |
| **powerbi** | Power BI + DLP Doctor |

`core` is always installed. Other buckets follow `ALFRED_BUCKETS` in `.env`.

## Active roster (Alfred-native)

| Agent | Bucket | Role |
|-------|--------|------|
| mr-smith | core | Thin router — durable handoff prompts; see `skills/prompt-handoff.md`. Prefer Cursor Plan Mode for ordinary planning. |
| design-agent | core | Jean Paul — UI design isolation |
| janitor | core | Folder clutter cleanup (delete to Recycle Bin) |
| dlp-doctor | powerbi | DLP / Labour Planning Power BI diagnostics |

### Repo A-Team (GitHub triage)

Paste one URL to **repo-scout** → parallel specialists → **ADOPT / TRIAL / SKIP** Verdict Card.

| Agent | Bucket | Role |
|-------|--------|------|
| repo-scout | core | Lead — intake, delegate, 8-section verdict |
| repo-safety-guard | core | OSS install / MCP safety (BLOCK vetoes ADOPT) |
| repo-stack-overlap | core | DUPLICATE / PARTIAL / COMPLEMENT / NEW vs Alfred |
| repo-eval-logistics | data | Warehouse / commercial analyst fit (0–5) |
| repo-eval-web | cloud | Web app shipping fit (0–5) |
| repo-eval-games | cloud | Mobile / game dev fit (0–5) |

Post-ADOPT implementation: main agent + domain skills (`alfred-supabase`, `alfred-vercel`, `jean-paul-design`) — not dedicated builder subagents.

```text
Repo Scout — evaluate https://github.com/owner/repo
```

Canonical prompt: `skills/repo-scout.md`

## VoltAgent imports (optional — not installed by default)

Generic persona agents from [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) were **removed** after a usage audit (near-zero Task invocations). Re-import only if you explicitly want them back:

```powershell
.\tools\Import-VoltAgentAgents.ps1 -Force
.\Provision-Cursor.ps1 -SyncOnly -Buckets all
```

Edit the `$Catalog` in `Import-VoltAgentAgents.ps1` to choose which personas to pull.

## Install paths (after provision)

- `~/.cursor/agents/*.md` — Cursor
- `~/.claude/agents/*.md` — Claude Code
- `~/.codex/agents/*.toml` — Codex CLI

Project-only agents (e.g. Boostl `competitive-analyst`, `session-hub`) live in each repo's `.cursor/agents/`.
