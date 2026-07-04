# Alfred Worker Routing Rules
*Version: 2026-07-04*

## Purpose

Alfred routes each request to the cheapest capable path. Heavy providers (Codex, Claude Code) are used only when the task needs code execution, file work, MCP tools, or Power BI.

## Categories (`alfred_brain()`)

| Category | Meaning | Default provider |
|----------|---------|------------------|
| `GENERAL` | Conversation, explanation, planning | `claude` |
| `SEARCH` | Live/current data (news, versions, prices, docs) | `claude` + Tavily |
| `CODE` | Repo code, tests, refactors, Alfred self-modification | `codex` |
| `EXECUTE` | Files, scripts, Excel, browser, GitHub, Office | `claude_code` |
| `POWERBI` | Models, DAX, Power Query, visuals | `claude_code` |

## Routing Priority

1. **Explicit override** — `use claude`, `use codex`, `with claude`, `via codex`, etc. (`detect_provider_override()`)
2. **Brain JSON** — `alfred_brain()` category + provider (primary)
3. **Keyword fallback** — if brain unavailable: Power BI keywords → `POWERBI`; Codex vs Claude keyword scores → `CODE` / `EXECUTE`; else `GENERAL`

## Web Search (Tavily)

Search runs when:
- Category is `SEARCH`, or
- Brain sets `needs_search: true`, or
- `_should_search()` matches **explicit** recency/lookup keywords (not every question)

Search does **not** run for meta commands (`back`, `menu`, `exit`) or short inputs.

See `skills/web-search.md` for Alfred CLI rules. In Cursor, use `parallel-search` or `fetch` MCP per `skills/mcp-routing.md`.

## Auto-Dispatch Gate

Auto-dispatch to Codex or Claude Code when:
- Provider is `codex` or `claude_code`
- Category is `CODE`, `EXECUTE`, or `POWERBI`
- No dangerous keyword in user input

Blocked keywords (require explicit confirmation):

`delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`

## Learning / Creator Mode

**Menu option 5 — Dev Portal.** Requests there use `force_learning=True`.

Trigger phrases (`LEARNING_MODE_KEYWORDS`):

`add a rule`, `new rule`, `learning mode`, `creator mode`, `teach alfred`, `update alfred`, `add feature`, …

Flow:
1. `generate_learning_discussion()` — discuss proposed change (no file writes)
2. User confirms `y` / declines `n`
3. Confirmed → `CLAUDE_EXECUTION` routed to **`claude_code`**
4. Declined → logged as `LEARNING_DECLINED`

See `docs/LEARNING-WORKFLOW.md` for Cursor-based skill learning (replaces the old daily GitHub loop).

## Quant Plugin

Optional. Set `QUANT_BASE_URL` for local Flask (`plugins/quant/app.py`). Menu **9. Quant Dashboard**.

Not part of `alfred_brain()` categories — accessed via dedicated menu path when implemented.

## Keyword Reference

### Codex (`CODEX_ROUTING_KEYWORDS`)

`refactor`, `unit test`, `implement`, `fix bug`, `alfred code`, `update alfred`, `frontend`, …

### Claude Code (`CLAUDE_CODE_ROUTING_KEYWORDS`)

`mcp`, `excel`, `power bi`, `playwright`, `pull request`, `read file`, `execute`, …

## Files To Keep In Sync

- `backend/main.py` (constants + `alfred_brain()`)
- `memory/routing-rules.md` (this file)
- `CLAUDE.md`, `README.md`
- `requirements/alfred-tools.json`
