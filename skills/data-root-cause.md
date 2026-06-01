# Data Root Cause Investigation

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** applies to finance, Power BI, and Excel metric investigations at Maersk.

---

## When This Skill Applies

Use when:
- A metric rises or falls unexpectedly and leadership wants an explanation
- Someone asks "why did X change?" and a data-backed answer is needed
- A Power BI number doesn't match expectations or a prior period
- A variance in the budget/actuals report needs investigating
- Post-mortem analysis after a planning or reporting discrepancy

---

## Five-Step Investigation Process

### Step 1 — Validate the change is real
Before investigating causes, confirm the shift is statistically significant:
- Calculate z-score against historical baseline
- If variance is within ±1.5 standard deviations, it's likely noise — say so and stop
- Check for data refresh issues, ETL failures, or date filter problems first

### Step 2 — Establish a timeline
- Chart the metric historically to identify exactly when the shift began
- **Abrupt change** → look for a specific event (system change, policy update, data issue)
- **Gradual drift** → look for a structural shift (mix change, underlying trend)

### Step 3 — Decompose the metric
Break the metric into its components before drilling into dimensions:
```
Revenue = Volume × Price × Mix
Headcount cost = Headcount × Average rate × Hours
Variance = Rate variance + Volume variance + Mix variance
```
Identify which component explains the change first.

### Step 4 — Drill down by dimension
Compare before/after across available dimensions — by region, department, cost centre, product, channel, or time period. Rank dimensions by their contribution to the total variance.

### Step 5 — Test and document hypotheses
For each candidate cause:
- State the hypothesis specifically: "Volume declined in APAC due to fewer shifts rostered in March"
- Show the evidence (data, numbers, dates)
- Record rejected hypotheses too — they matter for the audit trail

---

## Required Inputs

- Metric name and at least 30 days of historical data
- Dimensional breakdowns available (geography, department, category)
- Timing of the observed change
- Event log if available (system changes, org changes, policy updates)

---

## Output Format

Root cause report covering:
1. **Validated change** — magnitude, timing, statistical significance
2. **Component breakdown** — which sub-metric drove the change
3. **Top contributing dimensions** — ranked by impact
4. **Primary root cause** — specific, quantified
5. **Rejected hypotheses** — what it wasn't, and why
6. **Recommended actions** — what to do, who owns it, by when
