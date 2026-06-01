# Data Metric Reconciliation

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** particularly relevant for Power BI vs Excel vs source system discrepancies at Maersk.

---

## When This Skill Applies

Use when:
- A number in Power BI doesn't match the same number in Excel (or SAP, or a dataflow)
- Two reports show different figures for the same metric
- Someone asks "why doesn't this tie?" or "the numbers don't reconcile"
- Preparing a report and need to confirm all sources agree before publishing
- Investigating a data quality issue across the medallion dataflow stack

---

## Eight-Step Reconciliation Workflow

### Step 1 — Define the comparison
Before loading any data:
- Name the two (or more) sources being compared
- Define exactly what the metric means in each system
- Set acceptable variance threshold (e.g. < 0.1% for finance sign-off, < 1% for operational)
- Agree the time period and any filters (entity, region, cost centre)

### Step 2 — Load and tag each source
```python
df_pbi = pd.read_csv('power_bi_export.csv')
df_excel = pd.read_excel('finance_template.xlsx')

df_pbi['source'] = 'Power BI'
df_excel['source'] = 'Excel'
```

### Step 3 — Standardise formats
- Dates → `datetime` objects with consistent granularity (don't mix daily vs monthly)
- Metrics → `float64`, strip currency symbols and commas
- Identifiers → strip whitespace, normalise case
- Remove nulls or flag them explicitly

### Step 4 — Aggregate to the comparison level
```python
# Aggregate both sources to the same grain before joining
pbi_agg = df_pbi.groupby(['period', 'cost_centre'])['amount'].sum()
excel_agg = df_excel.groupby(['period', 'cost_centre'])['amount'].sum()
```

### Step 5 — Join and calculate variance
```python
reconciled = pbi_agg.join(excel_agg, lsuffix='_pbi', rsuffix='_excel', how='outer')
reconciled['variance'] = reconciled['amount_pbi'] - reconciled['amount_excel']
reconciled['variance_pct'] = reconciled['variance'] / reconciled['amount_excel'].abs()
```

### Step 6 — Categorise discrepancies
| Severity | Threshold | Action |
|----------|-----------|--------|
| 🔴 Critical | > 1% or > $10k | Investigate immediately |
| 🟡 Warning | 0.1%–1% | Document and monitor |
| 🟢 Acceptable | < 0.1% | Note in report, no action |

### Step 7 — Investigate root causes
Common causes to check in order:
1. **Date filter mismatch** — one source is month-end, the other is run-date
2. **Currency/unit difference** — one is AUD, other is USD; or thousands vs actuals
3. **Missing records** — rows present in one source but not the other (outer join NULLs)
4. **Calculation difference** — different formula for the same metric (e.g. FTE vs headcount)
5. **Timing/refresh lag** — one source hasn't refreshed yet
6. **Rounding** — cumulative rounding differences across many rows

### Step 8 — Document and report
Reconciliation report must include:
- Summary: total variance, % of rows reconciled within threshold
- Top 10 worst discrepancies by absolute value
- Root cause for each material discrepancy
- Recommended fix (which system is the source of truth)

---

## Power BI-Specific Notes
- Export from Power BI using "Analyse in Excel" or a DAX query for exact figures
- Check whether the PBI model applies RLS — a row-level security filter may be excluding records
- If using imported data, check the last refresh timestamp before concluding there's a discrepancy
