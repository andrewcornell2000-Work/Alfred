# Alfred's Discovery Log
*Every breakthrough. Every build. Every insight. Never deleted.*

---

> Loop started 2026-06-05. First discovery pending — awaiting iteration 1.

---

## Format
```
### [ITERATION N] [TYPE] — Title
**Date:** YYYY-MM-DD
**Type:** INSIGHT | TECHNIQUE | BUILD | BREAKTHROUGH
**What I found:** ...
**Why it matters:** ...
**What it unlocks:** ...
**Artifact:** (file path, account, commit hash)
```

---

### [ITERATION 10] TECHNIQUE — Agent Handoff Pattern (HANDOFF.md)
**Date:** 2026-07-03
**Type:** TECHNIQUE
**What I found:** The HANDOFF.md discipline is the dominant practitioner pattern for surviving context resets and tool switches in 2026 AI-assisted development. The file is not appended — it is *overwritten* at every session end so it always reflects current state. Three distinct types: same-tool next-day resume, cross-tool transfer (Cursor → Codex), and parallel worker dispatch. Key insight from Cursor community forums: the file must be self-contained enough that Codex can start from it with zero other context. The critical phrase that makes it work: "assume no memory of our conversation."
**Why it matters:** Andrew regularly switches between Cursor (interactive design) and Claude Code or Codex (autonomous execution). Without a handoff file, every new session either re-explains everything from scratch (slow) or runs with wrong assumptions (dangerous). The HANDOFF.md is also the bridge for parallel worktrees — each worker gets a scoped handoff covering only its slice.
**What it unlocks:** Any task that spans multiple sessions or tools becomes reliable. The cross-tool routing table (Cursor for design, Claude Code for autonomous execution, Codex for cloud parallel) gives Andrew a clear mental model for when to switch tools. The conflict-check prompt ("have key files changed since the handoff was written?") prevents stale handoffs from causing incorrect execution.
**Artifact:** `skills/agent-handoff.md`

---

### [ITERATION 12] TECHNIQUE — Spec-Driven Development with AI Agents
**Date:** 2026-06-18
**Type:** TECHNIQUE
**What I found:** Spec-driven development (SDD) — writing a SPEC.md file before any prompt — is now the dominant professional pattern for multi-file agent work in 2026. GitHub Spec Kit (open-source), AWS Kiro IDE, and Claude Code all ship native spec tooling. The core discipline: the spec is always updated to reflect decisions (not the chat), and the agent implements against SPEC.md, not against conversation history. The four-phase loop is: SPECIFY → PLAN → IMPLEMENT → VERIFY. Key anti-pattern caught: "updating rules in conversation" fails because the next session doesn't know about the conversation; all rules go in the spec file.
**Why it matters:** Andrew's agent sessions fail not because the model is bad but because business rules, edge cases, and success criteria live only in his head or in chat history that doesn't survive a context reset. A SPEC.md forces him to write those rules once, in a file, so every future session (and any collaborator) reads the same truth.
**What it unlocks:** Reliable multi-session tasks. Paste-ready VERIFY prompt that makes the agent check its own output against explicit success criteria. Finance-specific SPEC.md template for Excel/Power BI report work. "Out of scope" section pattern that prevents agents from helpfully adding unrequested features.
**Artifact:** `skills/agent-spec-driven.md`

---

### [ITERATION 11] TECHNIQUE — Agent Workflow Orchestration Patterns
**Date:** 2026-06-17
**Type:** TECHNIQUE
**What I found:** Three concrete orchestration patterns for multi-step agent workflows: (A) linear chain with checkpoint artifacts, (B) orchestrator + parallel workers via worktrees, (C) human-in-the-loop gate for destructive steps. Claude Code now natively supports up to 1,000 sub-agents with 16 concurrent execution paths and native checkpointing. The critical design insight is the HANDOFF.md + checkpoint file pattern — each step writes a self-contained artifact (status, decisions with rationale, outputs) so the next session can run with ONLY that file + the original brief, surviving context resets entirely.
**Why it matters:** Andrew regularly does multi-phase tasks spanning Excel + Power BI + code. Without explicit orchestration design, long sessions hit context limits mid-task, lose early decisions, and agents re-do work. The checkpoint pattern is the missing piece — it turns a fragile long session into a reliable chain of short, focused sessions.
**What it unlocks:** Any task that today requires Andrew to babysit a single long agent session can be refactored into a reliable 3-step chain. Especially: data→report→Power BI pipelines, multi-module refactors, Excel-clean→Power BI-load workflows.
**Artifact:** `skills/agent-workflow-orchestration.md`

---

### [ITERATION 10] TECHNIQUE — Agent Loop Debugging & Recovery
**Date:** 2026-06-16
**Type:** TECHNIQUE
**What I found:** Six named failure modes for agent sessions (tool misuse, context loss, goal drift, retry loop, cascading failure, sycophantic confirmation) with specific symptoms, diagnosis questions, and recovery prompts for each. The key insight is that each failure mode requires a different intervention — using a generic "try again" prompt on a goal-drift failure makes it worse.
**Why it matters:** Knowing how to recognise and name the specific failure type lets Andrew apply the right recovery in seconds rather than guessing. The pre-flight checklist prevents most failures before they start.
**What it unlocks:** Faster recovery from stuck agents. The structured output enforcement patterns are immediately useful for any task that needs a specific output format (tables, JSON, markdown reports).
**Artifact:** `skills/agent-loop-debugging.md`

---

### [ITERATION 9] TECHNIQUE — Context Engineering (Agent Window Management)
**Date:** 2026-06-15
**Type:** TECHNIQUE
**What I found:** Context engineering is a structured discipline for deciding what information enters an agent's context window, in what order, and how to compress and manage it over long sessions. The key finding: KV-cache structure (stable prefix → varying suffix) cuts time-to-first-token by up to 80% on Claude; MCP tool descriptions need 6 components (purpose, trigger, return type, param guidance, negative scope, example) or agents pick the wrong tool; the optimal context load order is system → conventions → task → history → files → prompt.
**Why it matters:** Most agent failures are context failures — agents don't have the right information, have too much noise, or have the right information in the wrong order. Context engineering is the layer above prompt engineering.
**What it unlocks:** Faster sessions via cache hits. Better tool selection via improved MCP descriptions. Reliable multi-session work via structured context resets.
**Artifact:** `skills/agent-context-engineering.md`

---

### [ITERATION 8] TECHNIQUE — Agent Self-Check Patterns
**Date:** 2026-06-19
**Type:** TECHNIQUE
**What I found:** Four escalating self-verification patterns: (1) inline critique before output, (2) output contracts (agent states success criteria before writing), (3) reflection pass (agent reviews its own output as a sceptic), (4) test-first loop (agent writes a test before the implementation). Key insight: "You're not done until X" is more reliable than "check your work" — it gives the agent a concrete stopping condition.
**Why it matters:** Agents default to confidence even when wrong. Self-check patterns shift the agent from "I think this is right" to "I can prove this is right."
**What it unlocks:** Reliable DAX measure verification, Power Query step validation, and any task where Andrew needs numbers he can stake his name on.
**Artifact:** `skills/agent-self-check.md`
