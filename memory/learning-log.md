# Alfred Learning Log

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
   → Sources: Cursor community forum (infinite loop bug thread), Claude Code GitHub issues (#30014), n8n community (tool call loop), Galileo blog (retry loop token burn), Zylos AI (trace-driven debugging for agents)
2. `agent debugging techniques "agent loop" failure modes hallucination tool error retry backoff practical 2025`
   → Sources: buildmvpfast.com (error recovery patterns), latitude.so (6 failure modes framework), aispaces substack, mindstudio.ai (6 failure patterns)
3. `"tool misuse" "context loss" "goal drift" "retry loop" agent failure modes checklist diagnosis 2025 2026`
   → Sources: latitude.so (confirmed 6-mode taxonomy), mindstudio.ai (context degradation, specification drift, sycophantic confirmation, tool errors, cascading failure, silent failure), Partnership on AI PDF (real-time failure detection)

**Change summary:**
- Created `skills/agent-loop-debugging.md` — a complete, actionable skill covering all 6 agent failure modes with symptoms, diagnosis questions, recovery prompts, and prevention patterns.
- Structured as: failure mode taxonomy table → 5 diagnosis questions → per-mode recovery playbook → pre-flight checklist → universal recovery template → structured output enforcement → 6 "Try asking:" prompts → quick reference card.
- The six failure modes covered: tool misuse, context loss, goal drift, retry loop, cascading failure, sycophantic confirmation.
- Recovery prompts are paste-ready — Andrew can copy them into Cursor chat when an agent gets stuck.
- Pre-flight checklist is a 7-item list to run before any task > 10 tool calls.
- Structured output section covers: markdown tables, code-only fences, JSON action arrays, DAX-only, and Claude Code SDK jsonSchema pattern.
- Positioned explicitly relative to companion skills: `agent-reasoning.md`, `agent-context-engineering.md`, `agent-token-efficiency.md`.
- Appended `agent-loop-debugging` entry to `requirements/discovered-tools.md`.

**Why this matters:**
This is the missing complement to context engineering and reasoning patterns. Knowing how to plan and manage context helps avoid failures — but when things go wrong mid-session (which they will), there's been no skill covering how to recognise the specific failure mode and apply the right recovery. The quick-reference card at the bottom lets Andrew diagnose in seconds without re-reading the whole skill.

**Files modified:**
- `skills/agent-loop-debugging.md` (new, ~9.5k chars)
- `requirements/discovered-tools.md` (appended 1 technique entry)
- `memory/learning-log.md` (this entry)

**Complementary skills:** `agent-reasoning.md`, `agent-context-engineering.md`, `agent-token-efficiency.md`

---

## 2026-06-15 (Iteration #10) — Context Engineering Skill

**Category:** Agent skills / Context architecture
**Mode:** New skill — context engineering for Cursor + Claude + Codex sessions

**Searches performed:**
1. `context engineering window management tool call planning agent loop 2025 practical techniques`
   → Sources: Haystack blog (deepset), LangChain blog, Manus blog (Peak Ji), Letta blog
2. `"context engineering" agent practical checklist KV cache tool description quality MCP 2025`
   → Sources: arXiv 2602.14878 (MCP tool description smells), Marina Wyss Medium course, Cursor Directory plugin, Manus Reddit thread

**Change summary:**
- Created `skills/agent-context-engineering.md` — a complete, actionable skill covering context window anatomy, write/select/compress/isolate patterns, KV-cache awareness, MCP tool description quality, and an Alfred-specific checklist.
- Structured as 8 sections, each with a practical checklist or action.
- Appended `context-engineering` technique entry to `requirements/discovered-tools.md`.

**Why this matters:**
Context engineering is the most direct lever for making Cursor and Claude Code sessions more reliable and cheaper. Without this knowledge, Andrew will hit context limit failures, redundant re-reads, and stale instructions at the worst moments.

**Files modified:**
- `skills/agent-context-engineering.md` (new)
- `requirements/discovered-tools.md` (appended 1 technique entry)
- `memory/learning-log.md` (this entry)
