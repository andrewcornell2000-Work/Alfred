# Alfred Learning Log

---

## 2026-06-05 (Iteration #10) — Cash Flow Forecasting Skill

**Category:** Skills / Finance
**Mode:** Direct implementation

**Change summary:**
- Created `skills/cash-flow-forecasting.md` — operational cash flow forecasting skill for Maersk finance & working capital management teams
- Covers: baseline data gathering (invoices, deposits, payroll, supplier payments, fuel), 13-week rolling forecast Excel template structure, scenario modeling (Base/Upside/Downside), daily management ritual (Monday reviews, red flag triggers), key assumptions with sensitivity, and weekly reporting checklist
- Includes practical templates: weekly cash flow forecast structure, cash inflow/outflow categorization by operational source, real-world 4-week example with $5M+ balances, working capital assumptions table with DSO/DPO sensitivity
- Adapted for shipping/logistics context: container deposits, freight revenue collection lag, seasonal patterns (Q4 peak → Q1 collections), integrated reporting with P&L forecast
- Triggers: weekly cash position forecasting, working capital optimization, stress-testing under demand/fuel shocks, 13-week rolling updates, DSO/DPO improvement initiatives

**Use case:** Enable Maersk MCL finance teams to forecast liquidity 13 weeks out with weekly granularity, identify cash shortfalls 8-10 weeks in advance, optimize working capital, and stress-test under market downturns

**Research insights:** 
- 13-week rolling forecasts are industry standard for operational cash management (Datarails, Intuit, Dryrun research)
- Finance teams using rolling forecasts can identify shortfalls 8-10 weeks in advance vs. real-time crisis
- Working capital optimization: every 1 day improvement in DSO or DPO can free up $20K-$50K+ depending on monthly run-rate
- Shipping industry specific: collections lag (freight invoices 30-45 days out), seasonal swings, fuel volatility create high cash sensitivity

**Files modified:** `skills/cash-flow-forecasting.md` (created), `memory/learning-log.md`

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
- Dev Portal lets the user teach Alfred skills, routing rules, tool requirements, and self-improvements 
