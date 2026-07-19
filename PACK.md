# Alfred Pack

**Alfred is not a chatbot.** It is a **Windows catalog + installer** that:

1. Installs CLIs from upstream (Claude Code, Codex, gh, pbi, …)
2. Provisions **MCP servers** into each host’s native config (Cursor, Claude Code, Codex)
3. Syncs **skills** once to `~/.agents/skills` and seeds **rules / graphify / subagents** per project
4. On update: `git pull` → upgrade packages from upstream → re-provision → doctor

## What you do day-to-day

**Work in Cursor** (or Claude Code / Codex). Just ask normally — MCPs and skills are already wired.

You do **not** open Alfred to chat or use a menu.

## What Alfred does for you

| When | What |
|------|------|
| Fresh machine | Run **`Alfred-Install.exe`** or `Alfred-Install.ps1` once |
| Weekly / after updates | Re-run **`run-alfred.bat`** (git pull → setup → provision) |
| "What's installed?" | `Alfred-Doctor.ps1` or `python -m backend.cli diagnose` |
| Claude Desktop Connectors empty | Prefer `ALFRED_SKIP_CLAUDE_DESKTOP=1` if you only use Cursor + Claude Code |

## Provision pipeline (single source of truth)

```
cursor/mcp.json          → MCP catalog (no secrets; buckets; upstream package ids)
skills/*.md              → agent how-to skills
skills/_packs/**/SKILL.md→ vendored multi-file skill packs
cursor/rules/*.mdc       → Cursor rules (per-project seed)
Provision-Cursor.ps1     → ~/.cursor/mcp.json
                         → claude mcp add --scope user
                         → codex mcp add
                         → ~/.agents/skills (single copy)
                         → retire leftover servers from prior catalogs
                         → uv tool upgrade graphifyy
```

## Work vs personal (SaaS)

- **Work** = `core,powerbi,data` — Excel, Power BI, DuckDB. PBI dashboard/visual design via Fabric skills + jean-paul. **No** supabase/vercel, **no** design MCPs (fal-ai/magic).
- **Personal / webdev** = `core,web,webdev,mediagen,data` — SaaS building: search/browse, Supabase, Vercel, design MCPs + heavy design skills.

## Secrets

Never commit API keys, tokens, or connection strings. Put them only in machine-local Alfred `.env` (gitignored). Client MCP configs may hold resolved tokens locally — never push those files to GitHub.

## Always-latest

Alfred points at upstream sources (`npx -y …@latest`, `uvx`, `uv tool upgrade`, GitHub releases). Re-running update refreshes those packages. Checked-in binaries under `bin/` are a cache, not the source of truth.
