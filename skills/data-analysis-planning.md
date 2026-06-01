# Data Analysis Planning

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** applies before any multi-step data analysis, Power BI investigation, or reporting task.

---

## When This Skill Applies

Use **before touching any data** when a task involves:
- A multi-step analytical question (not a simple lookup)
- Uncertain data availability — need to confirm sources exist before committing to an approach
- A compressed timeline where wrong-direction work would be costly
- Multiple stakeholders who need to agree on the approach before work begins

> "A 15-minute planning session prevents hours of wrong-direction work."

---

## Five-Phase Planning Process

### Phase 1 — Decompose the question
Break the business question into answerable sub-questions:

```
Business question: "Why is APAC labour cost over budget?"

Sub-questions:
1. What is the total variance ($, %)?
2. Which cost categories are over? (headcount, overtime, contractors)
3. Which sub-regions or departments drive it?
4. Did it start this month or has it been building?
5. Is it a rate issue, a volume issue, or a mix issue?
```

### Phase 2 — Map required data
For each sub-question, identify:
- What data is needed
- Where it lives (Power BI dataset, Excel file, SAP export, dataflow)
- Whether it's actually available and at the right grain
- Flag blockers upfront — don't discover mid-analysis that a table doesn't exist

### Phase 3 — Sequence the work
Order steps so outputs feed subsequent analysis:
- Identify which steps can run in parallel
- Identify dependencies (can't do step 3 until step 2 is confirmed)
- Put validation steps early — catch data quality issues before building on them

### Phase 4 — Estimate effort and check feasibility
Apply a rough time estimate per step. If total estimated time exceeds the deadline, cut scope now rather than later.

### Phase 5 — Document risks and assumptions
Before starting:
- What assumptions am I making about the data?
- What could go wrong (data not refreshed, access issues, definition mismatch)?
- What's the fallback if a data source is unavailable?

---

## Output: Analysis Plan

```
## Question
[Business question being answered]

## Sub-questions
1. [Sub-question] → Data source: [X] → Available: ✅/❌
2. [Sub-question] → Data source: [X] → Available: ✅/❌

## Approach
Step 1: [Action] (est. Xm) — depends on: nothing
Step 2: [Action] (est. Xm) — depends on: Step 1
Step 3: [Action] (est. Xm) — parallel with Step 2

## Assumptions
- [Assumption 1]
- [Assumption 2]

## Risks
- [Risk] → Mitigation: [fallback]

## Deliverable
[What the output looks like and who it's for]
```
