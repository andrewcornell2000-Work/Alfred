# Alfred Session Summary
*Last updated: 2026-05-28*

## Current Architecture

- **Entry point:** `backend/main.py` — all logic consolidated in one file
- **Routing brain:** `alfred_brain()` — single Claude CLI call classifies intent, selects provider, and optionally generates a multi-step plan; keyword fallback when Claude is unavailable
- **Providers:** Claude Code CLI (`claude -p`) for chat, execution, MCP tasks; Codex CLI (`codex`) for code changes and refactoring; Quant plugin API for market intelligence
- **Web search:** Tavily direct API (`_tavily_search()`) — no MCP needed; injected into execution scope when `needs_search=true`
- **Execution model:** `run_claude()` / `run_codex()` with 300s timeout; `_render_execution_result()` parses JSON summary/next-step fields for clean output
- **Multi-step tasks:** `_run_step_sequence()` — compound requests decomposed into 2–5 steps; each step feeds context forward; single approval before sequence starts
- **Terminal UI:** `rich.console.Console`; panels for plans, results, and memory; no verbose provider headers shown to user
- **Environment:** `.env` manages `TAVILY_API_KEY`, `GITHUB_TOKEN`, `QUANT_BASE_URL`; no OpenAI key required
- **Memory:** Hot context (`current-focus.md`, `recent-context.md`, `active-projects.md`, `notes.md`) injected into LLM calls; `autosave.md` excluded from injection (raw logs only); full dump available in Memory viewer

## Capability Registry

| Capability | Provider | Category |
|---|---|---|
| General Chat | Claude | GENERAL |
| Web Research | Tavily + Claude | SEARCH |
| Code & Refactoring | Codex | CODE |
| File & System Operations | Claude Code | EXECUTE |
| Excel Automation | Claude Code + MCP | EXECUTE |
| Power BI | Claude Code + MCP | POWERBI |
| Browser Automation | Claude Code + Playwright MCP | EXECUTE |
| GitHub Operations | Claude Code + GitHub MCP | EXECUTE |
| Office Documents | Claude Code | EXECUTE |
| Market Intelligence | Quant plugin | QUANT |

## Request Flow

1. **Brain:** `alfred_brain()` → JSON decision: `{category, provider, needs_search, needs_clarification, steps[]}`
2. **Clarification:** If `needs_clarification=true`, Alfred asks one targeted question before dispatching
3. **Multi-step detection:** If `steps[]` has 2+ items, show numbered plan, one approval, then `_run_step_sequence()`
4. **Single-step execution:** `generate_claude_scope()` → plan panel → confirm → `run_claude()` / `run_codex()`
5. **QUANT:** Routes directly to Quant plugin API without scope generation
6. **GENERAL/SEARCH:** `generate_general_response()` with optional Tavily pre-fetch; no dispatch
7. **Memory:** `append_autosave_entry()` after every interaction; compresses to `session-summary.md` after 10 entries

## Safety Rules

- **Dangerous keywords** block automatic dispatch: `delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`
- **Action keywords** trigger POWERBI dispatch: `inspect`, `run`, `edit`, `use mcp`, `use claude`
- **Learning / Creator Mode:** Detects self-modification requests → discussion → confirm → Codex dispatch
- **Execution timeouts:** `run_claude()` and `run_codex()` both have 300s timeout — Alfred never hangs
- **Auto-repair:** `_check_setup()` at startup shows numbered issue list; repair functions run in-place

## Memory System

- `memory/current-focus.md` — what you're working on (updated at session exit)
- `memory/recent-context.md` — recent decisions and outcomes (updated at session exit)
- `memory/session-summary.md` — this file; full architecture reference (compressed from autosave)
- `memory/autosave.md` — raw interaction log; gitignored; excluded from LLM injection
- `memory/notes.md` — quick notes via "remember: X" command
- `memory/active-projects.md` — active project tracking
- Compression threshold: 10 autosave entries → consolidated into summary + recent-context

## Current Skills

- `skills/powerquery-column-errors.md` — diagnose Power Query column errors by inspecting Transform steps

## Implemented Since Initial Build (chronological highlights)

1. Alfred Brain — unified LLM routing replacing keyword-only classification
2. Capability registry — single source of truth for Control Tower and Brain prompt
3. Mid-task clarification — Brain asks one targeted question before dispatch
4. Clean execution output — summary/next-step only, no provider/category headers
5. Auto-repair setup failures — interactive numbered issue list at startup
6. Multi-step task decomposition — compound requests execute step by step with context forwarding
7. Execution timeouts — 300s ceiling on run_claude / run_codex
8. Unified session memory — hot memory injection, startup briefing, "remember" command
9. OpenAI / Brave Search fully removed from all user-facing surfaces
10. Tavily direct API replaces Brave Search MCP

## Next Planned Features

- **Unified identity / session management** — single Alfred login managing all provider sessions
- **Agent workflows** — background tasks, scheduled tasks, persistent workspaces
