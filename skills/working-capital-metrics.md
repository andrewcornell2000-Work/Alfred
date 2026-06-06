# Working Capital Metrics & KPIs

## Core Metrics: The Cash Conversion Cycle (CCC)

The cash conversion cycle is the number of days between when you pay suppliers and when you collect cash from customers. It's the lifeblood of working capital management.

### Formula
**CCC = DIO + DSO - DPO**

Where:
- **DIO** = Days Inventory Outstanding (how long inventory sits before sale)
- **DSO** = Days Sales Outstanding (how long to collect payment from customers)
- **DPO** = Days Payable Outstanding (how long before you pay suppliers)

### Example: Maersk Shipping Operations
- DIO: 8 days (inventory/vessel turnaround)
- DSO: 22 days (customer payment terms)
- DPO: 35 days (supplier payment terms)
- **CCC = 8 + 22 - 35 = -5 days** ← Negative CCC is excellent (cash flows in before you pay out)

---

## Key Metrics by Function

### 1. Receivables Management (DSO Target: < 25 days for Maersk)
- Average days to collect from customers
- % of invoices paid on time (track by customer segment)
- Aging analysis (0-30, 30-60, 60-90+ days)
- Days sales outstanding trending (monthly)

**Action triggers:**
- DSO increasing 2+ days: review collection procedures
- Customer concentration >20%: personal follow-up warranted
- Invoices >60 days: escalate to collections team

### 2. Inventory Management (DIO Target: < 10 days for perishables, < 15 for general cargo)
- Inventory turnover ratio (COGS / Average inventory)
- Days inventory outstanding by cargo type
- Slow-moving SKU identification
- Inventory velocity (units per day by category)

**For Maersk:**
- Track vessel utilization (container throughput per day)
- Container return cycle time (empty to repositioned)
- Cargo dwell time at terminals

### 3. Payables Management (DPO Target: 30-45 days for Maersk)
- Days payable outstanding (maintain supplier relationships while optimizing)
- % of early payment discounts taken (ROI analysis)
- Supplier concentration risk (top 10 suppliers as % of spend)
- Payment timing optimization (avoid late fees, capture discounts)

**Action triggers:**
- DPO declining: negotiate better terms or consolidate suppliers
- Single supplier >15% of spend: develop secondary suppliers
- Missed discounts >$500K annually: restructure payment policy

---

## Working Capital Efficiency Dashboard

### Weekly Metrics (Every Monday)
| Metric | Current | Target | Variance | Trend |
|--------|---------|--------|----------|-------|
| DSO | 22.5 | <25 | -2.5 | ↓ (improving) |
| DIO | 8.2 | <10 | -1.8 | → (stable) |
| DPO | 34.8 | 30-45 | +4.8 | ↑ (extending) |
| CCC | -4.5 | <0 | -4.5 | ↑ (more negative = better) |

### Monthly Strategic Analysis
1. **Cash Release/Capture**: CCC trend analysis
   - If CCC worsening: lost $X per day in freed cash
   - Target quarterly improvement: 1-2 day reduction in CCC
2. **Receivables Quality**: Revenue growth vs. DSO trend
   - Decoupling = collection risk
3. **Supplier Health Score**: DPO paired with on-time payment %
4. **Working Capital Freed**: (CCC improvement) × (Daily revenue) = cash runway extended

---

## For Maersk Specifically

### Operational Constraints
- **Perishable cargo**: Shorter DIO required (food/pharma contracts specify hold time)
- **Equipment leasing**: DPO often fixed by manufacturer contracts (containers, chassis)
- **Fuel pricing**: Volatile supplier costs affect DPO negotiations
- **Regional terms**: Different countries have different payment norms (Europe: 60 days, Asia: 30 days)

### Priority Optimization Levers
1. **Customer payment terms negotiation**: Every 1 day of DSO improvement = ~$1.5M daily cash (scale to annual)
2. **Inventory positioning**: Hub location strategy affects DIO (centralized vs. distributed)
3. **Supplier consolidation**: Reduce vendor base 20%, negotiate volume discounts that improve DPO by 5 days
4. **Invoice automation**: OCR + early payment discounts (if ROIC > cost of capital, take them)

---

## Real-World Red Flags

| Red Flag | Root Cause | Action |
|----------|-----------|--------|
| DSO increasing suddenly | Customers in distress, or credit policy loosened | Tighten credit policy, audit new accounts |
| DPO declining | Suppliers demanding faster payment (sign of leverage loss) | Consolidate suppliers, renegotiate terms |
| CCC > 20 days | Inventory backed up or receivables slow | Audit DIO first (faster payoff), then DSO (customer collection) |
| Negative trends in all three | Operational inefficiency across the board | Full cash flow audit required |

---

## Implementation: Weekly Ritual (15 minutes, Monday morning)

1. **Pull data**: DSO, DIO, DPO from ERP (Maersk TMS/finance system)
2. **Compare to target**: Mark variance >±2 days for review
3. **Trend check**: Is CCC improving week-over-week? Plot 8-week rolling average
4. **Escalate if needed**: If DSO >28 days, DIO >12 days, or DPO <28 days, flag to finance manager
5. **Monthly deep dive**: Root cause analysis on significant variances

---

## Excel Template Structure

Create a working capital dashboard with:
- **Tab 1: Weekly Metrics** (auto-calc CCC, traffic light formatting)
- **Tab 2: Receivables Aging** (0-30, 30-60, 60-90 days + customer breakdown)
- **Tab 3: Inventory Turnover** (by cargo type, velocity, slow movers)
- **Tab 4: Payables Schedule** (supplier payment calendar, discount opportunities)
- **Tab 5: Trend Analysis** (8-week CCC chart, DSO/DIO/DPO rolling average)
- **Tab 6: Assumptions** (revenue per day, inventory value, supplier payment terms)

---

## Further Reading
- "The Perfect Order" (supply chain execution) — ties to DIO optimization
- "Working Capital Optimization" (treasury best practices) — DSO/DPO management frameworks
- Maersk internal: TMS data model (inventory tracking), Finance P&L integration points
