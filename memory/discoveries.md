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
**What it unlocks:** Faster recovery from stuck sessions. Paste-ready prompts that Andrew can use immediately when Cursor or Claude Code gets into a loop.
**Artifact:** `skills/agent-loop-debugging.md`

---

### [ITERATION 10] TECHNIQUE — Context Engineering for Agent Sessions
**Date:** 2026-06-15
**Type:** TECHNIQUE
**What I found:** Context engineering — deliberately controlling what goes into the agent's context window — is more impactful than prompt wording. Key patterns: write-to-file instead of chat (persists across sessions), selective reading (map mode before full read), compression (ask agent to summarise long artifacts before using them), isolation (fresh session per distinct sub-task), KV-cache awareness (stable prefix = cheaper, faster), and MCP tool description quality (bad descriptions cause tool misuse before the task starts).
**Why it matters:** Context engineering is the single highest-leverage skill for making Cursor/Claude sessions reliable and cheaper. Without it, sessions fail at context limit or hallucinate because stale instructions are still in-window.
**What it unlocks:** Longer, more reliable agent sessions. Cheaper runs (KV cache reuse). Better MCP tool selection (fewer wrong-tool errors).
**Artifact:** `skills/agent-context-engineering.md`
