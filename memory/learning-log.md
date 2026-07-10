# Alfred Learning Log

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
   the "Critic Agent" pattern (a secondary agent that reviews Builder Agent output against the Spec).
   Found DronaHQ Agentic SDLC guide confirming plan→code→verify as the dominant three-stage model.
2. `Claude Code "ultrathink" OR "extended thinking" practical patterns when to use Cursor agent 2025 2026`
   — Found comparative Claude Code vs Cursor analysis (FutureProofing.dev, Tech Insider 2026)
   confirming that builder-validator and self-critique patterns are now standard professional practice
   when output quality must be guaranteed before shipping to stakeholders.

**Gap identified:** No Alfred skill covers the builder-validator pattern — using a *second, independent
agent pass* as a critic to evaluate output quality. The existing skills cover adjacent territory:
- `agent-self-check.md` = prompting the builder to critique its own output (same context window, same biases)
- `agent-spec-driven.md` = writing the spec before the build
- `agent-workflow-orchestration.md` = chaining steps
None covered: fresh critic, spec-anchored evaluation, adversarial numeric audit, goal-alignment check,
or the result → action table (ACCEPT / NEEDS_FIXES / REJECT → what to do).

**Key facts gathered:**
- 75.3% of multi-agent failures stem from "planner-coder gap" — the builder didn't implement what the
  planner specified (arXiv 2025, confirmed in TestQuality/Anthropic SDLC guide).
- ASDLC.io "Critic pattern": secondary agent reads SPEC + output, flags divergence from spec.
  No access to builder's chain-of-thought — this is what prevents rationalisation bias.
- The builder-validator problem is structurally identical to unit tests in code: you don't verify
  a function by asking the function if it's correct. You run it against a known-good expected output.
- Cost insight: critic pass can use a smaller/faster model for structural checks — save the full
  model for adversarial numeric audits on financial outputs.
- Goal-alignment drift: long agent runs (40+ tool calls) frequently "solution drift" — the agent
  ends up solving a subtly different problem from what was originally asked. Pattern 4 catches this.

**Change summary:**
- Created `skills/agent-output-evaluation.md` (12.2k chars) — a complete, actionable skill covering:
  - Builder validation bias explanation (why same-agent self-check fails)
  - When-to-use checklist (2+ criteria = use the critic)
  - Four distinct critic patterns with paste-ready prompts:
    1. Fresh-window critic (any output)
    2. Spec-anchored critic (when SPEC.md exists)
    3. Adversarial numeric audit (finance/data outputs)
    4. Goal-alignment critic (long agent runs with drift risk)
  - How to embed in single session, multi-step chain, and Codex autonomous runs
  - What to do with each verdict (ACCEPT / NEEDS_FIXES / REJECT table)
  - Cost management guidance (smaller critic models, compression, loop cap)
  - Common mistakes table (5 antipatterns + fixes)
  - Quick-reference pattern selection table by situation
  - Five "Try asking:" examples Andrew can paste directly into Cursor

**Files modified:** `skills/agent-output-evaluation.md` (new), `memory/learning-log.md` (this entry),
`memory/discoveries.md` (appended).

---

## 2026-07-09 (Iteration #11) — MCP Security / Prompt Injection Defense Skill

**Category:** Agent security / MCP defense
**Mode:** New skill — MCP prompt injection and tool poisoning defense

**Searches performed:**
1. `MCP prompt injection attack 2025 2026 "tool poisoning" OR "rug pull" security defense Cursor Claude`
   — Found Simon Willison's April 2025 breakdown of MCP prompt injection; Microsoft Developer Blog
   confirming it as an active threat class; OWASP LLM Top 10 (2025) listing indirect prompt injection
   as #1; Johann Rehberger's "normalization of deviance" concern about how no-headline-incidents leads
   to false confidence.
2. `MCP server security audit checklist 2026 "read-only" "destructive" Claude Code`
   — Found Anthropic's own MCP security guidance recommending minimal permission scope; community
   practice of `--read-only` flags; version pinning to avoid rug-pull attacks.

**Change summary:**
- Created `skills/agent-mcp-security.md` — comprehensive MCP security skill covering the lethal
  trifecta threat model, three attack vectors, pre-flight session checklist, detection prompts,
  version pinning guidance, and a safe-by-default configuration template.

**Files modified:** `skills/agent-mcp-security.md` (new), `memory/learning-log.md` (this entry),
`memory/discoveries.md` (appended).

---

## 2026-07-09 (Iteration #10) — Agent Handoff Skill

**Category:** Agent technique / session management
**Mode:** New skill — HANDOFF.md discipline for cross-session continuity

**Change summary:**
- Created `skills/agent-handoff.md` covering the HANDOFF.md discipline: format, when to write it,
  how to load it in a new session, and how to split handoffs for parallel worktrees.

**Files modified:** `skills/agent-handoff.md` (new), `memory/learning-log.md` (this entry).
