# Alfred Pack

**Alfred is not a chatbot.** It is a **Windows catalog + installer** that:

1. Installs CLIs from upstream (Claude Code, Codex, gh, pbi, …)
2. Provisions the **same MCP allowlist** into each host **independently** via that host’s native method (Cursor file / `claude mcp` / `codex mcp`)
3. Syncs **skills** once to `~/.agents/skills` with **neutral names** (no `alfred-` prefix) and seeds **rules / graphify / subagents** per project
4. On update: `git pull` → upgrade packages from upstream → re-provision → doctor

MCP servers and skills keep their own identities — Alfred does not rebrand them as “Alfred MCPs” or “Alfred skills.”

## What you do day-to-day

**Work in Cursor** (or Claude Code / Codex). Just ask normally — MCPs and skills are already wired.

You do **not** open Alfred to chat or use a menu.

## What Alfred does for you

| When | What |
|------|------|
| Fresh machine | Run **`Alfred-Install.exe`** or `Alfred-Install.ps1` once |
| Weekly / after updates | Re-run **`run-alfred.bat`** (git pull → setup → provision) |
| "What's installed?" | `Alfred-Doctor.ps1` or `python -m backend.cli diagnose` |
| Claude Desktop Connectors | Off by default; opt in with `-ProvisionClaudeDesktop` / `ALFRED_PROVISION_CLAUDE_DESKTOP=1` |

## Provision pipeline (surgical per tool)

```
cursor/mcp.json          → shared MCP allowlist (no secrets; buckets; upstream ids)
skills/*.md              → catalog how-to skills (neutral slugs)
skills/_packs/**/SKILL.md→ vendored multi-file skill packs
cursor/rules/*.mdc       → Cursor rules (per-project seed)
Provision-Cursor.ps1
  Install-McpCursor      → ~/.cursor/mcp.json (+ retire)
  Install-McpClaude      → claude mcp add/remove --scope user
  Install-McpCodex       → codex mcp add/remove
  (Desktop Connectors)   → skipped unless opted in
  skills                 → ~/.agents/skills/<slug>/ (single copy, no alfred- prefix)
  self-heal              → remove catalog drift per tool independently
```

## Work vs personal (SaaS)

- **Work** = `core,powerbi,data` — Excel, Power BI, DuckDB. PBI dashboard/visual design via Fabric skills + jean-paul. **No** supabase/vercel, **no** design MCPs (fal-ai/magic).
- **Personal / webdev** = `core,web,webdev,mediagen,data` — SaaS building: search/browse, Supabase, Vercel, design MCPs + heavy design skills.

## Secrets

Never commit API keys, tokens, or connection strings. Put them only in machine-local Alfred `.env` (gitignored). Client MCP configs may hold resolved tokens locally — never push those files to GitHub.

## Always-latest

Alfred points at upstream sources (`npx -y …@latest`, `uvx`, `uv tool upgrade`, GitHub releases). Re-running update refreshes those packages. Checked-in binaries under `bin/` are a cache, not the source of truth.
