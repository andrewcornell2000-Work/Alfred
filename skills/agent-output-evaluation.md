# Agent Output Evaluation — Builder-Validator Pattern

> The verification gap is the #1 cause of multi-agent failure (arXiv 2025: 75.3% of failures trace back to semantic breakdown between a building agent and what was actually asked). The fix is simple in principle and almost never practised: **run a second, fresh agent as a critic before you accept any output**.

*Pattern surfaced 2026-07-09 | Sources: arXiv 2025 multi-agent failure taxonomy, Agentic SDLC Guide (TestQuality/Anthropic 2026), ASDLC.io Critic pattern, LangChain Agent Evaluation Readiness Checklist, ASOS Test-Driven Vibe Development case study*

*Companion skills: `agent-spec-driven.md` (write the success criteria the critic checks against), `agent-self-check.md` (make the builder critique itself first), `agent-workflow-orchestration.md` (embed this pattern inside a longer chain)*

---

## Why this exists

When you ask an agent to build something AND verify it, both jobs go to the same model with the same priors, the same context, and the same blind spots. It will rationalise its own output. This is the "builder validation bias" — the agent saw your request, made assumptions, built to those assumptions, and now checks whether the output matches… those same assumptions.

The builder-validator pattern breaks this by giving the critic role to a **fresh agent with no knowledge of how the output was produced** — only the original requirement and the output to evaluate.

In 2026 workflows:
- **Builder** = the agent that produces the output (Cursor, Claude Code, a Codex run)
- **Critic / Validator** = a second independent pass, often a different model or a fresh context window, that checks the output against the original spec with no access to the builder's reasoning

You already do this in code with tests. This is the same pattern applied to AI-generated outputs.

---

## When to use the critic pattern

Use it if **two or more** of these are true:

- [ ] The output will go to a stakeholder (not just a draft for you)
- [ ] The task involves numbers, formulas, or calculations
- [ ] The builder ran for more than ~20 tool calls
- [ ] The output modifies data or code that others depend on
- [ ] A previous agent session produced something unexpectedly wrong
- [ ] You're about to run a second, more expensive task that depends on this output being correct
- [ ] The original prompt was ambiguous and you wonder if the agent interpreted it correctly

**Skip for:** quick one-off explorations, questions with obvious correct answers, tasks you'll manually review yourself in full anyway.

---

## The four critic patterns (pick the right one)

### Pattern 1: Fresh-window critic (most common)

The simplest and most powerful pattern. Open a new chat (new context window, zero memory of the builder session). Give it:
1. The original requirement (paste your initial prompt)
2. The output to evaluate (paste or file-reference)
3. The evaluation criteria (what "correct" looks like)

**Paste this into a new Cursor/Claude chat:**
```
You are a sceptical peer reviewer. You did NOT produce this output — you're seeing it for the first time.

Original requirement:
[paste your original request]

Output to evaluate:
[paste the output or say "read SPEC.md and current-output.md"]

Your job:
1. Does this output actually satisfy the requirement? Check each criterion.
2. Are there any numbers, formulas, or claims you cannot verify from the output alone? Flag each.
3. List any assumptions the builder probably made that are NOT stated in the requirement.
4. Give a verdict: ACCEPT | NEEDS_FIXES | REJECT, with reasons.

Do not be diplomatic. If something is missing or wrong, say so plainly.
```

---

### Pattern 2: Spec-anchored critic

When you have a `SPEC.md` (see `agent-spec-driven.md`), the critic's job is mechanical: check the output against the spec's success criteria, item by item. This removes all subjectivity.

**Paste this:**
```
Read SPEC.md (the success criteria section) and read [output file or paste output].

For each success criterion in the spec, give a verdict: PASS / FAIL / PARTIAL.
For each FAIL or PARTIAL, quote the specific criterion and explain precisely what's missing.
Do not fix anything yet — just audit.
```

This pattern is best because the success criteria were written *before* the build, so the critic cannot be influenced by what the builder decided to build.

---

### Pattern 3: Adversarial critic (for data/finance outputs)

When numbers are involved, a single critic pass asking "is this correct?" is not enough. You need the critic to actively try to break the output — find the specific number or edge case that would expose a bug.

**Paste this:**
```
You are an auditor trying to find one concrete error in this output.

Output: [paste or reference]
Source data: [paste or reference]

Do the following:
1. Pick the three most important numbers in this output and trace each back to its source. Show your working.
2. Apply these tests:
   a. Do the totals add up? Check vertical and horizontal sums.
   b. Are there any rows where you'd expect a value but the output shows zero or blank?
   c. Does the period/date alignment make sense?
   d. Are percentages calculated from the right denominator?
3. List any number you CANNOT verify from the provided source data.
4. If you find an error, describe it precisely and estimate its materiality.
```

---

### Pattern 4: Goal-alignment critic (for agent sessions that ran long)

When an agent ran for many steps, it often "solution drifts" — starts solving a slightly different problem than you asked. The goal-alignment critic checks that the final output matches the *original* goal, not whatever sub-problem the agent was solving at the end.

**Paste this:**
```
I am going to give you my original goal and an agent's final output. Your only job is to tell me whether the output solves the original goal.

Original goal (what I asked for at the start):
[paste your original prompt or goal]

Final output:
[paste or reference]

Questions:
1. In one sentence, what problem does this output actually solve?
2. Is that the same problem as the original goal? If not, what drifted?
3. What would a correct output look like — describe it in one paragraph?
4. Verdict: ON-TARGET | PARTIAL | OFF-TARGET
```

---

## Embedding the critic into your workflow

### In a single Cursor session (lightweight)

After the builder finishes, open a **second Composer tab** (Cursor supports multiple). Paste Pattern 1 or Pattern 2. Keep the builder tab open but do NOT reference its history in the critic tab. This gives you an independent view for under 60 seconds of setup.

### In a multi-step chain (structured)

Add an explicit `VERIFY` step after every `BUILD` step in your orchestrated workflow:

```
Step 1: SPECIFY — write SPEC.md with success criteria
Step 2: BUILD — agent implements against spec
         → produces: output.md (or Excel, SQL, Python file)
Step 3: VERIFY — fresh critic reads SPEC.md + output
         → produces: evaluation.md (PASS/FAIL per criterion)
Step 4: FIX (only if FAIL) — builder reads evaluation.md and patches
Step 5: RE-VERIFY — critic runs again on patched output
```

Write this as your orchestration prompt:

```
We are running a builder-validator cycle.

Step 1: Read SPEC.md and implement the task. Save output to output.md.
        When done, write: "BUILD COMPLETE — ready for validation."

[new Cursor tab / new session]

Step 2: Read SPEC.md (success criteria) and output.md. 
        Evaluate item by item: PASS/FAIL/PARTIAL.
        Write evaluation.md. Do NOT fix anything.
        When done, write: "VALIDATION COMPLETE."

[I review evaluation.md and decide: ship or loop]
```

### With Codex (autonomous cloud run)

When dispatching to Codex, include the validation step in the task brief:

```
Task brief:
1. Implement [requirement] → write output to output.md
2. After implementing, switch roles: you are now a critic who did NOT write this output.
   Read SPEC.md success criteria. Evaluate output.md item by item.
   Write evaluation.md with PASS/FAIL per criterion.
3. If any FAIL, fix the issue and re-run the evaluation.
4. Only mark the task complete when all criteria are PASS.
```

---

## What to do with the evaluation result

| Verdict | Action |
|---------|--------|
| **ACCEPT / all PASS** | Ship it. Close the critic tab. |
| **NEEDS_FIXES (minor)** | Give the builder the evaluation.md. Say: "Fix only the FAIL items — do not change PASS items." |
| **NEEDS_FIXES (significant)** | Update SPEC.md with what was missing. Re-run the full builder pass against the updated spec. |
| **REJECT / OFF-TARGET** | The original requirement was probably ambiguous. Write a clearer SPEC.md before rebuilding. Don't just re-prompt — the next builder pass will drift in the same direction. |

---

## Practical cost management

Each critic pass adds tokens. Keep costs controlled:

- **Compress the output first** — don't paste a 200-row Excel dump into a critic. Paste a summary table + the 5 most important numbers. The critic validates structure and logic, not every cell.
- **Critic models can be smaller** — for structural/spec checks, a smaller/faster model (Claude Haiku, GPT-4o mini) is often enough. Reserve the full model for adversarial numeric audits.
- **Cap the re-verify loop** — if after two fix-and-revalidate passes you still have FAILs, escalate to a human rather than running another agent loop. The spec is likely wrong or ambiguous.
- **Write evaluation.md, not chat** — when the critic produces its verdict in a file, you can reference it later and it becomes part of the handoff to the next session.

---

## Try asking:

```
I'll give you two things: my original requirement, and the output from the previous agent run.
Act as a fresh critic — you didn't produce this. Does the output actually satisfy the requirement?
Check each criterion and give me PASS/FAIL/PARTIAL with reasons.
```

```
Read SPEC.md success criteria and evaluate output.md against each item.
Give a verdict per criterion. Do NOT fix anything yet — just audit and save the result to evaluation.md.
```

```
You are an auditor. Trace these three numbers back to the source data and show your working.
Then tell me which numbers in this output you CANNOT verify from the data provided.
```

```
My agent ran for 40 steps and produced this output. Does the final output solve my original goal
(which was: [paste original goal])? Or did the agent solve a slightly different problem along the way?
```

```
We're running a builder-validator cycle. Step 1: implement [task] and write output to output.md.
Step 2 — in a fresh context — read SPEC.md and evaluate output.md item by item, then write evaluation.md.
Only call the task complete when all success criteria show PASS.
```

---

## Common mistakes to avoid

| Mistake | Why it fails | Fix |
|---------|-------------|-----|
| Asking the builder to "check your own work" | Same priors, same blind spots — it will rationalise | Use a fresh context window or a different model |
| Giving the critic the builder's chain-of-thought | The critic sees the builder's reasoning and anchors to it | Give the critic only: original requirement + output |
| No written success criteria | The critic has nothing concrete to check against | Write SPEC.md success criteria before building |
| Accepting "looks good to me" from the critic | Too vague — forces the critic to be specific | Use the PASS/FAIL/PARTIAL format explicitly |
| Running 5 fix-revalidate loops | The spec is wrong — more loops won't fix a bad requirement | Stop after 2 loops; fix the spec first |

---

## Quick reference: which pattern for which situation

| Situation | Pattern |
|-----------|---------|
| Agent built a report/summary | Pattern 1 (fresh-window) + Pattern 4 (goal alignment) |
| Agent wrote code or SQL | Pattern 1 (fresh-window) + Pattern 3 (adversarial — run with test inputs) |
| You have a SPEC.md | Pattern 2 (spec-anchored) — most reliable |
| Numbers/financials involved | Pattern 3 (adversarial) — always for finance outputs |
| Long agent run (40+ steps) | Pattern 4 (goal-alignment) first, then Pattern 2 |
| Codex autonomous run | Embed Pattern 2 instructions in the original task brief |
