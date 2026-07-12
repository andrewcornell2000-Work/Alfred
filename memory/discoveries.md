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

### [ITERATION 12] TECHNIQUE — Builder-Validator Pattern (Agent Output Evaluation)
**Date:** 2026-07-09
**Type:** TECHNIQUE
**What I found:** The "verification gap" is identified in arXiv 2025 research as the root cause of 75.3% of multi-agent task failures — the builder implements its own interpretation and then verifies against that same interpretation, not against what was originally asked. The fix is the builder-validator pattern: a second, fresh agent receives only the original requirement and the output (never the builder's chain-of-thought), then evaluates it independently. This is structurally equivalent to unit testing but applied to AI-generated outputs. ASDLC.io documents this as the "Critic Agent" pattern; Anthropic's 2026 agentic SDLC guide identifies it as a mandatory gate before any output reaches a stakeholder.
**Why it matters:** Andrew regularly uses Cursor for building then asks "does this look right?" — this is precisely the pattern that fails. The builder finished, rationalised its own output, and now confirms it's correct. The critic pattern gives a concrete, independent check. For finance outputs (numbers, formulas), the adversarial numeric audit pattern (Pattern 3) adds trace-back verification — the critic traces each key number back to its source rather than just reading the output.
**What it unlocks:** Any agent-produced output that goes to a stakeholder or depends on correctness can now have a structured, paste-ready verification pass. The pattern also catches goal-alignment drift in long runs (40+ tool calls), which is otherwise invisible — the agent looks busy and productive but drifts off the original goal over time. Four patterns cover all scenarios: fresh-window (general), spec-anchored (when SPEC.md exists), adversarial (finance/data), goal-alignment (long runs).
**Artifact:** `skills/agent-output-evaluation.md` (new skill), `memory/learning-log.md` (updated)

---

### [ITERATION 11] BUILD — Outlook Calendar MCP shipped to pack
**Date:** 2026-07-08
**Type:** BUILD
**What I found:** `outlook-calendar-mcp` (npm) — an MCP server that drives the local Outlook COM automation layer on Windows to read/manage calendar events, create meetings, find free slots, and check attendee status. No API key or admin rights needed. Windows 11 24H2+ requires enabling VBScript via Settings → Apps → Optional features first. Works entirely with the local Outlook desktop client.
**Why it matters:** Andrew works on Windows with Outlook. Previously there was no way for Cursor or Claude Code to see or manage his calendar without leaving the editor. Now he can ask "find me a free hour this week" or "create a meeting with the finance team on Thursday at 2pm" directly in Cursor.
**What it unlocks:** Calendar-aware agent workflows: finding free time, blocking time for finance reviews, listing upcoming meetings to plan Cursor tasks around. Pairs with ms-365 MCP for full 365 coverage.
**Artifact:** `cursor/mcp.json` (outlook-calendar-mcp entry added), `memory/learning-log.md`

---

### [ITERATION 10] BUILD — ms-365 MCP shipped (Graph API: SharePoint, OneDrive, Outlook, Calendar, Teams)
**Date:** 2026-07-04
**Type:** BUILD / BREAKTHROUGH
**What I found:** `@softeria/ms-365-mcp-server` — a community MCP that connects Cursor and Claude Code to the Microsoft Graph API, giving read (and optionally write) access to SharePoint sites, OneDrive files, Outlook mail, Calendar, Teams, and To-Do. Authentication via MSAL device-code (browser pop-up, one-time). Default `--read-only` flag makes it safe for discovery tasks.
**Why it matters:** SharePoint and OneDrive access was the most-requested discovery target. Previously the only path was downloading files manually and opening them in Excel or markitdown. Now you can search a SharePoint document library from inside Cursor, read a Word doc, or find emails from a client — all without leaving the editor.
**What it unlocks:** "Find all Excel files in the Finance SharePoint library modified this month" — runs in Cursor in 10 seconds. Email search, calendar lookup, OneDrive file read. Pairs with markitdown for PDF/Office conversion of files found via ms-365.
**Artifact:** `cursor/mcp.json` (ms-365 entry), `skills/sharepoint-graph.md` (updated), `discovered-tools.md` (ms-365 entry)

---

### [ITERATION 9] TECHNIQUE — Agent Spec-Driven Development
**Date:** 2026-07-03
**Type:** TECHNIQUE
**What I found:** The SPEC.md-first pattern — writing a precise specification before touching any code — dramatically reduces the "drift and re-derive" failure mode in Cursor agents. The spec anchors every downstream decision and serves as the validator input for the builder-validator pattern.
**Why it matters:** Without a written spec, agents interpret requirements loosely and confirm their own interpretations. A two-page SPEC.md written before any code is the single highest-leverage intervention for long Cursor sessions.
**What it unlocks:** Clear task decomposition, parallel worktree assignments, builder-validator verification anchors. The SPEC.md pattern is now the recommended starting point for any Cursor task > 30 minutes.
**Artifact:** `skills/agent-spec-driven.md` (new skill)

---

### [ITERATION 8] BUILD — agent-workflow-orchestration skill shipped
**Date:** 2026-07-03
**Type:** BUILD
**What I found:** The "coordinator-worker" pattern is the dominant multi-agent orchestration model in 2026. One agent decomposes the task and assigns subtasks; worker agents execute with strict output schemas. The coordinator never executes; workers never re-plan.
**Why it matters:** Andrew's finance pipeline tasks (data pull → transform → reconcile → report) are naturally coordinator-worker shaped. Mapping them explicitly prevents agents from scope-creeping into each other's work.
**Artifact:** `skills/agent-workflow-orchestration.md` (new skill)

---

### [ITERATION 7] TECHNIQUE — MCP tool-description quality audit rubric
**Date:** 2026-06-15
**Type:** INSIGHT
**What I found:** arXiv 2025 research on tool selection failure in MCP-equipped agents identified six required components in a good tool description: purpose, trigger condition, return type, parameter guidance, negative scope, and example. Missing any one causes wrong tool selection at rates measured in the research at 15-40%.
**Why it matters:** mcp.json is the source of truth for tool descriptions. Auditing against this rubric is a low-cost, high-leverage action before any complex multi-MCP agent run.
**Artifact:** `skills/agent-context-engineering.md` (Section 6 — tool description audit rubric)

---

### [ITERATION 6] BUILD — DuckDB MCP shipped to pack
**Date:** 2026-06-12
**Type:** BUILD
**What I found:** `mcp-server-duckdb` (uvx) — SQL analytics on CSV, Parquet, and Excel exports without opening Excel. Zero admin install via uvx. Replaces the retired sqlite MCP with a much more capable engine (columnar, handles files > 1M rows, native Parquet support).
**Why it matters:** Most of Andrew's finance data lives in CSV or Excel exports. DuckDB MCP lets Cursor run SQL directly on those files — aggregations, joins, time-series queries — without any ETL step.
**Artifact:** `cursor/mcp.json` (duckdb entry), `skills/data-analysis-planning.md` (routing note added)
