# Labour Cost Forecasting

**Source:** Best practices for workforce cost planning in regulated industries  
**Adapted for Alfred:** Financial planning for Maersk MCL labour operations

---

## When This Skill Applies

Use when:
- Forecasting labour costs for next quarter / fiscal year
- Building headcount plans with cost implications
- Analyzing headcount scenarios (grow, freeze, reduce)
- Validating labour cost budget assumptions
- Identifying cost drivers (salary inflation, headcount changes, overtime)

---

## Step 1 — Gather baseline data

Before building a forecast, collect:

```
1. Current state (last full month)
   - Actual headcount by grade / grade_band (FTE and contract)
   - Actual spend by cost centre / function
   - Overtime, penalties, incentives as % of base salary

2. Cost structure
   - Salary bands by grade (min, mid, max)
   - Bonus / incentive pools (% of base)
   - On-costs (benefits, superannuation, payroll tax)
   - Allowances, shift penalties, etc.

3. Planned changes
   - Approved headcount changes (start dates, grades)
   - Salary review cycles and expected % increases
   - External factors (award changes, compliance costs)
```

---

## Step 2 — Build the forecast model

### Structure

```
Headcount Forecast
├── Grade bands (e.g., Manager, Coordinator, Operator)
├── Contract type (permanent, fixed-term, contractor)
├── Location (affects on-costs)
└── Timeline (monthly or quarterly)

Cost Forecast (per person × count × months)
├── Base salary (including any known increases)
├── On-costs (29–31% typical for Australia)
├── Overtime / penalties
├── Allowances
├── Termination / recruitment costs
```

### Excel formula template

```excel
=== HEADCOUNT ===
Actual FTE (Month N) → Forecast FTE (Month N+1)
= Forecast FTE (Month N) 
  + New hires (from Month N+1)
  - Planned leavers
  - Vacancy adjustments

=== COST ===
Monthly Labour Cost = SUM (
  (Base Salary + Allowances) × FTE
  × (1 + On-cost%)
  + Overtime Cost
  + Incentive Pool
)

Annual Forecast = SUM (all 12 months, adjusted for seasonal factors)
```

### Example for 3-month rolling forecast

| Month | Current FTE | Hires | Leavers | Forecast FTE | Base Cost | On-costs | Total Cost |
|-------|-------------|-------|---------|--------------|-----------|----------|------------|
| Jun   | 1,245       | 8     | 3       | 1,250        | $4.2M     | $1.3M    | $5.5M      |
| Jul   | 1,250       | 12    | 2       | 1,260        | $4.25M    | $1.31M   | $5.56M     |
| Aug   | 1,260       | 5     | 4       | 1,261        | $4.26M    | $1.32M   | $5.58M     |

---

## Step 3 — Scenario analysis

Build multiple scenarios to show cost sensitivity:

```
BASE CASE (most likely)
├── Headcount: approved plan as-is
├── Salary: award increase 3% from Sep
└── Spend: current OT%, no special costs

UPSIDE (lower cost)
├── Headcount: attrition 10% higher, natural lapse
├── Salary: no movement or lower increases
└── Spend: OT down 10%

DOWNSIDE (higher cost)
├── Headcount: lower attrition (retention bonus)
├── Salary: award increase 4%, additional market adjustments
└── Spend: OT up 15% (seasonal demand spike)
```

For each scenario:
- Calculate total labour cost (annual)
- Calculate variance from budget
- Identify key drivers of change

---

## Step 4 — Variance bridge

Show the path from current spend to forecast:

```
Actual spend (May)                    $5.4M
  + Salary increases                  +$0.15M  (3% from Jul)
  + Headcount growth (net 15 FTE)     +$0.08M
  + Overtime uplift (seasonal)        +$0.05M
  - Planned leavers (offset by hires) -$0.02M
  ─────────────────────────────────────────
Forecast spend (Aug)                  $5.65M

Variance to budget ($5.7M)            -$0.05M  (-0.9%) 🟢 ON TRACK
```

---

## Step 5 — Key assumptions & risks

Document every assumption in a simple table:

| Assumption | Value | Confidence | Risk if wrong |
|-----------|-------|------------|---------------|
| Award increase | 3% from Jul | High | Cost +/- $0.2M if 4–2% |
| Attrition rate | 8% annualised | Medium | Vacancy vs overtime tradeoff |
| Overtime as % salary | 5% | Medium | Seasonal demand may spike to 8% |
| On-cost rate | 30% | High | Fixed by compliance |

---

## Step 6 — Review & sign-off

Labour cost forecast checklist:

- [ ] Headcount plan reconciles with approved FTE map
- [ ] Salary increases reflect known awards / reviews
- [ ] On-costs include all statutory & commercial obligations
- [ ] Scenarios show both upside & downside risks
- [ ] Variance bridge explains every material move
- [ ] Assumptions documented & confidence assessed
- [ ] Signed off by Finance Lead + People Lead

---

## Tools & Exports

- **Excel forecast model:** Use INDIRECT() for scenario switching; lock assumptions area
- **PowerPoint chart:** Actual vs forecast by month; add scenario bands
- **Weekly update:** Track actuals vs forecast; flag when >2% behind plan
