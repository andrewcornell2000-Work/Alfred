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

### [ITERATION 15] TECHNIQUE — Agent Structured Output: Schema Enforcement for Reliable Pipelines
**Date:** 2026-07-12
**Type:** TECHNIQUE / BUILD
**What I found:** "JSON please" is advisory — Claude generates text that looks like JSON but frequently drifts in field names, types, and structure across runs. The actual mechanism for reliable structured output is a 4-level escalation: format hints (~70% reliable, zero overhead) → output contracts (state fields+types before starting, self-check before responding, ~85%) → JSON Schema declaration with `additionalProperties: false` and `enum` for categories (~97%) → tool-call enforcement (describe output as a synthetic tool call so Claude uses its typed-argument pathway rather than text-generation, 99%+). Confirmed from Anthropic's 2026 structured outputs docs, collinwilkins.com pipeline patterns, and kenhuangus.substack.com structured output chapter. Claude API's native structured output feature wraps JSON Schema as a synthetic tool definition at the inference level — the same trick can be exploited in Cursor prompts by describing the output as "call this tool with these typed arguments."
**Why it matters:** Andrew extracts cost tables from PDFs, feeds agent outputs into Power BI models and DuckDB queries, and runs the same analysis prompts week-to-week. Without schema enforcement, field names drift ("FTE Count" vs "headcount" vs "fte_count") and break every formula that references them. Parsing failures are silent — the pipeline breaks hours after the agent ran, not immediately. A saved SCHEMA_*.json file is the single cheapest fix for week-to-week drift on recurring extractions.
**What it unlocks:** Four ready-to-paste prompt patterns (one per enforcement level), three finance-specific recipes (PDF extraction → DuckDB, weekly variance schema file, markdown table for Excel paste), a validation/retry pattern with targeted error correction prompts, a multi-agent output contract pattern (Agent 1 writes HANDOFF_data.json to a declared schema; Agent 2 reads it), and a pre-run checklist.
**Artifact:** `skills/agent-structured-output.md` (new, 12,613 chars, 5 "Try asking:" prompts, 3 recipes, 1 checklist, 4 enforcement levels, validation loop)

---

### [ITERATION 14] TECHNIQUE — Four-Layer Agent Memory System (CoALA Framework)
**Date:** 2026-07-11
**Type:** TECHNIQUE / BUILD
**What I found:** The CoALA framework (Princeton, 2023; heavily applied in 2026) identifies four distinct memory types that capable agents need: Working (context window), Semantic (facts/conventions in CLAUDE.md), Procedural (build/run commands in AGENTS.md), and Episodic (session decisions in HANDOFF.md). Most developers give agents only working memory and wonder why they forget everything. The five most common memory failures in 2026 production deployments (sitepoint.com): context poisoning, session amnesia, stale semantic memory, procedural drift, and episodic flooding. All five are caused by conflating memory types or neglecting layers. Claude Code maps each type to specific files on disk — the system is already there; it just has to be wired deliberately.
**Why it matters:** Andrew runs multi-session Cursor and Claude Code tasks on finance data. Without episodic memory (HANDOFF.md), every session starts with "where were we?" Without semantic memory (CLAUDE.md), agents confidently apply stale naming conventions after schema changes. Without procedural memory (AGENTS.md), agents guess build flags. The framework gives a concrete file-per-layer setup that prevents all five failure modes.
**What it unlocks:** A structured memory architecture with a monthly health check, an anti-patterns table, a SCRATCH.md working notes pattern for long-running projects, and a decision-routing table ("which question → which file"). The skill also addresses the stale-fact problem with an explicit update schedule per layer, which is the most commonly missed discipline.
**Artifact:** `skills/agent-memory-management.md` (new, 290 lines, 5 "Try asking:" prompts across 4 sections)

---

### [ITERATION 13] TECHNIQUE — Agent Token Efficiency: Effort Levels + Prompt Caching
**Date:** 2026-07-10
**Type:** TECHNIQUE / BUILD
**What I found:** Claude Code has five named effort levels (low / medium / high / max / ultra code) that directly control the token thinking budget per request — from ~1k tokens at "low" up to uncapped at "ultra code". The counterintuitive finding: extra thinking budget is typically *wasted* reconstructing context the user should have provided upfront, meaning better context nearly always beats higher effort. Additionally, prompt caching is now a first-class efficiency tool: the model caches the stable prefix of each session, and any change to that prefix (even one word) invalidates the cache and re-processes everything at full cost. Cache breakpoints expire after ~5 minutes of API inactivity or between Cursor sessions.
**Why it matters:** Andrew runs Cursor agents on multi-file finance tasks regularly. Without knowing effort levels, he either uses too much compute (default max, every run) or too little (quick answer on complex debugging). The effort level table gives him a concrete selection guide. The prompt caching rules stop the single most common silent waste: re-pasting files that are already in context.
**What it unlocks:** Structured effort selection for every Cursor/Claude Code task type. Practical cache-maximising habits (stable prefix first, no mid-session rephrasing, don't re-paste files). Context compression checkpoints for long-running sessions that would otherwise overflow. Quick-reference table at the end of the skill maps task type → effort → thinking flag.
**Artifact:** `skills/agent-token-efficiency.md` (major upgrade: 120 → 220 lines, 6 new sections)

---

### [ITERATION 12] TECHNIQUE — Agent Claude Code Sub-agents (Claude Code native multi-agent)
**Date:** 2026-07-09
**Type:** TECHNIQUE / BUILD
**What I found:** Claude Code now ships native sub-agent spawning via the Task tool — no external orchestration framework required. Unlike Cursor parallel agents (which require git worktrees and manual wiring), Claude Code's Task tool lets a parent agent decompose a problem and dispatch independent sub-agents directly from within the same session. Key 2026 patterns: fan-out (one parent, many parallel sub-agents), pipeline (output of sub-agent A → input of sub-agent B), and specialist routing (sub-agents scoped to a single tool or domain). Sub-agents have isolated context windows by default but can share a scratch file for passing data between steps.
**Why it matters:** For Andrew's finance/data work, this means a single Cursor or Claude Code session can simultaneously fetch SharePoint files, run DuckDB analysis, draft the Word report, and check the result — without manual session-switching or copy-pasting intermediate outputs.
**What it unlocks:** Fan-out research pattern, pipeline pattern with HANDOFF, specialist routing (read-only sub-agent, compute sub-agent, write sub-agent), anti-patterns (spawning with shared mutable state, unbounded fans).
**Artifact:** `skills/agent-claude-code-subagents.md` (new, 180 lines)

---

### [ITERATION 11] BUILD — Agent Output Evaluation: Builder-Validator Pattern
**Date:** 2026-07-08  
**Type:** TECHNIQUE / BUILD
**What I found:** 75.3% of multi-agent failures trace to semantic breakdown between what was built and what was asked (arXiv 2025). The fix: a fresh-context critic that evaluates output against the original spec — not the builder's reasoning. Four escalating patterns: fresh-window critic (new chat, paste requirement + output), spec-anchored critic (mechanical SPEC.md checklist), cross-model validation (different provider = different blind spots), and automated regression (save evaluations as test cases). Key insight: the builder's context is the contamination — even asking the same model to review its own output in the same session produces sycophantic confirmation, not genuine critique.
**Why it matters:** Andrew's agent sessions produce Power BI models, cost reports, and data transforms that others depend on. A silent error in a labour cost formula or a wrong filter in a variance report propagates downstream. The critic pattern catches these before they leave the agent.
**What it unlocks:** Four copy-paste critic prompts, a confidence-vs-correctness calibration method, a regression test discipline (save one critic evaluation per task as a future test case), and a "when to skip" guide so it's not overhead on small tasks.
**Artifact:** `skills/agent-output-evaluation.md` (new, 200 lines)

---

### [ITERATION 10] TECHNIQUE — Agent MCP Security Patterns (prompt injection, tool poisoning, privilege)
**Date:** 2026-07-07
**Type:** TECHNIQUE / INSIGHT
**What I found:** arXiv 2025 survey (Yang et al.) documents three attack surfaces that Claude/Cursor users face in practice: prompt injection via MCP tool outputs (malicious instructions embedded in web pages, PDFs, or files the agent reads), tool description poisoning (a malicious MCP server lying about what its tools do), and privilege escalation (agent granted write permissions it shouldn't have for a read task). None of these require the user to do anything wrong — they exploit the fact that agents trust their context. The minimal-privilege rule is the highest-ROI mitigation: most agent tasks need read access, not write, and scoping permissions at task start prevents the worst outcomes.
**Why it matters:** Andrew uses Playwright, filesystem MCP, and ms-365 to read finance files and web pages — exactly the surfaces where injection happens. A PDF from a vendor or a web page fetched during research could contain embedded instructions that redirect a running agent.
**What it unlocks:** Three mitigation disciplines (trust tiers, minimal-privilege prompts, output validation before action), a safe-agent prompt template, and a pre-flight security checklist for high-risk tasks (anything write, anything external, anything financial).
**Artifact:** `skills/agent-mcp-security.md` (new, 150 lines)
