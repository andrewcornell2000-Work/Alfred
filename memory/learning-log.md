# Alfred Learning Log

---

## 2026-05-24 — Cost-Aware Worker Routing Rule

**Category:** Routing / Architecture
**Mode:** Direct implementation (initiated via Claude Code)

**Change summary:**
- Added `LEARNING_MODE_KEYWORDS` set for Learning / Creator Mode detection
- Added `LEARNING_DISCUSSION_PROMPT` system prompt for conversational pre-confirmation
- Added `is_learning_mode_task()` function
- Added `generate_learning_discussion()` function (uses openai_mini + memory context)
- Expanded `CODEX_ROUTING_KEYWORDS`: Alfred self-modification (`alfred code`, `alfred update`, `update alfred`), UI/app/website/dashboard design, code cleanup keywords
- Expanded `CLAUDE_CODE_ROUTING_KEYWORDS`: `power query`, `explore`, `file exploration`, `repository exploration`, `deep tool`
- Updated `choose_provider()` — returns `openai_mini` for CLAUDE_EXECUTION with zero keyword signal (avoids unnecessary heavy CLI dispatch)
- Updated `should_send_to_claude()` — added `provider` param; blocks auto-dispatch when provider is `openai_mini`
- Updated `_action_ask_alfred()` — Learning / Creator Mode intercept: discuss → confirm → force `CLAUDE_EXECUTION + codex`; declined path logs as `LEARNING_DECLINED` and continues
- Updated `_action_show_dispatch_rules()` — added rows for cost-aware fallback and Learning Mode; added Learning Mode keyword display
- Created `memory/routing-rules.md` as reusable routing rule reference
- Created `memory/learning-log.md` (this file)

**Files modified:** `backend/main.py`, `memory/routing-rules.md` (created), `memory/learning-log.md` (created)
