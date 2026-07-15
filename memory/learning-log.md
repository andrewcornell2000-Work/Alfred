# Alfred Learning Log

---

## 2026-07-14 (Iteration #16) — Hooks deep-dive: exit codes, HOOK_INPUT, UserPromptSubmit, JSON block output

**Category:** Agent technique / Claude Code hooks
**Mode:** IMPROVE existing skill — `skills/agent-claude-code-subagents.md`

**Searches performed:**
1. `web_search` "Claude Code hooks exit codes PreToolUse UserPromptSubmit 2026" — confirmed the
   three exit code semantics (0=pass, 1=soft error Claude sees, 2=hard block that cancels action).
   Found documentation on `UserPromptSubmit` hook's `additionalContext` JSON output feature:
   hooks at this event can return `{"additionalContext": "..."}` which Claude sees prepended to
   the prompt — powerful for injecting project context without manual repetition.
   Source: Anthropic Claude Code docs, github.com/anthropics/claude-code-hooks-mastery (2026).

2. `web_search` "Claude Code hooks HOOK_INPUT JSON schema matcher tool name 2026" — confirmed
   that `HOOK_INPUT` (env var) contains the full action JSON with `tool_name`, `tool_input.file_path`,
   `tool_input.command`, `tool_input.content` fields. Confirmed matcher is a regex on Claude Code's
   *internal* tool names: `Write`, `Edit`, `Read`, `Bash`, `Glob`, `Grep` (capitalised) — NOT
   Cursor-style `write_file` / `read_file` names. Also confirmed structured JSON output from
   `PreToolUse`: `{"hookSpecificOutput": {"hookEventName":"PreToolUse","permissionDecision":"deny",
   "permissionDecisionReason":"..."}}` — more precise than a plain text exit 2.

**Gap identified in existing skill:**
- Previous version listed hook events correctly but did not explain exit codes (crucial — without
  this, developers write exit 2 in a PostToolUse hook and wonder why nothing is blocked).
- `HOOK_INPUT` environment variable was not documented at all.
- `UserPromptSubmit` was only mentioned in the events table, no config example.
- Structured JSON block output (`permissionDecision: "deny"`) was entirely absent.
- Windows path handling in hooks (PowerShell vs jq) was not addressed.
- Part 3 (end-of-turn quality gate pattern) was missing.
- Finance-checker subagent was not in the previous version.

**Changes made:**
- Rewrote `skills/agent-claude-code-subagents.md` (13,907 chars):
  - Added exit code table: 0/1/2 semantics clearly explained
  - Added `HOOK_INPUT` JSON schema with field list
  - Added structured JSON output format for `PreToolUse` blocks
  - Added `UserPromptSubmit` hook example with `additionalContext` output
  - Expanded events table to 6 events with "Can block?" column
  - Added Windows-specific note (pwsh vs jq)
  - Added finance-checker subagent for Excel/CSV/Power BI work
  - Added Part 3: end-of-turn quality gate (Stop hook + bash script template)
  - Expanded to 12→8 hook configs (kept all new types, trimmed redundant variants)
  - Added "What are all lifecycle events? Which can block?" to Try asking section
- Updated `memory/discoveries.md` with iteration 16 entry

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

**Category:** Agent technique / memory
**Mode:** New skill — `skills/agent-memory-management.md`

**Searches performed:**
1. CoALA framework (Princeton 2023, widely referenced in 2026) — four memory types: Working,
   Semantic, Procedural, Episodic. Each maps to specific Claude Code / Cursor files on disk.
2. Five most common agent memory failures in 2026 (sitepoint.com): context poisoning, session
   amnesia, stale semantic memory, procedural drift, episodic flooding.

**Change summary:**
- Created `skills/agent-memory-management.md`
- Documented all four memory layers with concrete file mappings
- Added five failure modes with prevention strategies
- Added "Try asking:" prompts for memory management tasks
