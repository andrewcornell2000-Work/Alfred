# Alfred's Brain
*Living knowledge base — updated by learning sessions, not overwritten.*

**Home:** Alfred repo · **GitHub:** https://github.com/andrewcornell2000-Work/Alfred

---

## What Alfred Is

A Windows-first **toolchain pack**: MCPs, skills, and rules provisioned globally into Cursor, Claude Code, and Codex. Optional CLI (`backend/main.py`) routes tasks when you don't use Cursor directly.

## Current Architecture

- `backend/main.py` — `alfred_brain()` routing, Tavily search, skill injection, Codex/Claude dispatch
- `skills/` — top-level `.md` skills (keyword-matched at runtime); `_packs/` and `_vendor/` for provisioned bundles
- `cursor/mcp.json` + `Provision-Cursor.ps1` — MCP template and global wiring
- `cursor/rules/*.mdc` — Cursor agent rules (native tools default)
- `memory/` — persistent context, routing rules, learning log, instincts
- `plugins/quant/` — optional Quant Intelligence Flask plugin

## Providers

| Provider | Used for |
|----------|----------|
| `claude` | GENERAL chat, SEARCH synthesis |
| `codex` | CODE tasks |
| `claude_code` | EXECUTE, POWERBI, confirmed Dev Portal changes |
| Tavily | Live web data (direct API, not MCP) |

## Learning

- **Instincts** — `scripts/instinct-cli.py` + `memory/instincts/` (session hooks)
- **Dev Portal** — menu option 5; discuss → confirm → Claude Code dispatch
- **Cursor learning** — manual sessions per `docs/LEARNING-WORKFLOW.md` (replaces autonomous daily loop)

## Structure Reference

See **`docs/ALFRED-STRUCTURE.md`** for where rules, skills, MCPs, and web-search policy live.

## Accounts

See `memory/accounts.md`
