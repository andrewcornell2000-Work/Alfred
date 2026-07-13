# Alfred Learning Log

---

## 2026-07-12 (Iteration #15) — Agent Structured Output Skill

**Category:** Agent technique / pipeline reliability
**Mode:** New skill — `skills/agent-structured-output.md`

**Searches performed:**
1. Reviewed existing skills index and `agent-output-evaluation.md` in full — confirmed the
   existing skill covers *quality* (critic/validator pattern) but has no content on *data shape
   enforcement* (schema, field types, format contracts). The gap is real and not covered anywhere
   in the pack.

2. Cross-referenced Anthropic structured outputs documentation (2026): confirmed that Claude's
   native structured output feature wraps JSON Schema as a synthetic tool definition at the
   inference level, giving 99%+ schema conformity vs. ~70% from a plain "return JSON" instruction.
   Sources cross-checked: collinwilkins.com "LLM Structured Outputs: Schema Validation for Real
   Pipelines" (2026), kenhuangus.substack.com Chapter 15 (2026), Reddit r/ClaudeAI structured
   outputs launch thread, Peace of Code "Claude Certified Architect Ep 16: Structured Output &
   JSON Schema" (May 2026).

**Gap identified:**
- `agent-self-check.md` = logical correctness (agent verifies its reasoning)
- `agent-output-evaluation.md` = quality via critic (fresh agent reviews the output)
- `agent-structured-output.md` (NEW) = data shape enforcement (schema contracts, type safety,
  pipeline reliability)

These are three genuinely distinct failure modes. Structured output is the one missing from
the pack and the most relevant to Andrew's PDF extraction → DuckDB → Power BI workflows.

**Key facts gathered:**
- "JSON please" is advisory text generation: Claude produces something that looks like JSON but
  field names, types, and structure drift across runs. Reliability: ~70%.
- The fix is a 4-level escalation: format hint → output contract → JSON Schema declaration →
  tool-call enforcement. Each level has a concrete reliability estimate and paste-ready prompt.
- `additionalProperties: false` in JSON Schema is the single highest-value addition: prevents
  the model inventing "notes" or "confidence" fields to explain uncertainty.
- `enum` for category strings stops "Labour" vs "labour" vs "Labour costs" divergence that
  breaks Power BI measures and DuckDB GROUP BY queries.
- The tool-call enforcement trick: describing the output as "call this tool with these typed
  arguments" routes Claude through its tool-use inference pathway (trained on typed argument
  filling) rather than text-generation, producing dramatically more consistent structure.
- Schema drift is the silent killer for recurring tasks — the same prompt produces "FTE Count"
  one week and "headcount" the next. Saving a SCHEMA_*.json file and referencing it by filename
  is the cheapest fix with the highest recurring payoff.
- Multi-agent output contracts: Agent 1 writes HANDOFF_data.json to a declared schema; Agent 2
  reads it. Without this, agents invent field names independently and break each other silently.

**Change summary:**
- Created `skills/agent-structured-output.md` (12,613 chars)
  - Four enforcement levels with reliability estimates and paste-ready prompts
  - JSON Schema design rules (6 rules from 2026 production experience)
  - Validation + retry pattern with targeted error correction prompts
  - Failure mode table (5 common failures, causes, prevention)
  - Three finance recipes: PDF extraction → DuckDB, weekly variance schema file,
    markdown table for Excel paste
  - Multi-agent output contract pattern (HANDOFF_data.json with declared schema)
  - Pre-run checklist (5 checks)
  - Five "Try asking:" prompts (PDF extraction, reusable schema creation, retry on
    failed validation, Excel paste table, two-agent interface contract)
- Updated `memory/discoveries.md` with iteration 15 entry
- Updated `memory/learning-log.md` (this file)

---

## 2026-07-11 (Iteration #14) — Agent Memory Management Skill (CoALA Four-Layer System)

**Category:** Agent technique / memory architecture
**Mode:** New skill — `skills/agent-memory-management.md`

**Searches performed:**
1. `CoALA agent memory "working memory" "episodic memory" "semantic memory" "procedural memory" Claude Code CLAUDE.md practical implementation patterns`
   — Hit alexop.dev "The Four Types of Memory for AI Agents" (June 2026), fountaincity.tech, YouTube
   CoALA explainer (TechieTalksAI, June 2026), and the Anthropic "Code with Claude 2026" conference
   coverage noting that memory architecture was a primary theme of the May 2026 developer conference.
   The alexop.dev post was the primary source: confirmed that Claude Code maps each CoALA me

2. `"agent memory" "stale facts" "memory pruning" "memory decay" practical patterns Cursor Claude 2026 prevent context poisoning`
   — Hit sitepoint.com AI Agent Memory Guide (2026) identifying the five most common production memory
   failures: context poisoning, session amnesia, stale semantic memory, procedural drift, episodic
   flooding. Also found Cursor forum thread (forum.cursor.com) with practitioners discussing HANDOFF.md
   as the only cross-tool solution that works because "it gets rewritten on every handoff, so it's
   always today, not what I thought on Tuesday." Also found the Graphiti + Cursor shared memory video
   (Atef Ataya, 684k views) confirming strong interest in persistent agent memory.

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
- Updated `memory/discoveries.md`
- Updated `memory/learning-log.md`
