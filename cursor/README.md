# cursor/ — Alfred Pack provisioning source of truth

Despite the folder name, this is **not Cursor-only**. `Provision-Cursor.ps1` (repo root) reads
`cursor/mcp.json` and provisions **Cursor, Claude Code, and Codex** on a fresh machine.

See [PACK.md](../PACK.md) for the full pack model. New tools land here via the **discovery loop**
(`requirements/discovered-tools.md` → promote to `mcp.json` → re-provision).

Runs automatically at the end of `setup.ps1` and `Alfred-Install.ps1`, or manually:

```powershell
# MCP servers (global) + skills (global) for Cursor, Claude Code, and Codex:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1

# Also seed Cursor rules + shared AGENTS.md into a project:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -ProjectPath C:\path\to\repo

# Only one tool:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipClaude
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipCursor
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipCodex
```

## What lands where

| Source | What it is | Destination |
|--------|-----------|-------------|
| `mcp.json` | MCP server template (`${env:VAR}` placeholders, no secrets) | `~/.cursor/mcp.json` + `claude mcp add --scope user` + `codex mcp add` |
| `skills/*.md` (repo root) | Agent + tool how-to skills | `~/.cursor/skills/`, `~/.claude/skills/`, `~/.codex/skills/` |
| `rules/*.mdc` | Cursor project rules | `<project>/.cursor/rules/` (with `-ProjectPath`) |
| `rules/*.mdc` | Global agent-tooling policy | `~/.cursor/rules/` (always synced) |
| Repo root | Agent tooling pointer | `.cursorrules` synced on every provision |
| `AGENTS.shared.md` | Cross-tool rules | `<project>/AGENTS.md` (with `-ProjectPath`) |

Third-party skills and plugins install during provision via `npx`:

| Package | Command | Destination |
|---------|---------|-------------|
| Leonxlnx/taste-skill | `npx skills add https://github.com/Leonxlnx/taste-skill` | `~/.agents/skills` |
| supabase/agent-skills | `npx skills add supabase/agent-skills` | `~/.agents/skills` |
| vercel/vercel-plugin | `npx plugins add vercel/vercel-plugin` | Cursor/Claude/Codex plugin dirs |

Vendored `taste-*.md` copies in `skills/` are **not** synced — use the official install instead.

Skills are wrapped as `alfred-<name>/SKILL.md`. Add once in `skills/` — all three agents get it on next provision.

## Adding an MCP server

Edit `mcp.json`. Metadata keys (stripped before write):

- `_requires` — env vars that must resolve or server is skipped
- `_optionalEnv` — used if present, dropped if missing
- `_requiresCommand` — CLI on PATH required (`npx`, `uvx`, etc.)
- `_cursorOnly` — deprecated; remote URL MCPs now provision to Cursor, Claude Code, and Codex
- `_note` — human description

Path tokens resolved at provision time: `${repoRoot}`, `${financeDir}`, `${dataDir}`, `${memoryDir}`, `${powerBiMcp}`.

Secrets come from Alfred `.env` at provision time into machine-local config — never committed.

## Fresh-machine checklist

After `Alfred-Install.exe` or `setup.ps1`:

1. Restart Cursor / Claude Code / Codex
2. `claude auth login` and `codex login` (once)
3. Optional: add `GITHUB_TOKEN`, `TAVILY_API_KEY` to `.env`, re-run `Provision-Cursor.ps1 -ProjectPath <repo>`
4. Power BI MCP: install VS Code extension `analysis-services.powerbi-modeling-mcp`, re-provision
