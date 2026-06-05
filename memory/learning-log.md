# Alfred Learning Log

---

## 2026-05-24 (Iteration #10) — Labour Cost Forecasting Skill

**Category:** Skills / Finance
**Mode:** Direct implementation

**Change summary:**
- Created `skills/labour-cost-forecasting.md` — comprehensive labour cost forecasting skill for Maersk finance & labour planning teams
- Covers: baseline data gathering, forecast model structure with Excel templates, 3-month rolling forecast example, scenario analysis (Base/Upside/Downside), variance bridge methodology, assumptions documentation, and sign-off checklist
- Includes practical templates: headcount forecast structure, cost calculation formulas, monthly forecast table example, scenario sensitivity framework, variance bridge, and assumption risk register
- Designed for regulated industries (Australia-based on-cost rates 29–31%, statutory obligations)
- Triggers: quarter-end planning, budget validation, headcount scenario analysis, cost driver identification

**Use case:** Enable Maersk MCL finance & labour planning teams to build rapid, repeatable labour cost forecasts with clear variance tracking and scenario sensitivity

**Files modified:** `skills/labour-cost-forecasting.md` (created), `memory/learning-log.md`

---

## 2026-05-24 — Karpathy Coding Guidelines Skill

**Category:** Skills / Coding Standards  
**Mode:** Direct implementation (initiated via Claude Code)

**Change summary:**
- Created `skills/karpathy-coding-guidelines.md` — full Karpathy guidelines adapted for Alfred, with trigger conditions for coding, refactoring, debugging, architecture, UI/app design, and self-improvement tasks; source attribution preserved
- Created `AGENTS.md` — concise version for Codex and other coding agents, with Alfred-specific safety rules merged in
- Updated `CLAUDE.md` — added "Coding Guidelines" section pointing to both new files
- Updated `README.md` — added AGENTS.md reference under project layout

**Source:** https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md  
**Files modified:** `skills/karpathy-coding-guidelines.md` (created), `AGENTS.md` (created), `CLAUDE.md`, `README.md`, `memory/learning-log.md`

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

---

## 2026-05-24 - Dev Portal menu option

**Category:** Learning / Creator UX
**Mode:** Direct implementation (initiated via Codex)

**Change summary:**
- Added main menu option `8. Dev Portal`
- Dev Portal lets the user teach Alfred skills, routing rules, tool requirements, and self-improvements from a dedicated prompt
- Dev Portal forces the existing Learning / Creator confirmation flow before routing confirmed changes to Codex
- Added quick portal commands for `paste`, `clip`, `skills`, `rules`, and `back`

**Files modified:** `backend/main.py`, `README.md`, `memory/learning-log.md`
