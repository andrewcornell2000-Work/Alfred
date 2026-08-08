# cursor/ — MCP catalog + rule seeds (not Cursor-only)

Despite the folder name, this is **not Cursor-only**. `Provision-Cursor.ps1` (repo root) reads
`cursor/mcp.json` as a **shared allowlist**, then installs that set into each tool
**independently** via that tool’s native method:

1. Cursor → `~/.cursor/mcp.json`
2. Claude Code → `claude mcp add/remove --scope user`
3. Codex → `codex mcp add/remove`

Claude Desktop Connectors stay **off** unless you pass `-ProvisionClaudeDesktop`.

See [PACK.md](../PACK.md). Alfred is a catalog + installer — MCP/skill identities stay
upstream/neutral (not “Alfred MCPs” / “Alfred skills”).

```powershell
# Same allowlist → Cursor, then Claude Code, then Codex (separate configs):
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -Buckets "core,powerbi,data"

# Claude Code only:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -ClaudeOnly

# Also seed Cursor rules + shared AGENTS.md into a project:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -ProjectPath C:\path\to\repo
```

## What lands where

| Source | What it is | Destination |
|--------|-----------|-------------|
| `mcp.json` | MCP allowlist template (`${env:VAR}` placeholders, no secrets) | Per-tool native install (see above) |
| `skills/*.md` (repo root) | Agent + tool how-to skills | `~/.agents/skills/<slug>/` (neutral names) |
| `rules/*.mdc` | Cursor project rules | `<project>/.cursor/rules/` (with `-ProjectPath` / `ALFRED_PROJECT_PATHS`) |
| graphify | Local AST knowledge graph | CLI via `uv tool`; rule + `graphify-out/` per seeded repo |

## Buckets

Work default: `core,powerbi,data`. Personal: `all` (adds `web`, `mediagen`, `webdev`).
