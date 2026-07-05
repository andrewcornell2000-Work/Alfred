# Alfred Capability Registry
*Version: 2026-07-05*

## Purpose

Documents what Alfred **provisions** and how capabilities map to MCPs and providers.

Use **`python -m backend.cli diagnose`** for live readiness on this machine.

## Categories (registry metadata)

| Category | Meaning | Typical provider in Cursor |
|---|---|---|
| `GENERAL` | Conversation, explanation, planning | Claude |
| `SEARCH` | Live web data | Claude (+ Tavily when configured) |
| `CODE` | Write, fix, refactor, test code | Codex |
| `EXECUTE` | Files, MCP-heavy work, Office, browser, GitHub | Claude Code |
| `POWERBI` | Power BI, Power Query, DAX | Claude Code + Power BI MCP |

## Providers (for skill authors)

| Provider | Handles |
|---|---|
| `claude` | General answers, search-augmented responses |
| `codex` | Code changes, tests, implementation |
| `claude_code` | MCP-heavy execution (Excel, Power BI, files, browser) |

## Registry source of truth

- **Code:** `backend/provision/registry.py` — `TOOL_REGISTRY`, `register_tool()`
- **Shim:** `backend/routing/registry.py` re-exports for backward compatibility
- **Diagnostics:** `iter_control_tower_capabilities()` feeds `backend.cli diagnose`

## Safety (skill and manifest authors)

Destructive-operation guidance: **`requirements/safety-gates.md`**

## Adding a new capability

1. Add entry to `TOOL_REGISTRY` in `backend/provision/registry.py`
2. Add MCP entry to `cursor/mcp.json` + `requirements/alfred-tools.json` if tool-backed
3. Run `Provision-Cursor.ps1`
4. Run `python -m backend.cli validate`
5. Update this file if the capability is user-visible

## Files to keep in sync

1. `backend/provision/registry.py`
2. `cursor/mcp.json` + `requirements/alfred-tools.json`
3. `requirements/safety-gates.md` (if destructive)
4. This file
