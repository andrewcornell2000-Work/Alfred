# Cash Flow Forecasting

**Source:** CFO best practices for working capital management  
**Adapted for Alfred:** Operating cash flow planning for Maersk MCL finance teams

---

## When This Skill Applies

Use when:
- Forecasting weekly or monthly cash positions (13-week rolling)
- Planning for seasonal working capital swings
- Modeling impact of freight rate changes on collections
- Stress-testing cash under different demand scenarios
- Reporting cash burn / runway for business units

---

## Step 1 — Gather baseline data

Collect three months of actual data:

```
1. Operating cash inflows
   - Customer invoices (amount, terms, historical collection %)
   - Container deposits / refundable charges
   - Other operational receipts

2. Operating cash outflows
   - Payroll (monthly, tax, benefits)
   - Supplier payments (terms negotiated, actual payment lags)
   - Vessel / equipment costs (fixed + variable)
   - Fuel, port fees, terminal charges
   - Overhead, IT, insurance, compliance

3. Working capital movements
   - Days Sales Outstanding (DSO) — how long invoices take to pay
   - Days Payable Outstanding (DPO) — payment terms we have
   - Inventory / spare parts cycles
```

---

## Step 2 — Build the 13-week rolling forecast

### Structure

```
Weekly Cash Flow Forecast
├── Week 1–13 columns
├── Inflows section (by source)
├── Outflows section (by cost type)
└── Net cash movement + closing balance
```

### Excel template

```excel
=== CASH INFLOWS ===
Freight revenue (invoiced last month)
  × Historical collection %
  = Expected cash in (with payment term lag)

Container deposits returned
  = Cash in (weekly average)

=== CASH OUTFLOWS ===
Payroll                  = Fixed weekly amount
Supplier payments        = (Prior month spend) × (DPO / 30)
Vessel charter / lease   = Fixed weekly
Fuel & port costs        = Prior month + seasonal adjustments
Tax / compliance         = Scheduled quarterly

=== NET POSITION ===
Opening balance (Week N-1)
  + Total inflows
  - Total outflows
  = Closing balance (Week N)

Cash at risk = Minimum balance required - Forecast closing balance
```

### Example: 4-week cash flow

| Week | Freight In | Deposits | Payroll | Suppliers | Fuel | Other | Net Cash | Balance |
|------|-----------|----------|---------|-----------|------|-------|----------|---------|
| 1    | $2.8M     | $0.2M    | $1.1M   | $0.9M     | $0.6M | $0.3M | +$0.1M   | $5.2M   |
| 2    | $2.9M     | $0.15M   | $1.1M   | $0.95M    | $0.6M | $0.3M | +$0.1M   | $5.3M   |
| 3    | $2.7M     | $0.1M    | $1.1M   | $0.88M    | $0.6M | $0.3M | -$0.08M  | $5.22M  |
| 4    | $3.1M     | $0.25M   | $1.1M   | $1.0M     | $0.6M | $0.3M | +$0.35M  | $5.57M  |

**Minimum required balance:** $4.5M  
**Lowest forecast balance:** $5.22M  
**Cash cushion:** $0.72M ✓ Safe

---

## Step 3 — Scenario modeling

Build three scenarios showing cash stress:

```
BASE CASE (most likely)
├── Freight revenue: current bid forecast
├── Collections: historical DSO (42 days)
├── Costs: current run-rate + seasonal factors
└── Working capital: no major shifts

UPSIDE (improve cash)
├── Freight revenue: rates up 5% (market surge)
├── Collections: faster at 38 days (improved credit terms)
├── Costs: fuel prices down 8%
└── Payables: extended to 35 days (renegotiated)

DOWNSIDE (stress cash)
├── Freight revenue: rates down 8% (market softness)
├── Collections: slower at 48 days (customer defaults risk)
├── Costs: fuel spike 12%, unplanned vessel repairs
└── Payables: shortened to 25 days (supplier risk)
```

Calculate: What's the lowest balance in each scenario?

---

## Step 4 — Daily management during the week

### Monday morning ritual

```
1. Review actual cash position (bank statement)
2. Check invoices issued this week (future inflows)
3. Confirm supplier payment schedule (upcoming outflows)
4. Update forecast with Week 1 actual → roll forward to Week 14
5. Flag any balance < minimum required
6. Review collections (follow up on overdue invoices)
```

### Red flags to act on

| Flag | Action |
|------|--------|
| Forecast balance < $4.5M | Pause discretionary spend, accelerate collections |
| Major customer > 50 days overdue | Escalate to credit, consider payment plan |
| Unexpected large payment due | Confirm supplier invoice, negotiate timing |
| Freight rate collapse > 10% | Re-run scenario, brief leadership |
| Working capital swing (> $0.5M) | Investigate cause, update assumptions |

---

## Step 5 — Key assumptions & risks

| Assumption | Value | Confidence | Sensitivity |
|-----------|-------|------------|------------|
| Collection DSO | 42 days | Medium | ±3 days = ±$0.35M swing |
| Payables DPO | 30 days | High | ±5 days = ±$0.25M swing |
| Freight rate | $450/FEU | Low | ±$50 = ±$0.8M swing |
| Fuel cost | $420 per MT | Medium | ±$30 = ±$0.4M swing |
| Payroll growth | 2% annual | High | Minimal monthly impact |

---

## Step 6 — Weekly reporting checklist

Before Friday close-of-business:

- [ ] 13-week forecast updated with Week 1 actuals
- [ ] Minimum balance highlighted (green/red status)
- [ ] Top 3 risk items called out (overdue invoices, delayed shipments, cost surprises)
- [ ] Scenario summary: Base / Upside / Downside balances for Week 13
- [ ] Collections pipeline: $M by age bucket (current, 30–60 days, 60+ days)
- [ ] Outflows: any spend exceeding forecast by > $100K flagged
- [ ] Email to CFO/Finance Manager: 2–3 bullet points on health, actions, risks

---

## Pro tips for Maersk

**Container deposits:** These are timing swaps, not true revenue. Watch DSO on freight separately.

**Seasonal patterns:** Q4 peak drives collections in Q1. Q2-Q3 softer. Model 18-month to see cycles.

**Integrated reporting:** Link cash forecast to P&L forecast (labour + freight) so assumptions align.

**Working capital optimization:** Every 1 day improvement in DSO or DPO = ~$20K–$50K freed up depending on monthly run-rate.

**Stress testing:** Model a 20% freight rate shock and a 3-week payment delay simultaneously (realistic worst-case in downturn).

