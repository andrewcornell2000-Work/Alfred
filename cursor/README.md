# cursor/ - cross-tool provisioning source of truth

This folder is the single place Alfred reads when it provisions a machine's AI dev tools.
`Provision-Cursor.ps1` (in the repo root) consumes it and writes config into **both Cursor and
Claude Code**, so the same MCP servers, skills, and rules are available no matter which tool you open.

It runs automatically as part of `setup.ps1` (so it also re-runs after every Alfred update), or you
can run it on its own:

```powershell
# MCP servers (global) + skills (global) for both Cursor and Claude Code:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1

# Also seed Cursor rules + a shared AGENTS.md into a specific project:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -ProjectPath C:\path\to\repo

# Only one tool:
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipClaude   # Cursor only
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipCursor   # Claude Code only
```

## What lives here

| Path | What it is | Where it lands |
|------|-----------|----------------|
| `mcp.json` | MCP server manifest (template; `${env:VAR}` placeholders, **no secrets**) | `~/.cursor/mcp.json` (Cursor, global) + `claude mcp add --scope user` (Claude Code, all projects) |
| `rules/*.mdc` | Cursor project rules | `<project>/.cursor/rules/` (only with `-ProjectPath`) |
| `AGENTS.shared.md` | Cross-tool rules | `<project>/AGENTS.md` (only with `-ProjectPath`; never overwrites an existing one) |

Skills are **not** stored here - they are synced from the repo's top-level `skills/*.md`, wrapped as
`alfred-<name>/SKILL.md`, into `~/.cursor/skills/` and `~/.claude/skills/`. Add a skill once in
`skills/` and it reaches both tools.

## Adding / changing an MCP server

Edit `mcp.json`. Each server may carry provisioner metadata (stripped before anything is written):

- `_requires`: env var names that **must** resolve or the server is skipped (e.g. `GITHUB_PERSONAL_ACCESS_TOKEN`).
- `_optionalEnv`: env vars used if present, dropped if not (e.g. `CONTEXT7_API_KEY`).
- `_requiresCommand`: a CLI that must be on PATH or the server is skipped (e.g. `python` for `excel`).
- `_note`: human description.

Secrets are read from Alfred's `.env` (or machine environment) at provision time and written into
`~/.cursor/mcp.json`, which is machine-local and never committed. This mirrors the hard rule in
`requirements/mcp-tools.md`: never store credentials in a committed manifest.

> Power BI MCP is intentionally **not** auto-configured here: its command is a machine-specific VS Code
> extension path. See `requirements/mcp-tools.md` to wire it per machine.
