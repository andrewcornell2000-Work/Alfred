# Agent Workflow Orchestration

Use this skill when a task is too big for a single agent session — when it spans multiple tools,
multiple files, multiple decision points, or takes more than ~30 tool calls to complete.

Orchestration is the art of **breaking a big task into a sequence of focused agent calls, each
with clean inputs and outputs, so that failures are contained and progress is preserved**.

*Companion skills: `agent-parallel-worktrees.md` (run steps in parallel), `agent-context-engineering.md`
(manage what's in each step's window), `agent-loop-debugging.md` (recover when a step fails).*

---

## 1. When to orchestrate vs. single-session

Not every task needs orchestration. Over-engineering a simple request wastes setup time.

| Signal | Single session | Orchestrate |
|--------|---------------|-------------|
| **Estimated tool calls** | < 20 | > 30 |
| **File blast radius** | 1–3 files | 5+ files or multiple systems |
| **Distinct phases** | 1 (just do it) | 3+ (plan → build → verify) |
| **Human checkpoints needed** | 0 | 1–2 (approve before destructive step) |
| **Parallel sub-tasks** | None | 2+ independent workstreams |
| **Context bleed risk** | Low | High (Power BI + Excel + code changes at once) |
| **Cost sensitivity** | Low | High (sub-agents multiply token spend) |

**Default rule:** If you'd naturally say "first do X, then once that's done do Y", that's a chain.
If X and Y can proceed simultaneously without sharing files, that's parallel (see `agent-parallel-worktrees.md`).

---

## 2. The three orchestration patterns

### Pattern A: Linear chain (most common)

Each step produces a **checkpoint artifact** that the next step reads. The chain stops if any
step produces an error checkpoint.

```
Step 1 → checkpoint-1.md
Step 2 reads checkpoint-1.md → checkpoint-2.md
Step 3 reads checkpoint-2.md → final output
```

**When to use:** Sequential tasks where each step depends on the previous result.
**Example:** Analyse data → write report → format for PowerPoint.

### Pattern B: Orchestrator + workers

One "orchestrator" session breaks the task, writes a task manifest, then spawns parallel worker
sessions (via git worktrees — see `agent-parallel-worktrees.md`). Workers write results back to
agreed files; orchestrator aggregates.

```
Orchestrator → tasks/manifest.md (list of 4 sub-tasks)
Worker A (worktree-a) → results/analysis.md
Worker B (worktree-b) → results/schema.md
Orchestrator reads both → final/report.md
```

**When to use:** Independent sub-tasks that can run simultaneously. Classic use: one agent
refactors module A while another writes tests for module B.
**Cost warning:** Orchestrator + 3 workers = 4× token spend. Only worth it when total wall-clock
time saved exceeds the parallel overhead.

### Pattern C: Human-in-the-loop gate

A linear chain with mandatory pause points where you review an intermediate artifact before
the next step proceeds. Prevents a bad plan from being fully executed before you spot it.

```
Step 1: Plan → PAUSE (you review plan.md)
Step 2: Implement (only after you say "go")
Step 3: Verify → PAUSE (you review test results)
Step 4: Ship
```

**When to use:** Destructive actions (publish, overwrite, delete), API calls that cost money,
or any step where a wrong first step would make the next steps worthless.

---

## 3. Checkpoint artifacts — the glue between steps

A checkpoint file is what one agent step leaves for the next. **Checkpoints must be
self-contained** — the next step should be able to run with only the checkpoint + the original
task brief, without needing to re-read all previous conversation history.

### Good checkpoint structure

```markdown
# Checkpoint: [Step Name]
_Generated: [timestamp]_
_Status: COMPLETE | PARTIAL | NEEDS_REVIEW_

## What was done
- [bullet list of concrete actions taken]

## Key decisions
- [decision]: [rationale] — because the next step needs to know why, not just what

## Output artifacts
- [file path or system]: [description]

## Blockers / open questions
- [anything the next step needs to decide or check]

## Next step input
[the exact thing Step N+1 needs: a file list, a schema, a confirmed value, etc.]
```

### Anti-patterns to avoid

- **Narrative checkpoints** — prose like "I did various things and it went well" is useless.
  The next agent will hallucinate what "various things" means.
- **Checkpoint by reference** — "see the code I wrote" without listing which files. The next
  session may not have the same filesystem context.
- **No status field** — if a step partially completes before context limit, the next step needs
  to know which parts are done and which aren't.
- **Implicit assumptions** — "the schema is what we discussed" is not a checkpoint. Write the
  schema in the checkpoint.

---

## 4. Designing the task brief

Every agent step in a chain needs a **task brief** — a short, focused instruction that scopes
what the step should and should not do.

### Task brief template

```
## Task: [Step Name]

**Goal in one sentence:** [what this step must produce]

**Read:** [checkpoint files or artifacts from previous steps]

**Write:** [exact files/artifacts this step must produce before it finishes]

**In-scope:**
- [explicit list of what this step does]

**Out-of-scope (do NOT do):**
- [things that belong in a later step — be explicit]

**Done when:**
- [ ] [verifiable condition 1]
- [ ] [verifiable condition 2]
```

### Why "out-of-scope" matters

Without an explicit out-of-scope list, an agent in step 2 will helpfully start doing step 3,
producing partial step-3 work with step-2 context — and your step-3 agent will then re-do it
with different assumptions. Over-helpful agents are a bigger risk than unhelpful ones in chains.

---

## 5. Handoff state management

State that must survive across steps should be written to a **persistent handoff file** — not
just the checkpoint. Think of it as a shared memory that every step in the chain can read and
update.

### Recommended handoff file structure (`tasks/HANDOFF.md`)

```markdown
# Task Handoff State
_Task:_ [top-level goal]
_Started:_ [date]
_Current step:_ [step name]

## Confirmed facts
| Fact | Value | Confirmed by |
|------|-------|-------------|
| Finance folder path | C:\Finance\FY26 | Step 1 |
| Target Power BI file | FY26-Budget.pbix | Step 1 |
| Reporting period | June 2026 | You (pre-flight) |

## Decisions made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Variance threshold | ±5% | Andrew confirmed |
| Output format | PPTX + markdown | Step 2 |

## Step status
| Step | Status | Output |
|------|--------|--------|
| 1. Gather data | ✅ Done | tasks/checkpoint-1.md |
| 2. Analysis | 🔄 In progress | — |
| 3. Report | ⏳ Pending | — |

## Open questions
- [anything unresolved that a later step needs to handle]
```

**Where to store it:** In the repo under `tasks/` or a temp folder. Use `filesystem` MCP to
write/update; every step reads it at the start via a `read_file` call.

---

## 6. Using Claude Code sub-agents in practice

Claude Code's `Task` tool lets you spawn a sub-agent from within a session. As of 2026, a
single session supports up to 1,000 sub-agents with 16 concurrent paths. Practical limits are
lower — each sub-agent costs tokens, and context bleed between them is a real risk.

### Sub-agent prompt pattern

```
<task>
You are a sub-agent working on step 2 of a 4-step pipeline.

Read: tasks/checkpoint-1.md (what step 1 produced)
Read: tasks/HANDOFF.md (confirmed facts and decisions)

Your job: [single focused goal]

Write your result to: tasks/checkpoint-2.md using the checkpoint format in HANDOFF.md.

Do NOT: [explicit list of out-of-scope things]

Done when: tasks/checkpoint-2.md exists and contains a "Status: COMPLETE" line.
</task>
```

### Costs for sub-agents (rough guides, June 2026)

| Scenario | Sessions | Approx tokens | When worth it |
|----------|----------|---------------|---------------|
| Linear chain, 3 steps | 3 sequential | ~150k total | Task > 30 tool calls |
| Orchestrator + 3 workers | 4 parallel | ~200k total | Steps are independent AND total time matters |
| Full analysis + report + PPT | 4 sequential | ~180k total | Different tools/skills per step |

---

## 7. Decision framework: right pattern for common tasks

### "I need to analyse a dataset, write a report, and build a Power BI model from it"

Use **linear chain** (Pattern A):
1. Step 1 (Claude Code + duckdb MCP): analyse data → checkpoint with key findings + schema
2. Step 2 (Claude Code): write report markdown → checkpoint with narrative + table data
3. Step 3 (Claude Code + Power BI MCP): build model using schema from checkpoint-1 + data from
   checkpoint-2

**Human gate:** After step 1 — check the schema before steps 2 and 3 build on it.

### "I need to refactor 5 modules and write tests for each"

Use **orchestrator + workers** (Pattern B):
1. Orchestrator: read current structure → write tasks/manifest.md listing which module each
   worker handles, and the interface contract each must preserve
2. Workers A–E (one per worktree): each refactors one module, writes its tests, commits to its branch
3. Orchestrator: merge branches, resolve conflicts, run full test suite

### "I need to clean a messy Excel file and load it into Power BI"

Use **linear chain with human gate** (Pattern C):
1. Step 1 (excel-mcp): inspect columns, find inconsistencies → checkpoint listing problems
2. **PAUSE**: you review the problem list and confirm transformation rules
3. Step 2 (excel MCP + power query): apply transformations → checkpoint with before/after row counts
4. Step 3 (Power BI MCP): import cleaned data, build measures → model live in Desktop

---

## 8. Pre-flight checklist for any orchestrated workflow

Run this before you start step 1:

- [ ] Can I describe the end result in one sentence? If not, the task isn't scoped enough yet
- [ ] Do I know which files/systems will be touched by each step?
- [ ] Are there destructive actions? → add a human gate before each one
- [ ] Have I written HANDOFF.md with confirmed facts (paths, names, periods)?
- [ ] Does each step have an explicit out-of-scope list?
- [ ] Do I have a verification step (not just an action step) at the end?
- [ ] If this is parallel: are the sub-tasks truly independent? (shared files = not independent)

---

## 9. Try asking

Paste any of these into Cursor or Claude Code to put this skill into action:

**Design the workflow before starting:**
> "Before we start: this task has 3 distinct phases (gather data, build model, write report). Break it into 3 agent steps. For each step, write a one-sentence goal, list the inputs it reads, the output it writes, and what's explicitly out of scope."

**Create a handoff file before a multi-step task:**
> "Create a HANDOFF.md file for this task. Include: confirmed facts (the file paths I've given you), decisions still open, and a step-status table with 3 steps. I'll fill in the open decisions before we start step 1."

**Use a checkpoint when finishing a step:**
> "You've finished the analysis. Before we move on: write a checkpoint-1.md summarising exactly what you found, which files you changed, any decisions you made and why, and what step 2 needs to know."

**Spawn a focused sub-task:**
> "Treat this as a sub-agent task. Read tasks/checkpoint-1.md. Your only job is to build the Power BI measures listed there. Do NOT touch the report visuals — that's step 3. Write checkpoint-2.md when done."

**Enforce an explicit out-of-scope boundary:**
> "Stop. Step 2 is analysis only — you've started building the report, which is step 3. Roll back the report changes and write your checkpoint-2 now. I'll start a new session for step 3."

**Design a parallel worktree workflow:**
> "These 4 modules are independent — no shared state. Design a manifest.md that lets 4 parallel agents each handle one module. Include which files each agent owns and the interface contract each must preserve."

---

## 10. Quick reference

| Thing | What to do |
|-------|-----------|
| Task > 30 tool calls | Split into a chain |
| Steps share files | Keep them sequential, not parallel |
| Destructive step | Add human gate before it |
| Agent doing next step's work | Explicit out-of-scope list in task brief |
| Context bleed between steps | Fresh session + checkpoint as only input |
| Sub-agent cost concern | Use linear chain; only go parallel if time savings > 2× |
| Sub-tasks are independent | Use worktrees (see `agent-parallel-worktrees.md`) |
| Forgot a decision mid-task | Write it to HANDOFF.md immediately |

---

*Available in Cursor after next provision (`Provision-Cursor.ps1`).*
*Companion: `agent-parallel-worktrees.md` | `agent-context-engineering.md` | `agent-loop-debugging.md`*
