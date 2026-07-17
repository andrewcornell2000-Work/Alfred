# Data Analysis — Plan, explore, measure, summarise

Use before multi-step analytical work (Excel, Power BI, CSV/Parquet, warehouse metrics). One skill for the analysis lifecycle.

*Absorbs: data-analysis-planning, data-eda, data-metrics-calculator, data-time-series, data-executive-summary. For “why don’t these numbers match?” use `data-reconciliation`.*

---

## When to use

- Multi-step analytical question (not a simple lookup)
- Uncertain sources — confirm data exists before committing
- EDA, KPIs, time series, or exec write-up from data

---

## Phase 1 — Plan (15 minutes)

1. **Decompose** the business question into sub-questions
2. **Map data** — where it lives, grain, blockers
3. **Sequence** — dependencies first; validate early
4. **Feasibility** — stop if a required table/source is missing

## Phase 2 — EDA

- Row counts, null rates, key cardinality
- Date ranges and filter gotchas
- Outliers / negatives where they shouldn’t exist
- Document grain (what one row means)

Prefer DuckDB / SQL or Excel MCP over pasting whole tables into chat.

## Phase 3 — Metrics

- Define each KPI in one sentence (numerator, denominator, filters)
- Prefer measures already in the semantic model when using Power BI
- Show period comparison only after grain is confirmed

## Phase 4 — Time series (when relevant)

- Confirm calendar/period alignment across sources
- Separate level shifts (abrupt) from drift (gradual)
- Don’t forecast until history and grain are clean

## Phase 5 — Executive summary

- Bottom line first (1–2 sentences)
- 3–5 bullets with numbers
- One “watch out” / data caveat
- No methodology essay unless asked

## Anti-patterns

- Building charts before confirming sources
- Spawning a data-analyst subagent — stay in-session with this skill
- Pasting full exports into chat — query/filter first
