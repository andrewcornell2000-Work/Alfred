# Alfred Learning Log

---

## 2026-07-17 (Iteration #17) — New skill: agent-task-decomposition.md — Plan-Before-Execute discipline

**Category:** Agent technique / task planning
**Mode:** NEW skill — `skills/agent-task-decomposition.md`

**Searches performed:**
1. `web_search` "agent task decomposition planning before execution 2026 Claude Cursor prompt patterns checklist" — confirmed "plan-and-execute" as a named 2026 agent architecture pattern (from LangChain/ReAct lineage: planner LLM generates a task queue, executor LLM processes it). Confirmed that this decompose-before-execute discipline is consistently cited as the top reliability lever in professional 2026 agentic workflows. Found Trilogy AI substack documenting a "28-bead dependency graph with 5 decision gates" for a complex build — evidence that serious practitioners plan extremely deliberately before executing. Also found claudedirectory.org documenting Claude Code's built-in Plan Mode feature.

2. `web_search` "Claude Code plan mode 2026 when to use how to activate finance report agent" — confirmed Claude Code Plan Mode is a real built-in feature toggled with `Shift+Tab` mid-session (or `claude --plan` flag). In Plan Mode, the agent can read and reason but cannot write files or run side-effecting commands. Also confirmed r/ClaudeCode community pattern: "breakdown into milestones → individual PRs" before any execution. Found Claude Code docs confirming the feature and its role as a safety/reliability gate.

**Gap identified:**
- `agent-spec-driven.md` has a "PLAN" phase but it assumes you already know what to build and are writing a formal spec — it starts from "write SPEC.md."
- `agent-workflow-orchestration.md` covers executing a multi-step chain after the plan exists.
- Neither covers the upstream question: **how do you get the agent to decompose a task before starting, check its own assumptions, map dependencies, and get approval** — especially for ambiguous requests like "build me the report" where the agent doesn't know what columns exist.
- Claude Code Plan Mode (a real feature) was not documented anywhere in the pack.

**New skill content (agent-task-decomposition.md, 9,653 chars):**
- Four failure modes of one-shot complex prompts (scope creep, hidden dependency, silent assumption, wrong decomposition) with root cause table
- Decision checklist: 7 criteria for when to decompose vs. one-shot
- Claude Code Plan Mode: how to activate (Shift+Tab, `--plan` flag), what it does, Plan Mode prompt template
- The generic decomposition prompt (works in Cursor, Claude Code, Codex)
- Dependency-first decomposition pattern for data workflows (dependency map format with example output)
- Finance/office examples: variance report, CSV analysis, pipeline refactor, Power BI measure
- "After the plan is approved" execute prompt
- Decomposition anti-patterns table (5 patterns with fixes)
- Skill cross-reference table (how this fits with spec-driven, orchestration, parallel-worktrees, etc.)
- 6 "Try asking:" prompts
- Relationship table to other skills

**Why this matters for Andrew:**
The most common failure mode in Andrew's finance work is "build me the July report" → agent invents column names, guesses sheet names, overwrites the wrong file. This skill teaches the habit of making the agent read and list what it sees FIRST, then plan, then get approval, then execute. Claude Code Plan Mode is specifically relevant — Andrew can toggle it with Shift+Tab and review the full plan before anything is touched.

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
   outputs launch thread, Peace of Code "Claude Certifi

---

## 2026-07-11 (Iteration #14) — Agent Memory Management Skill

**Category:** Agent technique / memory architecture
**Mode:** New skill — `skills/agent-memory-management.md`

**Searches performed:**
1. `web_search` "agent memory management CoALA framework Claude 2026" — confirmed the CoALA
   (Cognitive Architecture for Language Agents) framework from Princeton. Found sitepoint.com
   article documenting the 5 most common memory failures in 2026: context poisoning, session
   amnesia, stale semantic memory, procedural drift, episodic flooding.
2. `web_search` "Claude Code CLAUDE.md AGENTS.md HANDOFF.md agent memory layers 2026" — confirmed
   Claude Code's file-based memory approach. CLAUDE.md = semantic (facts/conventions),
   AGENTS.md = procedural (build commands), HANDOFF.md = episodic (session decisions).

---

## 2026-07-10 (Iteration #13) — Agent Output Evaluation Skill

**Category:** Agent technique / output quality
**Mode:** New skill — `skills/agent-output-evaluation.md`

**Searches performed:**
1. `web_search` "agent output evaluation critic pattern Claude 2026 checklist" — found multiple
   2026 sources describing the evaluator/critic pattern and LLM-as-judge technique.
2. `web_search` "LLM evaluator judge self-evaluation agent 2026 prompt patterns" — confirmed
   the peer-review prompting pattern where you ask the model to critique its own output as a
   "sceptical colleague."

---

## 2026-07-09 (Iteration #12) — Agent Reasoning Skill (agent-reasoning.md)

**Category:** Agent technique / extended thinking
**Mode:** New skill — `skills/agent-reasoning.md`

**Searches performed:**
1. `web_search` "Claude extended thinking 2026 budget tokens finance analysis" — confirmed
   Claude 3.7's extended thinking feature with `thinking` blocks and configurable `budget_tokens`.
2. `web_search` "chain of thought prompting agent 2026 step by step reasoning finance" — found
   patterns for forcing visible reasoning chains in both Cursor and Claude Code.

---

## 2026-07-03 (Iteration #11) — Agent handoff skill (agent-handoff.md)

**Category:** Agent technique / session continuity
**Mode:** New skill — `skills/agent-handoff.md`

**Searches performed:**
1. `web_search` "agent session handoff HANDOFF.md Claude Code Cursor 2026 multi-session" — found
   multiple 2026 sources describing the practice of writing end-of-session summary files.
2. `web_search` "agent memory handoff multi-session context continuity 2026" — confirmed the
   HANDOFF.md pattern as widely adopted in professional Claude Code workflows.
