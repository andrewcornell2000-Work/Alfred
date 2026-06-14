# Alfred Learning Log

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
- Concrete proposed diff to `backend/main.py` (documented only — Andrew approves before applying): expanded `DANGEROUS_KEYWORDS_V2`, tightened fallback sets, generation of fallback sets from the Tool Registry (single source of truth), Tool Registry summary injected into `ALFRED_BRAIN_PROMPT`.
- Adds a "How to add a new tool without breaking routing" 5-step procedure so future MCP/CLI additions wire keywords + safety gate consistently.

**Use case:** Reference for any future change that touches routing — Andrew (or Alfred in a later iteration) can look up exactly which keyword set governs which behaviour, which destructive verbs are still ungated, and the standard procedure for adding a new tool without creating dead keywords or unsafe paths.

**Key findings worth flagging:**
- The safety gate is currently *too narrow* — 9 of Alfred's installed tools have destructive verbs that the gate doesn't catch. This is the highest-priority follow-up.
- The Tool Registry should be the single source of truth for keywords; today the fallback sets are hand-maintained in a second place and have already drifted.
- The brain prompt doesn't list the actual tools — it routes by category alone. A small change to inject the registry summary improves tool-name accuracy in user-visible plans.

**Files modified:** `skills/alfred-routing-keywords.md` (new, 16k chars), `memory/learning-log.md`

**Complementary skills:** `skills/github.md`, `skills/browser-automation.md`, `skills/office-mastery.md` (per-tool how-tos that should match the routing matrix).

---


---

## 2026-06-07 (Iteration #12) — Power Query Error Diagnostic Playbook (rewrite)

**Category:** Skills / Power Query & Data Engineering
**Mode:** Rewrite of broken/stub file

**Change summary:**
- Rewrote `skills/powerquery-column-errors.md` from a thin, escaped-character-corrupted stub into a complete, structured error diagnostic playbook
- Positioned explicitly as the *companion* to `power-query-transformations.md`: transformations skill = building queries, this skill = fixing broken queries. No content overlap.
- Covers a structured 6-step diagnostic workflow (read error → find failing step → check last good state → inspect formula → compare to source → fix at right layer)
- Error catalogue with cause + fix recipe for the 8 most common Power Query errors:
  1. `Expression.Error: column not found`
  2. `Column1/Column18 not found` (CSV column drift)
  3. `DataFormat.Error: We couldn't convert to Number`
  4. `Formula.Firewall: Query references other queries`
  5. `Expression.Error: The key didn't match any rows in the table`
  6. `OLE DB error` / gateway timeout
  7. `Value.Error: Cannot convert to logical`
  8. `Expression.Error: name isn't recognized`
- Prevention section: lock column positions with `Table.SelectColumns([], {"col1","col2"})` + named step pattern + parameterised source paths
- Try asking prompts for each diagnostic stage

**Files modified:** `skills/powerquery-column-errors.md` (rewrite), `memory/learning-log.md`
