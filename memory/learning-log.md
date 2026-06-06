# Alfred Learning Log

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
