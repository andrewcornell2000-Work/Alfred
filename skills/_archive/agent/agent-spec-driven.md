# Spec-Driven Development with AI Agents

> Write the spec before the prompt. The spec is the source of truth — the agent implements against it. When something changes, you update the spec and re-run, not chase the agent through conversation.

*Pattern surfaced 2026-06-18 | Sources: GitHub Spec Kit (open-source), Addy Osmani (Google), Augment Code guide, ProductBuilder.net 2026 survey of Claude Code / Cursor workflows*

---

## Why this exists

Agents go wrong not because the model is bad — they go wrong because you gave the agent a one-line prompt and expected it to reconstruct all your business rules, edge cases, constraints, and success criteria from context. Every new session loses that reconstruction.

**Spec-driven development** (SDD) fixes this by putting every decision in a persistent markdown file *before* the agent writes any code. The agent builds against the spec; the spec is the single source of truth.

This is now the dominant professional pattern for multi-file, multi-session agent work. GitHub Spec Kit, AWS Kiro IDE, and Claude Code all have native spec tooling in 2026.

---

## When to use spec-driven (decision checklist)

Use a spec file if **two or more** of these are true:

- [ ] The task spans more than one session or involves multiple files
- [ ] There are business rules / formatting rules that aren't obvious from the codebase
- [ ] You'll need to explain to someone else why the output looks the way it does
- [ ] The output will be re-run or maintained (not a one-off exploration)
- [ ] You care about specific edge cases or failure modes
- [ ] The task touches data that changes (reports, financial summaries, CSVs)

**Skip the spec for:** one-off exploratory questions, quick 5-minute fixes, asking what a function does.

---

## The four-phase workflow

```
SPECIFY → PLAN → IMPLEMENT → VERIFY
```

### Phase 1 — SPECIFY (you write this; ~10 minutes)

Create `SPEC.md` in the project root (or task folder). Include:

```markdown
## What this builds
One paragraph: what output exists when this is done, who reads it, what decision it informs.

## Inputs
- File/source A — what it contains, format, where it lives
- File/source B — ditto

## Expected output
- Format: Excel / markdown table / Power BI measure / Python script
- Key columns / sections that MUST appear
- Example row (if tabular)

## Business rules
- Rule 1 (e.g., "costs are allocated to department by headcount ratio")
- Rule 2 (e.g., "flag any row where variance > 10%")
- Rule 3

## Edge cases
- What to do if source data is missing
- What to do if values are negative / zero
- What to do if a column is renamed in the source

## Success criteria (definition of done)
- [ ] Output file exists at path X
- [ ] Section Y contains Z
- [ ] Total row matches manual calculation
- [ ] No hardcoded values — all formulas reference named ranges

## Out of scope
- What the agent should NOT do (prevents scope creep)
```

### Phase 2 — PLAN (agent-generated; you review)

Paste this into Cursor/Claude:

```
Read SPEC.md and produce a step-by-step implementation plan before writing any code.
For each step, state: what you'll do, what file you'll change, and what the success check is.
Do NOT write code yet — I need to review the plan first.
```

Review the plan. Fix misunderstandings in SPEC.md (not in chat) before proceeding. This is the key discipline: **the spec is always updated to reflect decisions**, not the other way around.

### Phase 3 — IMPLEMENT (agent executes against spec)

```
Implement the plan from SPEC.md step by step. After each step, note what you did and what the check result was. If a step fails, update SPEC.md with what you learned and retry.
```

### Phase 4 — VERIFY (you or agent checks the spec's own criteria)

```
Read SPEC.md → "Success criteria" section and check each item against the current output. 
List: PASS / FAIL / PARTIAL for each criterion. If FAIL, explain what's missing.
```

If anything fails, you update SPEC.md with the fix, and the agent re-runs *only the failing section*.

---

## SPEC.md template for finance / report work

Copy this for Excel reports, Power BI measures, data extracts:

```markdown
# SPEC — [Report Name] — [Date]

## What this builds
[Report name] for [audience] covering [period]. Used to [decision it informs].

## Source data
| Source | Format | Location | Key columns |
|--------|--------|----------|-------------|
| Payroll export | CSV | finance/payroll_June.csv | StaffID, Dept, Hours, Rate |
| Budget template | Excel | finance/budget_FY26.xlsx | Dept, BudgetHours, BudgetRate |

## Output
- File: finance/labour_variance_June.xlsx
- Sheet: "Summary" — one row per department, columns: Dept, ActualCost, BudgetCost, Variance$, Variance%
- Sheet: "Detail" — every staff row with flag column
- Sheet: "Notes" — methodology + data quality notes

## Business rules
1. Actual cost = Hours × Rate (not from a pre-calculated column)
2. Variance = Actual − Budget (negative = underspend, positive = overspend)
3. Flag rows where |Variance%| > 5%
4. Exclude contractors (StaffID starting with "C-")

## Edge cases
- Missing budget for a dept → show Actual cost, Variance = "No budget"
- Zero hours → include row, cost = $0, do not divide by zero
- Duplicate StaffID → sum hours, flag in Notes sheet

## Success criteria
- [ ] Summary sheet has exactly one row per unique department
- [ ] Total Actual in Summary matches SUM of Detail sheet
- [ ] Flag column present in Detail
- [ ] No hardcoded numbers — all totals are Excel formulas
- [ ] Notes sheet explains any departments with "No budget"

## Out of scope
- Do not reformat source CSV files
- Do not update the budget template
- Do not send or share the output file
```

---

## Anti-patterns to avoid

| What people do | Why it fails | Fix |
|----------------|--------------|-----|
| Put all rules in the chat prompt | Lost when context resets | Put rules in SPEC.md |
| Update rules in conversation | Next session doesn't know | Always edit SPEC.md |
| Ask agent to "figure out edge cases" | Agent invents plausible-sounding rules | You decide; agent executes |
| One massive prompt for everything | Agent can't verify its own output | Break into Plan → Implement → Verify |
| Skip the "out of scope" section | Agent helpfully adds unrequested features | Always list what NOT to do |
| Vague success criteria | "Does it look right?" is not verifiable | Write testable criteria (row counts, totals match) |

---

## Connecting to existing skills

- **agent-workflow-orchestration.md** — use SPEC.md as the "brief" that each phase of a multi-session workflow reads. The HANDOFF.md checkpoint file captures runtime state; SPEC.md captures design intent.
- **agents-md-project-context.md** — CLAUDE.md / .cursorrules sets agent defaults; SPEC.md is task-specific. Don't mix them.
- **agent-context-engineering.md** — spec-driven is context engineering applied to design-time. The spec is context you write once and reuse across all sessions.
- **data-analysis-planning.md** — for exploratory data work, write a lightweight spec (just "What questions" + "Expected output format") before asking the agent to analyse.

---

## Try asking:

**Kick off a spec-first task:**
```
Before writing any code, read this brief and draft a SPEC.md for me to review.
Brief: I need a monthly labour variance report — actual vs budget, by department, 
flagging anything over 5%, sourced from the CSV in the finance folder. 
Output: Excel file with Summary, Detail, and Notes sheets.
```

**Generate the plan from a spec:**
```
Read SPEC.md and write a step-by-step implementation plan — what you'll do, 
what file you'll touch, and how you'll verify each step. Do NOT write code yet.
```

**Verify a finished task against its spec:**
```
Open SPEC.md and go through every item in "Success criteria". For each one, 
show me the evidence it passes (formula, row count, whatever the check is). 
Mark PASS / FAIL / PARTIAL.
```

**Update a spec mid-task when a rule changes:**
```
The finance team says contractors with "C-" IDs should now be INCLUDED but 
flagged separately, not excluded. Update SPEC.md to reflect this change, 
then re-run only the filtering step.
```

**Start a report spec from scratch:**
```
Help me write a SPEC.md for a working capital report. Ask me questions 
one at a time: what the report is for, what data sources exist, what 
columns the output needs, what the business rules are, and what "done" looks like.
```

**Catch scope creep before it happens:**
```
I'm about to ask you to build X. Before I do: read SPEC.md and tell me 
if X is in scope, out of scope, or ambiguous. If ambiguous, ask me to 
clarify and I'll update the spec.
```

---

## Quick reference

```
Spec-driven loop:
 1. Write SPEC.md  →  agent reads it, NOT your chat memory
 2. Ask for PLAN  →  review before any code runs
 3. Say IMPLEMENT →  agent cites spec sections as it works
 4. Say VERIFY    →  agent checks success criteria, not "does it seem right"
 5. When rules change → edit SPEC.md first, then re-run

Key rule: the spec is always ahead of the code.
         If they disagree, the spec wins.
```
