# Agent Self-Check & Reflection

Use this skill when you want the agent to **verify its own output before declaring done** — catching errors, gaps, and wrong assumptions proactively rather than waiting for you to spot them.

*Distinct from:*
- *`agent-spec-driven.md` — spec is written before the task; self-check runs during and after*
- *`agent-loop-debugging.md` — debugging is reactive recovery after failure; self-check is proactive prevention*
- *`agent-workflow-orchestration.md` — orchestration manages chains of sessions; self-check governs quality within each step*

*Sources: Addy Osmani (Google) "Self-Improving Coding Agents" 2026; Developers Digest "7 Agent Orchestration Patterns"; Production MCP Patterns Part 2 (Agarwal 2026); Claude Code feature guide (Shankar 2026)*

---

## Why agents don't self-check by default

The model's training optimises for completing the turn — producing an answer that looks finished.
"Looks finished" and "is correct" are not the same thing.

An agent will:
- Say "Done!" after writing a function it never tested
- Skip edge cases you didn't explicitly mention
- Stop at 80% of the work because the first pass looked reasonable
- Confirm it checked something it only scanned

**The fix** is not to trust the model's confidence — it is to explicitly trigger a reflection pass as part of the prompt structure.

---

## The four levels of self-check

Use the level that matches the task size. Don't over-engineer small tasks.

| Level | Use when | What it adds |
|-------|----------|-------------|
| **1 — Inline critique** | Quick tasks, single-file edits | One sentence: "What could go wrong?" |
| **2 — Output contract** | Any task with clear success criteria | Explicit assertions checked before done |
| **3 — Reflection pass** | Multi-step tasks, reports, code with logic | Separate "critic" pass after first draft |
| **4 — Test-first loop** | Code changes, data transforms, formulas | Write the check before the implementation |

---

## Level 1 — Inline critique (30 seconds overhead)

Append to almost any prompt:

```
After completing this, state ONE thing that could still be wrong or that you didn't verify.
If you can't think of anything, say "checked: nothing flagged" — but only if you genuinely checked.
```

This prevents the confident-but-wrong "Done!" response by forcing the agent to slow down and
actually examine its output. Especially useful for:
- DAX measures (did the filter context behave as expected?)
- Power Query steps (did the data type change silently?)
- SQL joins (did a row count shift unexpectedly?)

---

## Level 2 — Output contracts

An output contract is a list of **testable assertions** about what the final output must contain.
Write it at the start of the task, and ask the agent to check each assertion before finishing.

### Writing a contract

Good contracts are binary — pass or fail, no "mostly":

```
OUTPUT CONTRACT for this task:
[ ] The summary table has exactly 4 columns: Month, Revenue, Cost, Variance
[ ] The Variance column is calculated as Revenue minus Cost (not Cost minus Revenue)
[ ] The Total row at the bottom matches the column sum
[ ] No hardcoded dollar values — all figures come from named cell references
[ ] The file saves without formula errors (#REF!, #VALUE!, #DIV/0!)
```

### Checking a contract

Append at the end of the task prompt:

```
Before saying done: read through the OUTPUT CONTRACT above and mark each item PASS, FAIL, or 
PARTIAL with a one-line explanation. If any item fails, fix it before continuing.
```

The agent will work through the list rather than doing a vague "this looks good" scan.

### Finance-specific contract examples

**Excel formula task:**
```
[ ] All amounts in AUD
[ ] Negative variances show as red (conditional formatting applied, not manual colour)
[ ] Pivot cache refreshed after data change
[ ] No merged cells in the data range
```

**Power BI measure task:**
```
[ ] Measure returns BLANK, not 0, when no rows exist
[ ] FORMAT wrapper applied to currency measures
[ ] Measure uses CALCULATE, not a plain SUM, so slicers work correctly
[ ] Test: does the measure change when I filter by one department?
```

**Data reconciliation task:**
```
[ ] Row count before vs. after transform is documented
[ ] No duplicate keys in the output
[ ] NULL values in mandatory columns are flagged (not silently dropped)
[ ] Total control sum (sum of all Amount values) matches source
```

---

## Level 3 — Reflection pass

For multi-step tasks or anything where "correct" is subtle — reports, analysis summaries, plans —
ask the agent to do a second pass from the perspective of a critic.

### The critic prompt

```
Now read back what you just produced as if you are a sceptical reviewer seeing it for the first time.
List 3 things that could be wrong, misleading, or incomplete.
For each, either fix it now or explain why it doesn't need to change.
```

This works because it shifts the model's frame from "I produced this" to "someone else produced this".
The same information produces more honest critique when the model is put in the reviewer role.

### Variants

**"Senior analyst" framing:**
```
Review this report as a senior analyst who will present it to the CFO tomorrow.
What would embarrass you if it's wrong? Fix those things first.
```

**"Different department" framing:**
```
A colleague from IT (not finance) will use this output. 
What would confuse them? What assumptions have you made that aren't written down?
```

**"Edge case hunter" framing:**
```
What happens to this logic if: (a) a department has zero headcount, 
(b) the month is the first of the financial year, (c) a cost code doesn't exist in the lookup?
Show me the output for each case.
```

---

## Level 4 — Test-first loop

For code, formulas, or data transforms where correctness can be verified mechanically.
Write the test/assertion before writing the implementation.

### Pattern

```
STEP 1 — Write the test first.
Before writing the [function / measure / transform], write me a test that would FAIL if the logic is wrong.
Show me the expected input and expected output.

STEP 2 — Implement.
Now write the [function / measure / transform] that passes the test from step 1.

STEP 3 — Verify.
Run (or simulate running) the test from step 1 against the implementation from step 2.
Show the actual output vs. the expected output.
```

### Why it works

When the test comes first, the model has to articulate what "correct" means before it starts.
This forces a precision of thought that you don't get from "write a function that does X".

### Finance examples

**Excel formula:**
```
Test first: for an employee with base salary $80,000, 
3 months tenure, and 0.9 performance multiplier — the bonus should be $3,600.
Show your working before writing the formula.
Now write the BONUS formula that produces exactly $3,600 for that input.
```

**DuckDB / SQL transform:**
```
Test first: the output of this query should have exactly one row per Employee-Month combination,
with no NULLs in the Cost column, and the SUM(Cost) should equal the source table total.
Now write the query. Then check each assertion against your output.
```

**Power Query step:**
```
Before adding the merge step: tell me what the row count is before and what it should be after.
Tell me which join type you'll use and why.
Now add the step. Confirm the actual row count matches your prediction.
```

---

## Building self-check into your standard prompts

You don't need to paste a full reflection framework every time.
Add ONE of these short triggers to your usual prompts to get most of the benefit:

| Situation | Append to your prompt |
|-----------|----------------------|
| Any code / formula | "...then confirm it handles [edge case] correctly." |
| Report / summary | "...then flag any number that is an estimate or assumption." |
| Data transform | "...then show me the row count before and after." |
| Long task | "...after each step, tell me if anything surprised you." |
| Final output | "...before saying done, what's the most likely thing that's wrong?" |

---

## The "done" definition

Agents declare done when the conversation turn ends, not when the task is actually finished.
Change the definition of done in your prompt:

```
You are not done until:
1. The output contract above is fully PASS
2. You have stated what you checked and what you didn't
3. You have named the one thing most likely to be wrong (even if you believe it's fine)
```

This makes "I'm done" a meaningful statement rather than a polite way to end the turn.

---

## Pre-task self-check setup (30-second ritual)

Before a non-trivial task, paste this:

```
Before you start:
1. Restate the goal in one sentence to confirm you understood it
2. Name the ONE thing that would make this output wrong even if everything else is right
3. Tell me what you'll check when you're done

[then describe the task]
```

This takes 30 seconds and catches the most common source of failure — agent starts on a subtly
wrong interpretation and you don't find out until the very end.

---

## Connecting to the skill family

| Need | Skill |
|------|-------|
| Write success criteria before starting | `agent-spec-driven.md` → SPEC.md template |
| Agent went wrong and needs recovery | `agent-loop-debugging.md` → 6 failure modes |
| Task spans multiple sessions | `agent-workflow-orchestration.md` → checkpoint pattern |
| Context window is bloated | `agent-context-engineering.md` → compression techniques |
| Running parallel sub-tasks | `agent-parallel-worktrees.md` → git worktree setup |

---

## Try asking

```
Before you write this DAX measure — state what the correct output should be 
for a slicer showing only the IT department. Then write the measure and verify it.
```

```
Review what you just produced as if you are a sceptical colleague 
who will stake their reputation on it. List 3 things that could still be wrong.
```

```
You're not done until you've shown me the row count before and after this 
Power Query merge step, and confirmed no unexpected NULLs appeared.
```

```
Write a test case FIRST: what input values and expected output would expose 
a bug in this formula? Then write the formula. Then verify it passes the test.
```

```
After completing this report section — flag every number that is an estimate 
or assumption rather than a hard figure from the source data.
```
