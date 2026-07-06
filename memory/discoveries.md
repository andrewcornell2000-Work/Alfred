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

### [ITERATION 11] TECHNIQUE — MCP Security and Prompt Injection Defense
**Date:** 2026-07-09
**Type:** TECHNIQUE
**What I found:** MCP prompt injection is a documented, real attack class (Simon Willison, April 2025; Microsoft Developer Blog). Three attack vectors: (1) indirect injection — hidden instructions in files/pages the agent reads, (2) tool poisoning — malicious text in MCP server tool description fields, (3) "rug pull" — a package the operator vetted at v1.0 publishes v1.1 with a poisoned description, and `npx -y @latest` silently picks it up. The "lethal trifecta" (Willison) is the threat model: an attack needs private data access + untrusted content exposure + an outbound channel simultaneously. Removing any one leg breaks it.
**Why it matters:** Andrew's Alfred pack runs `filesystem` (Finance OneDrive), `ms-365` (mail + SharePoint), `fetch` (any URL), and `playwright` (any live page) simultaneously. The `fetch` + `filesystem` combination is the textbook trifecta entry point. The ms-365 MCP with `--read-only` removed would be the highest-risk configuration. There are no headline-grabbing incidents yet (Johann Rehberger's "normalization of deviance" concern) — but security researchers have demonstrated the attack chains work.
**What it unlocks:** A mental model Andrew can apply before every session: which MCPs are active? Does this task need all of them? Am I about to read external content while write tools are live? The pre-flight checklist and paste-ready detection prompts give him a practical workflow. Version pinning guidance prevents silent rug-pull updates.
**Artifact:** `skills/agent-mcp-security.md`

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
**What I found:** Three concrete orchestration patterns for multi-step agent workflows: (A) linear chain with checkpoint artifacts, (B) orchestrator + parallel workers via worktrees, (C) human-in-the-loop gate for destructive steps. Claude Code now natively supports up to 1,000 sub-agents with 16 concurrent execution paths and native checkpointing. The critical design insight is the HANDOFF.md + checkpoint file pattern — each step writes a self-contained artifact the next step reads. The orchestrator's only job is routing + error recovery, not content.
**Why it matters:** Andrew runs multi-step report pipelines: extract → transform → format → email. Without an explicit orchestration pattern, each handoff point either loses context or requires manual re-instruction. The three patterns give him a vocabulary for designing these pipelines and a recovery prompt when one step fails.
**What it unlocks:** Reliable multi-step automations. The "gate" pattern for destructive operations (confirm before overwriting a workbook) is immediately applicable to the finance workflow.
**Artifact:** `skills/agent-workflow-orchestration.md`
