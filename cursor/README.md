# cursor/ — Alfred provisioning source of truth

Despite the folder name, this is **not Cursor-only**. `Provision-Cursor.ps1` (repo root) reads
`cursor/mcp.json` and provisions **Cursor, Claude Code, and Codex**.

See [PACK.md](../PACK.md). Alfred is a catalog + installer — add tools to `mcp.json` / skills, then re-provision.

```powershell
# MCP servers + skills for Cursor, Claude Code, and Codex:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -Buckets "core,powerbi,data"

# Also seed Cursor rules + shared AGENTS.md into a project:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -ProjectPath C:\path\to\repo
```

## What lands where

| Source | What it is | Destination |
|--------|-----------|-------------|
| `mcp.json` | MCP server template (`${env:VAR}` placeholders, no secrets) | `~/.cursor/mcp.json` + `claude mcp add --scope user` + `codex mcp add` |
| `skills/*.md` (repo root) | Agent + tool how-to skills | `~/.agents/skills` (single copy) |
| `rules/*.mdc` | Cursor project rules | `<project>/.cursor/rules/` (with `-ProjectPath` / `ALFRED_PROJECT_PATHS`) |
| graphify | Local AST knowledge graph | CLI via `uv tool`; rule + `graphify-out/` per seeded repo |

## Buckets

Work default: `core,powerbi,data`. Personal: `all` (adds `web`, `mediagen`, `cloud`).
