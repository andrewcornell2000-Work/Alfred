# Business Metrics Calculator

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** focused on finance, workforce, and operational metrics relevant to Maersk MCL.

---

## When This Skill Applies

Use when:
- Calculating or verifying standard business metrics for a report or deck
- The team disagrees on how a metric should be defined
- Benchmarking performance against targets or prior periods
- Building a metrics summary for a new reporting area
- Validating that an existing calculation matches the agreed definition

---

## Step 1 — Identify the metric type and agree the definition

Before calculating anything, confirm:
- **What exactly is being measured** (e.g. FTE headcount vs bodies, revenue vs net revenue)
- **The period** (month-end, average, point-in-time, trailing 12M)
- **Any exclusions** (contractors, vacancies, intercos)
- **The source of truth** (which system's number wins if they differ)

> A metrics report is only as good as the agreed definitions feeding it.

---

## Core Metric Formulas

### Workforce / Labour Planning

```
FTE Headcount = Sum of (contracted hours / standard hours per FTE)

Headcount Variance = Actual headcount - Budgeted headcount

Labour Cost per FTE = Total labour cost / Average FTE

Overtime Rate = Overtime hours / Total hours worked

Attrition Rate = Leavers in period / Average headcount × 100
Annualised Attrition = (Leavers / Average headcount) × (12 / months in period) × 100

Vacancy Rate = Open positions / Total approved headcount × 100
```

### Finance / Cost

```
Budget Variance ($) = Actual - Budget
Budget Variance (%) = (Actual - Budget) / Budget × 100

YoY Growth = (Current period - Prior year period) / Prior year period × 100

Cost per Unit = Total cost / Volume
Run Rate = Period spend × (12 / months elapsed)  # annualised from YTD
```

### Operational

```
Utilisation = Productive hours / Available hours × 100
Efficiency = Standard hours / Actual hours × 100  (>100% = ahead of standard)
```

---

## Step 2 — Calculate and validate

```python
import pandas as pd

df = pd.read_excel('actuals.xlsx')

# Example: budget variance by cost centre
df['variance_$'] = df['actual'] - df['budget']
df['variance_pct'] = (df['variance_$'] / df['budget'].abs()) * 100

# Sort by absolute variance to find biggest movers
df = df.reindex(df['variance_$'].abs().sort_values(ascending=False).index)
```

---

## Step 3 — Benchmark and grade

For each metric, compare against:
- Internal target / budget
- Prior period (MoM, YoY)
- Industry benchmark if available

Use a simple traffic light:
| Status | Threshold |
|--------|-----------|
| 🔴 Off track | > 5% adverse variance |
| 🟡 Watch | 2–5% adverse variance |
| 🟢 On track | Within 2% of target |

---

## Step 4 — Metrics report structure

```
## Period: [Month Year]

### Summary
| Metric | Actual | Budget | Variance | Status |
|--------|--------|--------|----------|--------|
| FTE    | 1,245  | 1,260  | -15 (-1.2%) | 🟢 |
| Cost   | $8.2M  | $7.9M  | +$0.3M (+3.8%) | 🟡 |

### Key Drivers
[Top 3 movers with quantified impact]

### Risks / Watch Items
[Anything outside threshold that needs attention]
```
