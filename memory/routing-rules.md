# Alfred Worker Routing Rules
*Version: 2026-05-24*

## Cost-Aware Provider Selection

Alfred routes tasks to the cheapest capable provider. Heavy providers (Codex, Claude Code) are only invoked when the task genuinely requires them.

| Provider | Handles |
|---|---|
| **openai_mini** | Conversation, classification, planning, memory notes, skill drafting, CLAUDE_EXECUTION tasks with no keyword signal |
| **codex** | Alfred code updates, app/UI/website/dashboard design, Python refactors, tests, code cleanup, implementation tasks |
| **claude_code** | MCP-heavy work, Power BI investigations, Power Query, repository/file exploration, complex execution, deep tool use |

## Routing Logic (Priority Order)

1. `GENERAL` → always **openai_mini**
2. `POWERBI` → always **claude_code**
3. `CLAUDE_EXECUTION` + Codex keyword score > Claude score → **codex** → auto-dispatch
4. `CLAUDE_EXECUTION` + Claude keyword score >= Codex score → **claude_code** → auto-dispatch
5. `CLAUDE_EXECUTION` + no keyword match (both scores = 0) → **openai_mini** → plan shown, no auto-dispatch

## Auto-Dispatch Gate

Auto-dispatch to Codex/Claude is blocked when:
- A dangerous keyword is detected (`delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`)
- The chosen provider is **openai_mini** (cost-aware fallback — plan displayed instead)

## Learning / Creator Mode

Triggered when the task contains a phrase from `LEARNING_MODE_KEYWORDS` — indicating the user wants to add, modify, or teach Alfred a new rule, feature, or behavior.

**Flow:**
1. Alfred discusses the proposed change conversationally (openai_mini, no dispatch)
2. Alfred summarizes the change with **Proposed change:** line
3. Alfred asks: `Proceed with this change? (y/n)`
4. **Confirmed** → forces `CLAUDE_EXECUTION + codex`, generates scope, auto-dispatches to Codex
5. **Declined** → logs as `LEARNING_DECLINED`, nothing written or dispatched

**Trigger phrases** (see `LEARNING_MODE_KEYWORDS` in `backend/main.py`):
`add a rule`, `new rule`, `add rule`, `routing rule`, `update alfred`, `modify alfred`,
`change alfred`, `teach alfred`, `add to alfred`, `add feature`, `new feature`,
`add behavior`, `update routing`, `add routing`, `update dispatch`, `add dispatch`,
`save this rule`, `remember this rule`, `add this rule`, `creator mode`, `learning mode`

## Keyword Reference

### Codex trigger keywords
`alfred code`, `alfred update`, `app design`, `bug fix`, `class`, `clean up`, `code cleanup`,
`code review`, `coverage`, `dashboard design`, `dead code`, `debug code`, `dependency`,
`docstring`, `extract method`, `fix bug`, `frontend`, `function`, `implement`,
`implementation`, `import`, `lint`, `linting`, `method`, `module`, `package`,
`pytest`, `refactor`, `refactoring`, `rename`, `repo`, `repository`, `review code`,
`test suite`, `tests pass`, `type hint`, `typing`, `ui design`, `unit test`, `unit tests`,
`update alfred`, `web app`, `web application`, `website design`, `write code`

### Claude Code trigger keywords
`database`, `deep tool`, `execute`, `explore`, `file exploration`, `file system`,
`filesystem`, `folder`, `inspect file`, `mcp`, `onedrive`, `power bi`, `power query`,
`powerbi`, `read file`, `repository exploration`, `run script`, `scan`, `sharepoint`,
`workspace`
