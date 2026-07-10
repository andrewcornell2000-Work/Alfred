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

### [ITERATION 13] TECHNIQUE — Agent Token Efficiency: Effort Levels + Prompt Caching
**Date:** 2026-07-10
**Type:** TECHNIQUE / BUILD
**What I found:** Claude Code has five named effort levels (low / medium / high / max / ultra code) that directly control the token thinking budget per request — from ~1k tokens at "low" up to uncapped at "ultra code". The counterintuitive finding: extra thinking budget is typically *wasted* reconstructing context the user should have provided upfront, meaning better context nearly always beats higher effort. Additionally, prompt caching is now a first-class efficiency tool: the model caches the stable prefix of each session, and any change to that prefix (even one word) invalidates the cache and re-processes everything at full cost. Cache breakpoints expire after ~5 minutes of API inactivity or between Cursor sessions.
**Why it matters:** Andrew runs Cursor agents on multi-file finance tasks regularly. Without knowing effort levels, he either uses too much compute (default max, every run) or too little (quick answer on complex debugging). The effort level table gives him a concrete selection guide. The prompt caching rules stop the single most common silent waste: re-pasting files that are already in context.
**What it unlocks:** Structured effort selection for every Cursor/Claude Code task type. Practical cache-maximising habits (stable prefix first, no mid-session rephrasing, don't re-paste files). Context compression checkpoints for long-running sessions that would otherwise overflow. Quick-reference table at the end of the skill maps task type → effort → thinking flag.
**Artifact:** `skills/agent-token-efficiency.md` (major upgrade: 120 → 220 lines, 6 new sections)

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

### [ITERATION 10] TECHNIQUE — Agent Handoff / HANDOFF.md Discipline
**Date:** 2026-07-09
**Type:** TECHNIQUE
**What I found:** The most common source of agent session failure is not the agent itself but context loss between sessions — the next session re-discovers the same things, makes the same wrong assumptions, and repeats steps that were already done. The HANDOFF.md discipline solves this: a structured document written at the end of every session that captures goal, decisions made, files changed, current state, next step, and critical assumptions to avoid. It is the agent equivalent of a baton pass in a relay race — the baton has the context the next runner needs.
**Why it matters:** Andrew works across Cursor, Claude Code, and Codex — often switching between them mid-task. Without HANDOFF.md, each new tool starts from scratch. With it, any tool can orient itself in 10 seconds. The parallel-worktrees discipline from Iteration 3 is especially valuable with HANDOFF.md — each worktree gets its own handoff so sub-agents don't need to understand each other's work.
**What it unlocks:** Cross-session continuity, parallel agent coordination, and Codex autonomous run setup (Codex can read HANDOFF.md and follow it without human intervention).
**Artifact:** `skills/agent-handoff.md`
