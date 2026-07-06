# Alfred Learning Log

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

**Gap identified:** No existing skill in the Alfred pack covers MCP security. The gap is significant
because Andrew's pack has six MCPs with meaningful attack surface: `filesystem` (Finance OneDrive),
`ms-365` (mail + SharePoint + OneDrive), `fetch` (any URL), `playwright` (any live page), `github`
(repo + token), and `firecrawl` (crawling external sites). The `fetch` + `filesystem` combination
in particular is a classic trifecta entry point.

**Key facts gathered from research:**
- Real attack (Willison 2025): payload embedded in a fetched web page caused an agent to silently
  read `~/.cursor/mcp.json` and pass its contents as a parameter in the next tool call.
- Tool poisoning: tool description fields are passed verbatim to the model — attackers can embed
  instructions in Unicode zero-width characters or HTML comment markup invisible to human reviewers.
- "Rug pull": `npx -y package@latest` (Alfred's default) silently picks up compromised v1.1 after
  operator vetted v1.0. Version pinning is the mitigation.
- Microsoft guidance: separate read-only and write MCPs; never mix untrusted input sessions with
  write-capable tools active.
- Willison's "lethal trifecta" requires all three — removing any one leg breaks the attack chain.

**Change summary:**
- Created `skills/agent-mcp-security.md` (10.8k chars) — a complete, actionable skill covering:
  - Three main attack patterns with real examples (indirect injection, tool poisoning, trifecta)
  - Alfred pack exposure map table (all active MCPs rated by risk leg)
  - Seven concrete defences (least-MCP principle, isolation, description audit, version pinning,
    read-only defaults, output scrutiny, monitoring for unexpected tool calls)
  - Five paste-ready detection prompts for when behaviour feels off
  - Pre-flight security checklist for sensitive sessions
  - Six "Try asking:" examples Andrew can paste into Cursor

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
   session end so it always reflects present state, never accumulates stale history. Also found Firecrawl
   blog confirming a 'handoff' skill is among top-value Codex skills for 2026.
2. Fetched Cursor community forum page 2 of the thread — obtained real practitioner detail: the file
   must be plain text (all tools understand it), must be overwritten not appended, and must solve two
   problems simultaneously: recency (it's always "today") and portability (Cursor, Claude Code, and
   Codex can all consume it).

**Gap identified:** No existing skill covers the HANDOFF.md pattern specifically. The closest skill
(`agent-workflow-orchestration.md`) covers checkpoint artifacts within a task chain but does not cover
the session-end → session-start transfer pattern, cross-tool routing guidance (Cursor for design, Codex
for autonomous execution), or paste-ready prompts for generating and consuming a HANDOFF.md.

**Change summary:**
- Created `skills/agent-handoff.md` (9.2k chars) — a complete, actionable skill covering:
  - Three handoff types: same-tool next-day, cross-tool transfer, parallel worker dispatch
  - Full HANDOFF.md template with every section explained (What we're building / Done / Decisions locked /
    Next steps / Do NOT do / Key files / Open questions / Starting prompt)
  - Three paste-ready prompts for generating handoffs (quick, cross-tool Codex, parallel worker)
  - Three prompts for consuming a handoff (resume, Codex autonomous, conflict check)
  - Tool routing table: Cursor for design, Claude Code for autonomous execution, Codex for cloud parallel
  - Common mistakes table with fixes (7 anti-patterns)
  - Five "Try asking:" examples Andrew can paste directly into Cursor

**Files modified:** `skills/agent-handoff.md` (new), `requirements/discovered-tools.md` (appended),
`memory/learning-log.md` (this entry), `memory/discoveries.md` (appended).

---

## 2026-06-23 — ECC cherry-pick: 4 MCPs + continuous-learning instinct engine

**Category:** Harness upgrade / MCPs + continuous learning
**Mode:** Read-only review of `affaan-m/ECC`, ported only what beat current Alfred

**Source:** Cloned ECC read-only to `C:\Users\Andre\_ecc-review` (220k-star agent
harness). Reviewed its 28-MCP catalog, ~250 skills, 67 subagents, hook system,
and the continuous-learning-v2 "instinct" engine. Skipped 80% (language/crypto/
healthcare/enterprise boilerplate + the commercial layer); took the high-value bits.

**Change summary:**
- **MCPs** added to `cursor/mcp.json` (provisioner auto-skips if key/command missing):
  - `fal-ai` — image/video/audio generation (needs `FAL_KEY`)
  - `magic` — Magic UI components (no key)
  - `parallel-search` — citation-backed web search/fetch via `mcp-remote` (key-free)
  - `longhand` — lossless Claude Code session history → SQLite+ChromaDB (`pip install longhand`)
  - Note: parallel-search is HTTP-only upstream; Alfred's provisioner is command-based,
    so it's wired through the `mcp-remote` stdio bridge.
- **Instinct engine** — `scripts/instinct-cli.py` (lean, stdlib-only reimplementation of
  ECC's 1,914-line continuous-learning-v2; stores confidence-scored `when X → do Y`
  lessons in `memory/instincts/`, project + global scope, decay + TTL prune).
- **Hooks** wired in `.claude/settings.json` (Python, no node dep):
  - `SessionStart` → `session-start-instincts.py` surfaces active/strong instincts into context
  - `PreToolUse(Edit|Write|MultiEdit)` → `config-protection.py` blocks weakening of safety rules

**Files modified:** `cursor/mcp.json`, `scripts/instinct-cli.py`, `.claude/settings.json`,
`scripts/session-start-instincts.py`, `scripts/config-protection.py`, `requirements/discovered-tools.md`,
`memory/learning-log.md`, `memory/discoveries.md`.
