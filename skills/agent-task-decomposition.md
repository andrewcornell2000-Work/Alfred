# Agent Task Decomposition — Plan Before You Execute

> The single most reliable way to prevent agent disasters is to make the agent plan out loud before it touches a single file. Every 10 minutes you spend on decomposition saves an hour of untangling.

*Pattern current as of 2026 | Sources: Claude Code Plan Mode (Anthropic), zeroentropy.dev planning-decomposition, r/ClaudeCode community workflows, Trilogy AI planning guide, "Plan-and-Execute" agent architecture (LangChain / ReAct lineage)*

---

## Why decomposition fails without a discipline

Agents that one-shot complex tasks typically fail in one of four ways:

| Failure mode | What it looks like | Root cause |
|---|---|---|
| **Scope creep** | Agent refactors three extra files you didn't ask about | No boundary on what "done" means |
| **Hidden dependency** | Step 4 needs output from Step 2 but Step 2 wasn't run first | No dependency map before starting |
| **Silent assumption** | Agent invents a column name that doesn't exist in the data | No "check inputs first" gate |
| **Wrong decomposition** | Agent splits "build the report" into 12 micro-steps that don't match your data model | Agent decomposed without reading files |

All four are prevented by **decompose → review → execute**, not by a better execution prompt.

---

## When to decompose (decision checklist)

Decompose explicitly if **two or more** of these are true:

- [ ] The task touches more than one file or data source
- [ ] You'd struggle to explain all the steps in one sentence
- [ ] There are order-of-operations constraints ("X must happen before Y")
- [ ] The task will take the agent more than ~5 tool calls to complete
- [ ] Any step produces output that a later step depends on
- [ ] The output matters enough that getting it wrong is costly to fix
- [ ] You're not 100% sure what data/columns/sheets are available

**One-shot is fine for:** "what does this function do?", "fix this typo in the formula", "rename this column", "add a total row to this table".

---

## Claude Code Plan Mode (the built-in gate)

Claude Code has a native **Plan Mode** — a session state where the agent reads files, searches, and reasons, but **cannot write files or run side-effecting commands**. It's the safest way to force decomposition.

### Activating Plan Mode

```
# In Claude Code terminal:
claude --plan            # start in plan mode (non-destructive read-only)

# Or mid-session, press:
Shift+Tab               # toggle Plan Mode on/off (Claude Code ≥ 1.0)
```

In Plan Mode, Claude will tell you what it would do, list files it would change, and surface dependency questions — without touching anything. You review, correct, then press Shift+Tab again to let it execute.

### Plan Mode prompt pattern

```
[Plan Mode is ON — do not write any files yet]

I want you to plan the following task. For each step:
- State what you will do in plain English
- List the file(s) or data sources you will read or write
- State what the step produces (output) and what depends on it
- Flag any assumption you're making that I should confirm

Task: [your task here]

Do NOT execute yet. Present the plan as a numbered list and ask me to confirm.
```

---

## The decomposition prompt (Cursor / Claude Code / Codex)

When you're not in Claude Code, paste this before any complex task:

```
Before writing any code or making any changes, produce a decomposition:

1. Read the relevant files first (list which ones you'll look at)
2. Write a numbered plan with:
   - Each step in plain English
   - What file / tool it uses
   - What it produces
   - What later steps depend on it
3. Flag any ambiguity or assumption you're making
4. Mark which steps can run in parallel and which must be sequential

Do not start executing until I confirm the plan.
```

---

## Dependency-first decomposition (for data workflows)

For finance/office tasks where data flows between steps, add a **dependency check** before the plan:

```
Before decomposing the task, answer these questions:
1. What data sources does this task need? List file names, sheet names, or table names.
2. Which sources can you confirm exist right now vs. which are assumed?
3. Are there any columns or fields you'll need that you haven't seen yet?
4. Does any step require output from a previous step before it can run?

Then write the dependency map as: Step N → depends on → [Step M output / file X / confirmation from me]
```

### Example output you want to see

```
Dependency map for "build July labour cost variance report":
- Step 1: Read wages export (wages_jul_2026.xlsx) → produces clean headcount table
- Step 2: Read budget file (budget_2026.xlsx, Sheet "Headcount Budget") → produces budget baseline
  ⚠ ASSUMPTION: budget sheet name is "Headcount Budget" — please confirm
- Step 3: Join on Employee_ID → depends on Step 1 + Step 2 both complete
- Step 4: Calculate variance % → depends on Step 3
- Step 5: Write output to variance_report.xlsx → depends on Step 4
- Steps 1 and 2 can run in parallel. Steps 3–5 must be sequential.

Shall I proceed with this plan?
```

---

## Finance and office examples

### "Build me the monthly variance report"

❌ **Don't:** "Build me the monthly labour variance report for July."
*(Agent invents column names, guesses the budget sheet, overwrites the wrong file)*

✅ **Do:**
```
Before building the July labour variance report:
1. List every file you'll need to read and confirm they're visible to you
2. Show me the column names in each source — don't assume
3. Write a numbered plan with dependencies
4. Tell me which output file you'll create and where
Do not write anything until I confirm.
```

---

### "Analyse this CSV and summarise for the exec"

```
Before analysing the CSV:
1. Read the file and list: row count, column names, date range if applicable, any nulls in key columns
2. Write a 3-point plan: what you'll calculate, what you'll ignore, what format the summary will use
3. Flag any column where the meaning isn't obvious from the name alone
Confirm with me before writing the summary.
```

---

### "Refactor the data pipeline to add the new department mapping"

```
Before touching any files:
1. Grep for every place "department" or "dept" appears in the pipeline folder
2. List all files that reference the current mapping
3. Write a plan: which files change, in what order, and what breaks if the mapping column is renamed
4. Identify whether there's a test or validation step that should run after each change
Present the plan — don't edit files yet.
```

---

### "Create a new Power BI measure for headcount variance"

```
Before writing the DAX:
1. List the existing tables and columns relevant to headcount in this model
2. Confirm which base measure (if any) the new one builds on
3. Write the measure in plain English first ("headcount actual minus headcount budget, as a % of budget")
4. Then write the DAX and explain each function call in one line
Show me before adding it to the model.
```

---

## After the plan is approved — the execute prompt

```
The plan is approved. Execute step by step.
After each step:
- State what you did
- Show me the key output or result (row count, value, file written)
- Confirm whether the next step's dependency is now satisfied
If anything unexpected happens, pause and ask rather than guessing.
```

---

## Decomposition anti-patterns

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| Asking the agent to plan AND execute in the same prompt | Agent skips straight to execution | Two separate prompts: plan first, then explicit approval |
| Accepting a plan without checking assumptions | Agent's "assumption" is often wrong | Require every assumption to be flagged and confirmed |
| Plans with no output artifacts named | Agent produces something but you don't know where it went | Every step must name its output |
| Over-decomposing simple tasks | 12 steps for a column rename wastes time | Apply the decision checklist — one-shot simple things |
| Plan that skips "read first" | Agent writes code without knowing the actual schema | First step of every data task must be "read and list column names" |

---

## Relationship to other skills

| Skill | What it adds |
|---|---|
| `agent-spec-driven.md` | Use once decomposition reveals a task spans sessions — write SPEC.md before executing |
| `agent-workflow-orchestration.md` | Use when executing an approved multi-step chain across tools |
| `agent-parallel-worktrees.md` | Use when the dependency map shows steps that can truly run in parallel |
| `agent-loop-debugging.md` | Use when execution goes wrong mid-plan |
| `agent-self-check.md` | Use at the verify step after execution |

---

## Try asking

- **"Before you start — read the relevant files and show me a numbered plan with dependencies. Don't write anything until I confirm."**
- **"List every assumption you're making about this data. I'll confirm or correct each one before you proceed."**
- **"Split this task into steps. Mark which can run in parallel and which must be sequential. Show the dependency map."**
- **"Build me the July headcount variance report — but first list the files you'll need and confirm they're there, then get my approval on the plan before writing anything."**
- **"This looks like a 10-step task. Plan it in Claude Code Plan Mode first so nothing gets touched until I've reviewed the steps."**
- **"What's your plan for this refactor? Walk me through every file you'd change, in what order, and why — before you edit anything."**

---

*Skill added: 2026-07-17 | Iteration #17 | Distinct from agent-spec-driven (task planning layer) and agent-workflow-orchestration (execution layer)*
