# Alfred Learning Log

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
  - Finance-specific SPEC.md template for Excel/Power BI report work (labour variance report example)
  - Anti-patterns table: 6 common failures with root cause and fix
  - Connection to existing skills (orchestration, context engineering, agents-md, data analysis)
  - 6 paste-ready "Try asking:" prompts covering: spec creation, plan phase, verify phase, mid-task rule change, Q&A spec interview, scope creep check

**Key insight from research:**
The VERIFY phase is the most consistently skipped step. Most people ask "does this look right?" instead of having the agent check against explicit success criteria. The discipline of writing testable criteria (row counts, totals match, no hardcoded values) and then having the agent VERIFY against them turns a fragile "looks about right" into a genuine pass/fail check.

**Why this matters:**
Andrew writes multi-phase reports (Excel + Power BI) where business rules are typically held in his head. When a session resets, those rules disappear and the agent starts making plausible-sounding guesses. A SPEC.md written before the task starts means every future session — and any collaborator — reads the same truth. The "Out of scope" section alone prevents the agent from helpfully adding unrequested features (a common problem on report tasks).

**How it connects to existing skills:**
- `agent-workflow-orchestration.md`: SPEC.md is the "brief" each phase of a chain reads; HANDOFF.md captures runtime state, SPEC.md captures design intent
- `agents-md-project-context.md`: CLAUDE.md sets agent defaults; SPEC.md is task-specific — don't mix them
- `agent-context-engineering.md`: SDD is context engineering applied at design-time
- `data-analysis-planning.md`: for exploratory data work, a lightweight spec (just "What questions" + "Expected output format") is enough

**Files modified:**
- `skills/agent-spec-driven.md` (new, 9.1k chars)
- `memory/learning-log.md` (this entry)
- `memory/discoveries.md` (appended entry)

---

## 2026-06-17 (Iteration #11) — Agent Workflow Orchestration Skill

**Category:** Agent skills / Workflow design
**Mode:** New skill — multi-step agent workflow orchestration patterns

**Searches performed:**
1. `prompt chaining agent workflow orchestration patterns 2025 practical "multi-turn" "handoff" cursor claude code`
   → Sources: Reddit r/ClaudeAI (multi-agent orchestration beyond one-shot), Medium (AI agentic workflow patterns 2026), Beam AI (6 multi-agent orchestration patterns for production 2026)
2. `"agent orchestration" "prompt chaining" vs "single agent" patterns decision framework 2025 LLM practical`
   → Sources: Reddit r/AI_Agents (separate agents vs single orchestrated flow), LaoZhang AI Blog (Claude Code agent teams practical guide 2026 — sub-agents, cost calculations, delegate mode, CLAUDE.md optimization), Medium AI Engineering Trend (Claude Code dynamic workflows — 1,000 sub-agents, 16 concurrent paths, native checkpointing)
3. `prompt chaining "checkpoint" "handoff state" agent workflow practical cursor claude code 2025 "sub-agent" "task decomposition"`
   → Sources: LaoZhang AI Blog confirmed Claude Code agent teams patterns; Medium AI Engineering Trend confirmed dynamic workflows launch details

**Change summary:**
- Created `skills/agent-workflow-orchestration.md` (~12.7k chars) — a complete, actionable skill covering when to orchestrate vs. single-session, three orchestration patterns (linear chain, orchestrator+workers, human-in-the-loop gate), checkpoint artifact design, handoff state management, sub-agent usage in Claude Code, a decision framework with 3 worked examples, pre-flight checklist, 6 paste-ready "Try asking:" prompts, and quick reference card.
- Key insight from research: Claude Code now supports up to 1,000 sub-agents with 16 concurrent paths and native checkpointing — the tooling has caught up to the patterns.
- The skill fills the gap between "how to plan" (agent-reasoning) and "how to run multiple coordinated sessions" — the orchestration layer that was missing from the skills library.
- Three patterns: (A) Linear chain — sequential steps with checkpoint files, (B) Orchestrator+workers — manifest-driven parallel delegation, (C) Human-in-the-loop gate — mandatory pause before destructive steps.
- HANDOFF.md pattern: persistent state file that every step in a chain reads/updates, preventing context loss between sessions.
- Checkpoint artifact format: self-contained (status, actions, decisions with rationale, artifacts, next-step input) — the critical design rule is that the next step must be runnable with ONLY the checkpoint + original brief.
- Decision framework covers 3 real workflows: data→report→Power BI, multi-module refactor, Excel clean→Power BI load.

**Why this matters:**
Andrew regularly does multi-phase tasks that touch Excel + Power BI + code. Without orchestration design, a single long session hits context limits, loses decisions made early, and the agent starts re-doing earlier work. This skill gives him a concrete pattern for structuring those tasks before he starts — especially the HANDOFF.md + checkpoint file pattern, which survives context resets.

**Files modified:**
- `skills/agent-workflow-orchestration.md` (new, ~12.7k chars)
- `memory/learning-log.md` (this entry)
- `memory/discoveries.md` (appended entry)

**Complementary skills:** `agent-parallel-worktrees.md`, `agent-context-engineering.md`, `agent-loop-debugging.md`, `agent-reasoning.md`

---

## 2026-06-16 (Iteration #10) — Agent Loop Debugging & Recovery Skill

**Category:** Agent skills / Debugging
**Mode:** New skill — diagnosing and recovering from stuck/broken Cursor and Claude Code agent sessions

**Searches performed:**
1. `agent loop stuck recovery patterns "tool call" "infinite loop" "max iterations" cursor claude code debugging checklist 2025`
   → Sources: Cursor community forum (infinite loop bug thread), Claude Code GitHub issues (#30014), n8n community (tool call lo
