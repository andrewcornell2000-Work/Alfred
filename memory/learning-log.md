# Alfred Learning Log

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
- Structured as 8 sections, each with a practical checklist or pattern Andrew can use directly in Cursor.
- Grounded in current research: LangChain's write/select/compress/isolate framework; Manus's KV-cache stability insight; arXiv 2025 six-component MCP tool description rubric.
- Alfred-specific patterns added: LeanCTX as context budget manager (15× cheaper than raw read), memory MCP priming at session start, SCRATCH.md pattern for long sessions.
- 6 actionable "Try asking:" prompts covering compression, memory priming, handoffs to Codex, and sequential-thinking as planner.
- Explicitly positioned relative to companion skills: `agent-reasoning.md` (decompose tasks), `agent-token-efficiency.md` (tactical tool choices). No content overlap.
- Updated `requirements/discovered-tools.md` with three new technique entries: context-engineering, KV-cache-aware prompting, MCP tool description quality audit.

**Why this matters:**
Context engineering is the highest-impact discipline for long Cursor sessions. Without it:
- Models forget earlier decisions as the window fills
- Irrelevant pasted files crowd out the actual problem context
- KV-cache misses make frontier model sessions slow and expensive
- Bad MCP tool descriptions cause the model to pick the wrong tool

The skill gives Andrew a concrete pre-task checklist and compress-point pattern he can follow in any complex Cursor session.

**Files modified:**
- `skills/agent-context-engineering.md` (new, ~10k chars)
- `requirements/discovered-tools.md` (appended 3 technique entries)
- `memory/learning-log.md` (this entry)

**Complementary skills:** `agent-reasoning.md`, `agent-token-efficiency.md`, `lean-ctx.md`

---

## 2026-06-08 (Iteration #13) — Routing & Safety-Gate Audit Skill

**Category:** Tools / Self-upgrade (routing + safety)
**Mode:** New skill — audit & improvement spec

**Change summary:**
- Created `skills/alfred-routing-keywords.md` — a full audit of how `backend/main.py` picks a tool for a request, what's brittle, and what to change.
- Documents the 6-stage routing pipeline: provider override → learning-mode → Alfred Brain (JSON classifier) → keyword fallback → safety gate → dispatch.
- Maps the six keyword sets that drive routing (`DANGEROUS_KEYWORDS`, `ACTION_KEYWORDS`, `LEARNING_MODE_KEYWORDS`, `CODEX_ROUTING_KEYWORDS`, `CLAUDE_CODE_ROUTING_KEYWORDS`, `SEARCH_TRIGGER_KEYWORDS`) plus `TOOL_REGISTRY[*].keywords`.
- Identifies 13 missing destructive verbs tha
- Identifies routing keyword problems: bare `document`, `report`, `open`, `code` over-trigger; Power Query is only correctly routed because of a hard short-circuit (made explicit); fallback sets have drifted from the Tool Registry.
- Provides a target **routing decision matrix** — for each request shape, the right category, provider, MCP, and whether the safety gate fires (pattern: read+draft = no gate; send/delete/overwrite/publish/refresh = gate).
- Concrete proposed diff to `backend/main.py` (documented only — Andrew approves before applying): expanded `DANGEROUS_KEYWORDS_V2`, tightened fallback sets, generation of
