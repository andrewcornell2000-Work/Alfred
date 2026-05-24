# Alfred Worker Routing Rules
*Version: 2026-05-24*

## Purpose

Alfred routes each user request to the cheapest capable path. Heavy providers are used only when the request needs code execution, file work, deep inspection, or a specialist plugin.

## Categories

| Category | Meaning | Default path |
|---|---|---|
| `GENERAL` | Conversation, explanation, planning, lightweight memory notes | `openai_mini` |
| `POWERBI` | Power BI, Power Query, dashboards, models, DAX, refresh issues | `claude_code` |
| `CLAUDE_EXECUTION` | File, folder, code, command, repo, or implementation work | Provider scoring |
| `QUANT` | Stocks, tickers, trading opportunities, market analysis, backtests | Quant plugin |

## Providers

| Provider | Handles |
|---|---|
| `openai_mini` | Classification, general chat, low-cost planning, non-dispatched execution plans with weak signals |
| `codex` | Alfred code changes, Python refactors, tests, implementation, UI/app/dashboard/frontend work |
| `claude_code` | Power BI investigations, MCP-heavy work, file-system exploration, broad execution tasks, deep tool use |
| `quant_tool` | Quant Intelligence Flask API under `plugins/quant` or `QUANT_BASE_URL` |

## Routing Priority

1. Explicit provider override wins when the user starts with or includes phrases such as `use claude`, `with claude`, `via claude`, `ask claude`, `use codex`, `with codex`, `via codex`, or `ask codex`.
2. `GENERAL` always routes to `openai_mini`.
3. `QUANT` routes directly to the Quant plugin API; it does not generate a Claude/Codex scope.
4. `POWERBI` routes to `claude_code`.
5. `CLAUDE_EXECUTION` compares Codex and Claude keyword scores:
   - Codex score greater than Claude score -> `codex`
   - Claude score greater than or equal to Codex score -> `claude_code`
   - Both scores zero -> `openai_mini`, plan only, no auto-dispatch

## Auto-Dispatch Gate

Alfred may auto-dispatch to Codex or Claude Code only when:

- The selected provider is `codex` or `claude_code`
- The category is `CLAUDE_EXECUTION`, or the category is `POWERBI` with an action keyword
- No dangerous keyword is present

Auto-dispatch is blocked when the request contains:

`delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`

When blocked, Alfred should show the plan and wait for a safer user instruction.

## Learning / Creator Mode

Menu option `8. Dev Portal` opens a dedicated Learning / Creator prompt. Requests entered there are forced through the guarded learning flow even if they do not contain trigger phrases.

Triggered phrases include:

`add a rule`, `new rule`, `add rule`, `routing rule`, `update alfred`, `modify alfred`, `change alfred`, `teach alfred`, `add to alfred`, `add feature`, `new feature`, `add behavior`, `update routing`, `add routing`, `update dispatch`, `add dispatch`, `save this rule`, `remember this rule`, `add this rule`, `creator mode`, `learning mode`

Flow:

1. Alfred discusses the proposed change with `openai_mini`.
2. Alfred ends with a `Proposed change:` line.
3. Alfred asks for confirmation.
4. Confirmed changes are routed as `CLAUDE_EXECUTION` to `codex`.
5. Declined changes are logged as `LEARNING_DECLINED`; nothing is written or dispatched.

Current limitation: Dev Portal routes implementation work, but deterministic first-class editing flows for skills, routing rules, tool manifests, and project files are still planned.

## Quant Routing

Quant requests include:

- Specific ticker analysis such as `analyze NVDA`
- Trading opportunities
- Market, macro, institutional, smart-money, options, alerts, backtest, paper portfolio, or learning-stat requests

Quant command parser output maps to these endpoints:

| Command | Endpoint |
|---|---|
| `analyze` | `/api/analyze/<ticker>` |
| `backtest` | `/api/backtest/<ticker>` |
| `institutional` | `/api/institutional/<ticker>` |
| `opportunities` | `/api/opportunities` |
| `macro` | `/api/macro` |
| `paper` | `/api/paper` |
| `alerts` | `/api/alerts` |
| `learning` | `/api/learning` |
| `refresh` | `/api/refresh` |

`QUANT_BASE_URL` controls whether Alfred talks to a cloud deployment or a local Flask server.

## Keyword Reference

### Codex trigger keywords

`alfred code`, `alfred update`, `app design`, `bug fix`, `class`, `clean up`, `code cleanup`, `code review`, `coverage`, `dashboard design`, `dead code`, `debug code`, `dependency`, `docstring`, `extract method`, `fix bug`, `frontend`, `function`, `implement`, `implementation`, `import`, `lint`, `linting`, `method`, `module`, `package`, `pytest`, `refactor`, `refactoring`, `rename`, `repo`, `repository`, `review code`, `test suite`, `tests pass`, `type hint`, `typing`, `ui design`, `unit test`, `unit tests`, `update alfred`, `web app`, `web application`, `website design`, `write code`

### Claude Code trigger keywords

`database`, `deep tool`, `execute`, `explore`, `file exploration`, `file system`, `filesystem`, `folder`, `inspect file`, `mcp`, `onedrive`, `power bi`, `power query`, `powerbi`, `read file`, `repository exploration`, `run script`, `scan`, `sharepoint`, `workspace`

### Power BI action keywords

`inspect`, `run`, `edit`, `use mcp`, `use claude`

## Files To Keep In Sync

- `backend/main.py`
- `memory/routing-rules.md`
- `README.md`
- `CLAUDE.md`
- `requirements/alfred-tools.json`
- Any relevant skill file under `skills/`
