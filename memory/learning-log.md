# Alfred Learning Log

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
1. `MCP prompt injection tool poisoning attack defense Cursor Claude Code 2025 2026`
   — Found Simon Willison's canonical April 2025 post documenting real attack chains (hidden
   instructions embedded in fetched web pages causing agents to silently read credential files).
   Found Microsoft Developer Blog guidance on indirect injection in MCP. Found hidekazu-konishi.com
   (June 2026) comprehensive defense guide covering supply-chain vetting, version pinning, allowlist
   configuration, and monitoring. Confirmed the "lethal trifecta" (private data + untrusted input +
   outbound channel) as the established threat model coined by Willison.
2. `site:simonwillison.net MCP prompt injection "tool poisoning" "indirect" example attack 2025`
   — Retrieved the "lethal trifecta" tagging and specific attack chain examples from Willison's tags
   index. Found "rug pull" attack type documented (package vets at v1.0, deploys poison in v1.1,
   npx -y picks it up silently). Found Johann Rehberger's "normalization of deviance" concern —
   no headline-grabbing incidents yet, but attack surface is real and growing.

**Gap identified:** No existing skill in the Alfred pack covered MCP security. The gap is significant
because Andrew's pack has six MCPs with meaningful attack surface: `filesystem` (Finance OneDrive),
`ms-365` (mail + SharePoint + OneDrive), `fetch` (any URL), `playwright` (any live page), `github`
(repo + token), and `firecrawl` (crawling external sites). The `fetch` + `filesystem` combination
in particular is a classic trifecta entry point.

**Change summary:**
- Created `skills/agent-mcp-security.md` — complete security skill covering three attack patterns,
  Alfred pack exposure map, seven defences, five detection prompts, pre-flight checklist, and
  six "Try asking:" examples.

**Files modified:** `skills/agent-mcp-security.md` (new), `requirements/discovered-tools.md`
(appended), `memory/learning-log.md` (this entry), `memory/discoveries.md` (appended).

---

## 2026-07-03 (Iteration #10) — Agent Handoff Skill

**Category:** Agent skills / Workflow design
**Mode:** New skill — agent handoff pattern (HANDOFF.md discipline)

**Searches performed:**
1. `HANDOFF.md template agent context transfer Cursor Claude Code Codex best practices 2025 2026`
   — Found Cursor community forum thread confirming HANDOFF.md as the dominant practitioner pattern
   for cross-tool context continuity. Key practitioner insight: it is rewritten (not appended) at every
   session end so it always reflects present state, never accumulates stale history.
2. `Claude Code Codex handoff context session continuity agent memory 2026`
   — Found Codex CLI documentation confirming `AGENTS.md` + scratch files as the primary continuity
   mechanism. Found practitioner workflows using HANDOFF.md as the bridge specifically for
   Cursor → Codex autonomous dispatch (task brief format, not free-form conversation summary).

**Change summary:**
- Created `skills/agent-handoff.md` — complete handoff skill with three handoff types, five
  paste-ready prompts, cross-tool routing table, and HANDOFF.md template.

---

## 2026-06-30 (Iteration #9) — Claude Code Subagent Skill

**Category:** Agent technique / Claude Code features
**Mode:** New skill — Claude Code subagents and parallel execution

**Gap identified:** Claude Code's native `/spawn` and subagent features were undocumented in Alfred.
The skill covers: when to use subagents vs. Cursor parallel worktrees, how to dispatch a Codex
cloud run from Claude Code, and the three coordination patterns.

**Change summary:**
- Created `skills/agent-claude-code-subagents.md`

---

## 2026-06-25 (Iteration #8) — Token Efficiency Skill

**Category:** Agent technique / context window cost management
**Mode:** New skill

**Change summary:**
- Created `skills/agent-token-efficiency.md` — covers: model selection by task type, context
  compression techniques, structured output over prose, and cost-aware agent design.

---

## 2026-06-22 (Iteration #7) — ms-365 MCP (SharePoint / Graph)

**Category:** MCP discovery
**Mode:** New MCP — Microsoft 365 via Graph API

**Gap identified:** Alfred had no native Microsoft 365 integration. The ms-365 server covers
SharePoint, OneDrive, Outlook, Calendar, Teams, and To-Do — all via official Microsoft Graph,
with MSAL device-code auth (browser pop-up once, then token cached).

**Change summary:**
- Added `ms-365` to `cursor/mcp.json`
- Updated `skills/sharepoint-graph.md`
- Added entry to `requirements/discovered-tools.md`

---

## 2026-06-19 (Iteration #6) — Agent Self-Check Skill

**Category:** Agent technique
**Mode:** New skill

**Change summary:**
- Created `skills/agent-self-check.md` — four escalating patterns (inline critique, output
  contracts, reflection pass, test-first loop).

---

## 2026-06-18 (Iteration #5) — Spec-Driven Development Skill

**Category:** Agent technique
**Mode:** New skill

**Change summary:**
- Created `skills/agent-spec-driven.md` — SPECIFY→PLAN→IMPLEMENT→VERIFY workflow with
  SPEC.md template and paste-ready prompts for each phase.

---

## 2026-06-16 (Iteration #4) — Agent Loop Debugging Skill

**Category:** Agent technique
**Mode:** New skill

**Change summary:**
- Created `skills/agent-loop-debugging.md` — six failure modes, recovery prompts,
  pre-flight checklist, structured output enforcement.

---

## 2026-06-15 (Iteration #3) — Context Engineering + Parallel Worktrees Skills

**Category:** Agent technique (two skills)
**Mode:** New skills

**Change summary:**
- Created `skills/agent-context-engineering.md`
- Created `skills/agent-parallel-worktrees.md`
