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

### [ITERATION 12] TECHNIQUE — Builder-Validator Pattern (Agent Output Evaluation)
**Date:** 2026-07-09
**Type:** TECHNIQUE
**What I found:** The "verification gap" is identified in arXiv 2025 research as the root cause of 75.3% of multi-agent task failures — the builder implements its own interpretation and then verifies against that same interpretation, not against what was originally asked. The fix is the builder-validator pattern: a second, fresh agent receives only the original requirement and the output (never the builder's chain-of-thought), then evaluates it independently. This is structurally equivalent to unit testing but applied to AI-generated outputs. ASDLC.io documents this as the "Critic Agent" pattern; Anthropic's 2026 agentic SDLC guide identifies it as a mandatory gate before any output reaches a stakeholder.
**Why it matters:** Andrew regularly uses Cursor for building then asks "does this look right?" — this is precisely the pattern that fails. The builder finished, rationalised its own output, and now confirms it's correct. The critic pattern gives a concrete, independent check. For finance outputs (numbers, formulas), the adversarial numeric audit pattern (Pattern 3) adds trace-back verification — the critic traces each key number back to its source rather than just reading the output.
**What it unlocks:** Any agent-produced output that goes to a stakeholder or depends on correctness can now have a structured, paste-ready verification pass. The pattern also catches goal-alignment drift in long runs (40+ tool calls), which is otherwise invisible — the agent looks busy and productive but drifts off the original goal over time. Four patterns cover all scenarios: fresh-window (general), spec-anchored (when SPEC.md exists), adversarial (finance/data), goal-alignment (long runs).
**Artifact:** `skills/agent-output-evaluation.md`

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
**What I found:** Spec-driven development (SDD) — writing a SPEC.md file before any prompt — is now the dominant professional pattern for multi-file agent work in 2026. GitHub Spec Kit (open-source), AWS Kiro IDE, and Claude Code all ship native spec tooling. The core discipline: spec captures business rules and success criteria before any build; the agent implements against the spec; when something changes, you update the spec (not the conversation). The four-phase workflow (SPECIFY → PLAN → IMPLEMENT → VERIFY) maps directly onto how Kiro, Cursor, and Claude Code split their UI.
**Why it matters:** Andrew's common failure mode: one-line prompt that the agent fills with its own assumptions. Two days later the output is wrong but nobody can articulate why. SPEC.md makes every assumption visible and checkable.
**What it unlocks:** SPEC.md as single source of truth survives context resets, tool switches, and team handoffs. The agent PLAN phase (no code, just plan) catches misunderstandings before they're built. The VERIFY phase closes the loop against the original success criteria — no more "it looked done but wasn't."
**Artifact:** `skills/agent-spec-driven.md`
