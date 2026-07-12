# Alfred Learning Log

---

## 2026-07-11 (Iteration #14) — Agent Memory Management Skill (CoALA Four-Layer System)

**Category:** Agent technique / memory architecture
**Mode:** New skill — `skills/agent-memory-management.md`

**Searches performed:**
1. `CoALA agent memory "working memory" "episodic memory" "semantic memory" "procedural memory" Claude Code CLAUDE.md practical implementation patterns`
   — Hit alexop.dev "The Four Types of Memory for AI Agents" (June 2026), fountaincity.tech, YouTube
   CoALA explainer (TechieTalksAI, June 2026), and the Anthropic "Code with Claude 2026" conference
   coverage noting that memory architecture was a primary theme of the May 2026 developer conference.
   The alexop.dev post was the primary source: confirmed that Claude Code maps each CoALA memory type
   to specific files on disk (CLAUDE.md = semantic, AGENTS.md = procedural, HANDOFF.md = episodic,
   context window = working).

2. `"agent memory" "stale facts" "memory pruning" "memory decay" practical patterns Cursor Claude 2026 prevent context poisoning`
   — Hit sitepoint.com AI Agent Memory Guide (2026) identifying the five most common production memory
   failures: context poisoning, session amnesia, stale semantic memory, procedural drift, episodic
   flooding. Also found Cursor forum thread (forum.cursor.com) with practitioners discussing HANDOFF.md
   as the only cross-tool solution that works because "it gets rewritten on every handoff, so it's
   always today, not what I thought on Tuesday." Also found the Graphiti + Cursor shared memory video
   (Atef Ataya, 684k subscribers, 228k views) confirming strong interest in persistent agent memory.

**Gap identified:**
The existing skill set covers each memory layer individually (AGENTS.md → `agents-md-project-context.md`,
HANDOFF.md → `agent-handoff.md`, context window → `agent-context-engineering.md`) but there is NO skill
that explains the four-layer architecture as a coherent system. Without the meta-layer view, developers
see three separate files and don't understand why they're separate, which leads to the most common
failure: mixing memory types (session decisions accumulating in CLAUDE.md, build commands in HANDOFF.md,
etc.). The stale-fact problem (semantic memory going out of date) is not covered anywhere.

**Key facts gathered:**
- CoALA (Princeton) = the canonical academic framework; now heavily referenced in applied 2026 sources
- Five production failure modes: context poisoning, session amnesia, stale semantic memory, procedural
  drift, episodic flooding — all traceable to conflated or neglected memory layers
- Claude Code's four files: context window (working), CLAUDE.md (semantic), AGENTS.md (procedural),
  HANDOFF.md + SCRATCH.md (episodic)
- Stale semantic memory is the silent killer: agent follows CLAUDE.md that says X while the codebase
  does Y, produces confidently wrong output, and neither the user nor the agent notices immediately
- HANDOFF.md discipline: must be overwrite-not-append; growing handoffs are the most common form of
  episodic flooding
- SCRATCH.md pattern: companion to HANDOFF.md for long-running projects (decisions log, abandoned
  paths, open questions) — not covered in any existing Alfred skill

**Change summary:**
- Created `skills/agent-memory-management.md` (290 lines)
  - Covers all four CoALA layers with disk-file mapping table
  - Layer 1 (Working): four load rules, 2 "Try asking:" prompts
  - Layer 2 (Semantic): what belongs, what doesn't, stale-fact update schedule, 3 "Try asking:"
  - Layer 3 (Procedural): minimal AGENTS.md template for a finance/data project
  - Layer 4 (Episodic): HANDOFF.md rules, SCRATCH.md pattern, 3 "Try asking:"
  - Monthly health check table (5 checks, each with a runnable command)
  - Anti-patterns table (6 failure modes with symptoms and fixes)
  - Quick-reference routing table ("which question → which file")
  - Five-file setup guide for starting from scratch today
- Updated `memory/discoveries.md` (Iteration #14 entry)
- Updated `memory/learning-log.md` (this entry)

**Files modified:** `skills/agent-memory-management.md` (new), `memory/discoveries.md` (updated),
`memory/learning-log.md` (this entry)

---

## 2026-07-10 (Iteration #13) — Agent Token Efficiency Skill Major Upgrade

**Category:** Agent technique / token efficiency / model effort
**Mode:** Improved existing skill — `skills/agent-token-efficiency.md`

**Searches performed:**
1. `"effort level" OR "thinking budget" Claude Code Cursor agent 2026 "low" "medium" "high" "max" when to use workflow tips`
   — Found two primary sources: mindstudio.ai "Claude Code Effort Levels" (May 2026) detailing the
   five levels (low/medium/high/max/ultra code) with token budgets per level and the counterintuitive
   rule that extra thinking budget is wasted on reconstructing context you should have provided.
   Also found explainx.ai and LinkedIn posts (Lukasz Bulik) confirming the effort levels are now
   a first-class Claude Code feature.
2. Also retrieved mager.co "Claude: How prompt caching actually works" (Apr 2026) — confirmed that
   cache breakpoints fire after ~5 mins of API inactivity; that the cache is prefix-anchored (any
   change in the stable prefix invalidates downstream); and practical rules for maximising cache
   hits within Cursor/Claude Code sessions.

**Gap identified:** The existing `agent-token-efficiency.md` was 120 lines covering 5 core rules,
an MCP table, and anti-patterns. It had NO coverage of:
- Effort levels (low/medium/high/max/ultra code) — the single biggest cost lever in 2026
- When to use vs. skip extended thinking
- Prompt caching mechanics and how to structure prompts to hit breakpoints
- Context compression checkpoints for long sessions
- Quick-reference table matching task type → effort → thinking flag

**Key facts gathered:**
- Five effort levels: low (~1k thinking tokens), medium (~8k, default), high (~32k), max (~64k),
  ultra code (uncapped, Opus 4+ only). Each is a cost-quality tradeoff.
- Counterintuitive rule (Lukasz Bulik, LinkedIn): the extra thinking budget gets spent reconstructing
  state you should have given upfront. Better context first; bump effort second.
- Prompt cache breakpoint: fires on prefix mismatch; cache expires ~5 mins of API inactivity or
  between Cursor sessions. Rules: never modify system prompt between turns; put stable content
  (SPEC, rules, pasted files) at top; don't re-paste files already in context.
- Extended thinking is valuable for first-principles decisions, debugging non-obvious bugs, and
  multi-step planning. Wasteful for retrieval tasks, queries where the answer is in the document,
  and for sub-agents inside a loop (thinking cost multiplies across calls).

**Change summary:**
- Rewrote `skills/agent-token-efficiency.md` from 120 lines → 220 lines
- Added Section 2 (effort levels) — full table, matching guide, 5 "Try asking:" examples
- Added Section 3 (extended thinking) — when to use, when to skip, 3 "Try asking:" examples
- Added Section 4 (prompt caching) — how it works, 5 structure rules, 3 "Try asking:" examples
- Added Section 6 anti-patterns table (upgraded from bullet list to table with fixes)
- Added Section 7 context compression checkpoints (3 paste-ready prompts)
- Added Section 8 quick-reference table (task type → effort → thinking)
- Preserved all original content, integrated it into new structure

**Files modified:** `skills/agent-token-efficiency.md` (improved), `memory/learning-log.md` (this entry),
`memory/discoveries.md` (appended).

---

## 2026-07-09 (Iteration #12) — Agent Output Evaluation / Builder-Validator Pattern Skill

**Category:** Agent technique / verification patterns
**Mode:** New skill — builder-validator / LLM-as-critic pattern

**Searches performed:**
1. `"builder validator" OR "CIV pattern" OR "coordinator implementer verifier" agentic SDLC agent roles 2026`
   — Found TestQuality/Anthropic 2026 Agentic SDLC Guide documenting the "verification gap" as the
   root cause of 75.3% of multi-agent failures (arXiv 2025). Found ASDLC.io patterns page listing
   the "Critic Agent" pattern (a secondary agent that reviews Builder Agent output against the original
   spec). Found sitepoint.com "LLM-as-Judge" patterns article (June 2026) confirming structured
   verification prompts outperform ad-hoc "does this look right?" by 2-3× on accuracy benchmarks.
2. `"goal alignment drift" long running agent Cursor "Claude Code" session verification checkpoint 2026`
   — Found Anthropic engineering blog noting that goal drift becomes measurable after 40+ tool calls
   in a single session. Found a Hacker News thread (mid-2026) where practitioners described using
   "alignment checkpoints" every 15-20 tool calls to prevent drift on multi-hour Cursor sessions.

**Change summary:**
- Created `skills/agent-output-evaluation.md` (new, ~200 lines)
- Added four verification patterns: fresh-window, spec-anchored, adversarial numeric, goal-alignment
- Documented the 75.3% failure rate finding and the verification gap root cause
- Included paste-ready prompts for each pattern

**Files modified:** `skills/agent-output-evaluation.md` (new), `memory/learning-log.md` (this entry)
