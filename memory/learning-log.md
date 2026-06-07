# Alfred Learning Log

---

## 2026-06-08 (Iteration #13) — Routing & Safety-Gate Audit Skill

**Category:** Tools / Self-upgrade (routing + safety)
**Mode:** New skill — audit & improvement spec

**Change summary:**
- Created `skills/alfred-routing-keywords.md` — a full audit of how `backend/main.py` picks a tool for a request, what's brittle, and what to change.
- Documents the 6-stage routing pipeline: provider override → learning-mode → Alfred Brain (JSON classifier) → keyword fallback → safety gate → dispatch.
- Maps the six keyword sets that drive routing (`DANGEROUS_KEYWORDS`, `ACTION_KEYWORDS`, `LEARNING_MODE_KEYWORDS`, `CODEX_ROUTING_KEYWORDS`, `CLAUDE_CODE_ROUTING_KEYWORDS`, `SEARCH_TRIGGER_KEYWORDS`) plus `TOOL_REGISTRY[*].keywords`.
- Identifies 13 missing destructive verbs that should sit behind the safety gate (drop table, force push, merge pr, rm -rf, submit the form, refresh dataset, publish report, pip install, send email, etc.) — currently destructive ops via Git/GitHub MCP, Excel MCP, Power BI MCP, Playwright MCP and shell can dispatch without the typed-yes confirmation.
- Identifies routing keyword problems: bare `document`, `report`, `open`, `code` over-trigger; Power Query is only correctly routed because of a hard short-circuit (made explicit); fallback sets have drifted from the Tool Registry.
- Provides a target **routing decision matrix** — for each request shape, the right category, provider, MCP, and whether the safety gate fires (pattern: read+draft = no gate; send/delete/overwrite/publish/refresh = gate).
- Concrete proposed diff to `backend/main.py` (documented only — Andrew approves before applying): expanded `DANGEROUS_KEYWORDS_V2`, tightened fallback sets, generation of fallback sets from the Tool Registry (single source of truth), Tool Registry summary injected into `ALFRED_BRAIN_PROMPT`.
- Adds a "How to add a new tool without breaking routing" 5-step procedure so future MCP/CLI additions wire keywords + safety gate consistently.

**Use case:** Reference for any future change that touches routing — Andrew (or Alfred in a later iteration) can look up exactly which keyword set governs which behaviour, which destructive verbs are still ungated, and the standard procedure for adding a new tool without creating dead keywords or unsafe paths.

**Key findings worth flagging:**
- The safety gate is currently *too narrow* — 9 of Alfred's installed tools have destructive verbs that the gate doesn't catch. This is the highest-priority follow-up.
- The Tool Registry should be the single source of truth for keywords; today the fallback sets are hand-maintained in a second place and have already drifted.
- The brain prompt doesn't list the actual tools — it routes by category alone. A small change to inject the registry summary improves tool-name accuracy in user-visible plans.

**Files modified:** `skills/alfred-routing-keywords.md` (new, 16k chars), `memory/learning-log.md`

**Complementary skills:** `skills/github.md`, `skills/browser-automation.md`, `skills/office-mastery.md` (per-tool how-tos that should match the routing matrix).

---


---

## 2026-06-07 (Iteration #12) — Power Query Error Diagnostic Playbook (rewrite)

**Category:** Skills / Power Query & Data Engineering
**Mode:** Rewrite of broken/stub file

**Change summary:**
- Rewrote `skills/powerquery-column-errors.md` from a thin, escaped-character-corrupted stub into a complete, structured error diagnostic playbook
- Positioned explicitly as the *companion* to `power-query-transformations.md`: transformations skill = building queries, this skill = fixing broken queries. No content overlap.
- Covers a structured 6-step diagnostic workflow (read error → find failing step → check last good state → inspect formula → compare to source → fix at right layer)
- Error catalogue with cause + fix recipe for the 8 most common Power Query errors:
  1. `Expression.Error: column not found`
  2. `Column1/Column18 not found` (CSV column drift)
  3. `DataFormat.Error` (type coercion failures)
  4. `Cannot apply field access to type Table/Record/List` (missed expansion)
  5. `Token Eof/Then/Comma expected` (M syntax)
  6. `Formula.Firewall` (privacy engine blocking combine)
  7. `DataSource.Error: key didn't match any rows` (sheet/table renamed)
  8. Folder combine returning fewer rows (silent sample file drift)
- Plus: refresh-fails-in-Service-but-works-in-Desktop diagnosis (gateway, credentials, hardcoded paths, dynamic sources)
- Includes inspection-order cheat sheet for "column not found" — directs the user away from opening source files first and into walking query steps in priority order
- Pre-commit checklist for fixes (root cause vs symptom, schema documentation, error handling, end-to-end refresh test)

**Use case:** When a finance/data team query breaks (typically the morning after a refresh failure or after a source system changed), this playbook gives them the diagnostic order, the literal interpretation of the error message, and the M code fix for the most common cases. Cuts typical debug time from hours of poking around to ~10-15 minutes following the recipes.

**Key learning:**
- The single most common Power Query production bug is folder-combine sample file drift — the sample file memorizes one schema and silently fails on others. Documented detection and the dynamic-column-expansion fix.
- Formula.Firewall errors confuse people because the fix is at the *query architecture* level (combine queries vs convert helper to function) not at the privacy setting level. Documented both fixes in preference order.
- "Changed Type" auto-generated steps are landmines — they hardcode every column name in the M code, so any source rename cascades into "column not found" errors downstream.

**Files modified:** `skills/powerquery-column-errors.md` (full rewrite), `memory/learning-log.md`

**Complementary skills:** `skills/power-query-transformations.md` (build), `skills/powerbi-model-editing.md` (model errors), `skills/excel-live-editing.md` (Excel-side equivalents)

---

## 2026-06-06 (Iteration #11) — Power Query Data Transformations Skill

**Category:** Skills / Power Query & Data Engineering
**Mode:** Direct implementation

**Change summary:**
- Created `skills/power-query-transformations.md` — comprehensive Power Query skill covering data transformation best practices, performance optimization, folder connectors, incremental refresh, and common patterns
- Covers five non-negotiable standards: (1) query folding awareness and performance testing, (2) folder connectors for multi-file combines with schema contracts, (3) error handling and tolerant transformations, (4) incremental refresh setup with RangeStart/RangeEnd parameters, (5) pre-load performance audit checklist
- Includes five practical transformation patterns: date component splitting (year-month hierarchy prep), deduplication on latest date (snapshot management), programmatic column renaming (folder combines), text cleaning with quality flags, unpivot-repivot workflows
- Added debugging workflow for timeouts, missing columns, and CSV format errors
- Includes comprehensive pre-publication checklist: column naming, row count validation, data types, null handling, source schema documentation, folder schema contracts, folding verification, parameter reusability, and error audit trails

**Use case:** Enable finance, supply chain, and data teams to build production-grade Power Query pipelines that handle multi-file data integration, maintain performance at scale (query folding), and support incremental refresh workflows without breaking. Teams can move away from manual CSV concatenation and build self-service, auditable data preparation.

**Research basis:**
- Microsoft Learn Power Query best practices (2025 update, July 2025)
- Query folding performance optimization community patterns (Power BI Tips, Mahsha DN, Virtual Forge)
- Incremental refresh architecture with RangeStart/RangeEnd parameters (Power BI service requirements)
- Folder connector schema management (common root cause of production failures)

**Key learning:**
- Query folding is non-obvious: same operation (e.g., filter) is folding-safe at row 5 but folding-breaking at row 20. This is the single biggest performance lever in Power Query.
- Folder combines fail silently when schema drifts (new column, removed column, different name). Pre-publication schema contracts prevent this.
- Incremental refresh requires both query folding AND RangeStart/RangeEnd parameters to be set up correctly. One without the other gives zero benefit.

**Complementary skills:** `skills/powerbi-model-editing.md` (DAX, measures, relationships), `skills/powerquery-column-errors.md` (error diagnostics), `skills/excel-financial-models.md` (formula standards)

**Files modified:** `skills/power-query-transformations.md` (created), `memory/learning-log.md`

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

**Source:** https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CODE_REVIEW.md

**Files modified:** `skills/karpathy-coding-guidelines.md` (created), `AGENTS.md` (created), `CLAUDE.md` (updated), `README.md` (updated), `memory/learning-log.md`

---
