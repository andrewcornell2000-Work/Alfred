# Alfred Learning Log

---

## 2026-07-03 (Iteration #10) — Agent Handoff Skill

**Category:** Agent skills / Workflow design
**Mode:** New skill — agent handoff pattern (HANDOFF.md discipline)

**Searches performed:**
1. `HANDOFF.md template agent context transfer Cursor Claude Code Codex best practices 2025 2026`
   — Found Cursor community forum thread confirming HANDOFF.md as the dominant practitioner pattern
   for cross-tool context continuity. Key practitioner insight: it is rewritten (not appended) at every
   session end so it always reflects present state, never accumulates stale history. Also found Firecrawl
   blog confirming a 'handoff' skill is among top-value Codex skills for 2026.
2. Fetched Cursor community forum page 2 of the thread — obtained real practitioner detail: the file
   must be plain text (all tools understand it), must be overwritten not appended, and must solve two
   problems simultaneously: recency (it's always "today") and portability (Cursor, Claude Code, and
   Codex can all consume it).

**Gap identified:** No existing skill covers the HANDOFF.md pattern specifically. The closest skill
(`agent-workflow-orchestration.md`) covers checkpoint artifacts within a task chain but does not cover
the session-end → session-start transfer pattern, cross-tool routing guidance (Cursor for design, Codex
for autonomous execution), or paste-ready prompts for generating and consuming a HANDOFF.md.

**Change summary:**
- Created `skills/agent-handoff.md` (9.2k chars) — a complete, actionable skill covering:
  - Three handoff types: same-tool next-day, cross-tool transfer, parallel worker dispatch
  - Full HANDOFF.md template with every section explained (What we're building / Done / Decisions locked /
    Next steps / Do NOT do / Key files / Open questions / Starting prompt)
  - Three paste-ready prompts for generating handoffs (quick, cross-tool Codex, parallel worker)
  - Three prompts for consuming a handoff (resume, Codex autonomous, conflict check)
  - Tool routing table: Cursor for design, Claude Code for autonomous execution, Codex for cloud parallel
  - Common mistakes table with fixes (7 anti-patterns)
  - Five "Try asking:" examples Andrew can paste directly into Cursor

**Files modified:** `skills/agent-handoff.md` (new), `requirements/discovered-tools.md` (appended),
`memory/learning-log.md` (this entry), `memory/discoveries.md` (appended).

---

## 2026-06-23 — ECC cherry-pick: 4 MCPs + continuous-learning instinct engine

**Category:** Harness upgrade / MCPs + continuous learning
**Mode:** Read-only review of `affaan-m/ECC`, ported only what beat current Alfred

**Source:** Cloned ECC read-only to `C:\Users\Andre\_ecc-review` (220k-star agent
harness). Reviewed its 28-MCP catalog, ~250 skills, 67 subagents, hook system,
and the continuous-learning-v2 "instinct" engine. Skipped 80% (language/crypto/
healthcare/enterprise boilerplate + the commercial layer); took the high-value bits.

**Change summary:**
- **MCPs** added to `cursor/mcp.json` (provisioner auto-skips if key/command missing):
  - `fal-ai` — image/video/audio generation (needs `FAL_KEY`)
  - `magic` — Magic UI components (no key)
  - `parallel-search` — citation-backed web search/fetch via `mcp-remote` (key-free)
  - `longhand` — lossless Claude Code session history → SQLite+ChromaDB (`pip install longhand`)
  - Note: parallel-search is HTTP-only upstream; Alfred's provisioner is command-based,
    so it's wired through the `mcp-remote` stdio bridge.
- **Instinct engine** — `scripts/instinct-cli.py` (lean, stdlib-only reimplementation of
  ECC's 1,914-line continuous-learning-v2; stores confidence-scored `when X → do Y`
  lessons in `memory/instincts/`, project + global scope, decay + TTL prune).
- **Hooks** wired in `.claude/settings.json` (Python, no node dep):
  - `SessionStart` → `session-start-instincts.py` surfaces active/strong instincts into context
  - `PreToolUse(Edit|Write|MultiEdit)` → `config-protection.py` blocks weakening linter configs
  - `PreToolUse(Bash)` → `pre-commit-quality.py` secret/debugger/console scan before commit
  - `Stop` → `observe-session.py` (opt-in `ALFRED_INSTINCT_OBSERVE=1`) cheap observation log
- Seeded 3 curated global instincts; added `/instinct-status` + `/instinct-learn` commands,
  `skills/continuous-learning.md`, and wired the loop prompt (STEP 0 surface/decay/prune,
  STEP 4 record lessons).
- Smoke-tested: JSON valid, CLI add/dedupe/reinforce/status, all three hooks (block + allow paths).

**Files modified:** `cursor/mcp.json`, `.claude/settings.json`, `.gitignore`,
`ALFRED_LOOP_PROMPT.md`, `README.md`, `scripts/instinct-cli.py`,
`scripts/hooks/{session-start-instincts,config-protection,pre-commit-quality,observe-session}.py`,
`skills/continuous-learning.md`, `.claude/commands/{instinct-status,instinct-learn}.md`,
`memory/instincts/{README.md,global.json}`.

---

## 2026-06-18 (Iteration #12) — Spec-Driven Development Skill

**Category:** Agent skills / Workflow design
**Mode:** New skill — spec-driven development with AI agents

**Searches performed:**
1. Fetched `addyosmani.com/blog/good-spec` — Addy Osmani (Google) guide on writing effective specifications for AI coding agents; covers spec structure, what to include, and the discipline of not letting chat replace the spec.
2. Fetched `productbuilder.net/learn/spec-driven-development` — 2026 survey of spec-driven development patterns across Claude Code, GitHub Spec Kit, and Kiro; confirmed SDD is the dominant professional pattern for multi-file agent work.
3. Fetched `augmentcode.com/guides/automating-spec-driven-development-with-ai-agents` — Augment Code practical guide; confirmed four-phase loop (SPECIFY→PLAN→IMPLEMENT→VERIFY), the "out of scope" section pattern, and VERIFY-against-criteria as the missing step most people skip.

**Change summary:**
- Created `skills/agent-spec-driven.md` (9.1k chars) — a complete, actionable skill covering:
  - The core insight: agents fail not because the model is bad but because business rules live in chat history, not files
  - "When to use spec-driven" decision checklist (6 criteria; use if 2+ are true)
  - Four-phase workflow: SPECIFY → PLAN → IMPLEMENT → VERIFY, with paste-ready prompts for phases 2–4
  - Full SPEC.md template (What this builds / Inputs / Expected output / Business rules / Edge cases / Success criteria / Out of scope)
  - Finance/Power BI example SPEC.md filled in with real content (not placeholder lorem ipsum)
  - 6 "Try asking:" examples Andrew can paste directly into Cursor
  - Companion skill links to `agent-context-engineering.md`, `agent-self-check.md`
