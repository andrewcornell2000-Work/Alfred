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

## Blockers / assumptions
- [anything the next step must know or verify before proceeding]

## Next step prompt
[paste-ready prompt for the next session, including which checkpoint to read]
```

### What makes checkpoints fail

| Bad pattern | Why it breaks the next step |
|-------------|----------------------------|
| "Done!" as the checkpoint | Next session has no context — re-reads everything, wastes tokens |
| List of files changed, no decisions | Next step doesn't know *why* a file looks the way it does |
| Checkpoint assumes same conversation continues | New session has zero memory of previous turns |
| Missing "next step prompt" | Human must reconstruct the correct starting prompt from scratch |

---

## 4. Output contracts — defining exactly what format step N must produce for step N+1

The most common source of orchestration failure is not tool errors or context loss — it's
**format mismatch**: step N produces output in a form that step N+1 cannot directly consume.

An **output contract** is a brief, explicit declaration at the top of a step's prompt that
tells the agent: "Your output must be in THIS shape, because the next session will read it
directly without any reformatting."

### Why this matters

Without an output contract, the agent makes a format choice based on what "looks good" to
a human reader — markdown prose, comma-separated inline lists, narrative paragraphs. The
next step (which may be a different agent session, a Power Query transform, or a Python script)
then has to guess the format and often gets it wrong.

**Example failure:**
- Step 1 produces a summary as a prose paragraph: *"The three main cost drivers are wages, rent, and IT..."*
- Step 2 tries to read this as a structured table → fails, or produces garbage

**With an output contract:**
- Step 1 is told: "Output a markdown table with columns: Driver | Amount | % of Total"
- Step 2 reads a clean, predictable table → works every time

### Output contract templates

**For data passed between two agent sessions:**
```
Your output for this step must be a markdown file at checkpoint-2.md structured EXACTLY as:

# Step 2 Output
## Summary table
| Column A | Column B | Column C |
|----------|----------|----------|
[rows here]

## Flags
- [any anomalies or assumptions, one per bullet]

DO NOT include prose paragraphs — the next agent session reads only this file.
```

**For data that feeds a Python/DuckDB script:**
```
Write your output as a CSV with a header row. Column names must be:
date, category, amount, source
No extra columns. No summary rows. No totals row at the bottom.
File path: data/step2-output.csv
```

**For data that feeds Power Query:**
```
Output a flat Excel table (no merged cells, no grouped rows).
First row is the header. Column names use underscores, not spaces.
No blank rows between the header and data.
Sheet name: data
```

**For data that feeds a Word / report template:**
```
Output your findings as structured sections matching these headings EXACTLY:
## Executive Summary
## Key Findings
## Recommendations
Each section: 3–5 bullet points maximum. No sub-sections.
```

### Paste-ready output contract prompt pattern

Use this at the start of any step whose output feeds something else:

```
Before you write any output, re-read the output contract below and confirm you will follow it.
Then produce your output.

OUTPUT CONTRACT:
- Format: [markdown table | CSV | JSON array | flat prose | numbered list]
- File: [path and filename]
- Required columns/sections: [list them]
- Prohibited: [merged cells | prose paragraphs | totals rows | sub-sections — whatever breaks downstream]
- The next step is: [brief description of what reads this output]
```

---

## 5. Handoff prompt — starting a downstream step cleanly

When you start the step that reads a checkpoint, use this pattern:

```
Read checkpoint-2.md first. Do not ask clarifying questions — all context is in that file.
Your task is: [specific task for this step only].
Output contract: [paste the output contract for THIS step's output].
Stop after producing the output — do not attempt the next step.
```

**Key elements:**
- "Read [file] first" — prevents the agent from relying on session history (there is none)
- "Do not ask clarifying questions" — checkpoint contains everything; questions mean the checkpoint was incomplete
- "Stop after" — prevents the step from helpfully continuing into territory you haven't approved

---

## 6. Task manifest for Pattern B (orchestrator + workers)

When breaking work into parallel streams, the orchestrator should write a manifest before
spawning workers. Workers read only their section.

```markdown
# Task Manifest
_Created by orchestrator: [timestamp]_
_Status: ACTIVE_

## Shared context
[1–3 bullets every worker must know]

## Task A — [Worker A's stream name]
- **Scope:** [exactly what this worker does — no more]
- **Input files:** [list]
- **Output contract:** [format + file path]
- **Must NOT touch:** [files out of scope]

## Task B — [Worker B's stream name]
- **Scope:** [...]
- **Input files:** [...]
- **Output contract:** [...]
- **Must NOT touch:** [...]

## Aggregation step
- Run after BOTH workers write their outputs
- Reads: [Task A output file], [Task B output file]
- Produces: [final output]
```

---

## 7. Try asking

These prompts activate orchestration patterns directly in Cursor or Claude Code.

**Starting a linear chain:**
> "This task has 3 phases: clean the CSV, build the Power Query model, then write the summary report. Set up the chain — write the checkpoint template we'll use between phases, define the output contract for each handoff, and give me the starting prompt for phase 1."

**Enforcing an output contract:**
> "Before you start — state the output contract for this step: what file you will write, what format, what columns, and what the next session will do with it. Confirm you understand it, then produce the output."

**Pausing for human review before a destructive step:**
> "Complete phase 1 (the analysis), write checkpoint-1.md, then STOP and ask me to review before you do anything else. Do not start phase 2 until I explicitly say 'go'."

**Spawning parallel workers from an orchestrator:**
> "Break this task into 2 independent streams — one for the data model changes and one for the report visuals. Write a task manifest for each stream with clear output contracts, then tell me the worktree setup commands."

**Starting a downstream step from a checkpoint:**
> "Read checkpoint-2.md. All context is in that file — do not ask me clarifying questions. Your task is to produce the final Power BI measures file. Follow the output contract in the checkpoint exactly."

**Diagnosing a format mismatch mid-chain:**
> "The output from step 1 is in the wrong format for step 2. Compare checkpoint-1.md against what the output contract required, identify the discrepancy, and tell me the minimum edit to make it compatible without re-running step 1."
