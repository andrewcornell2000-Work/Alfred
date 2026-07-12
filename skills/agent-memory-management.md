# Agent Memory Management (The Four-Layer System)

> Agents don't fail because the model is bad — they fail because the *memory system* is bad. A single context window is just one of four memory layers. Set up all four and your agent stops forgetting.

*Framework: CoALA (Cognitive Architectures for Language Agents — Princeton, 2023/2026 applied edition).
Sources: alexop.dev, fountaincity.tech, sitepoint.com AI Agent Memory Guide (2026), Anthropic Claude Code memory docs.*

*Companion skills: `agents-md-project-context.md` (procedural layer setup), `agent-context-engineering.md` (working-memory tuning), `agent-handoff.md` (episodic → next session).*

---

## Why this matters right now

Most developers give agents one context window and wonder why they forget everything.
The CoALA framework (Princeton) shows that capable agents need **four distinct memory stores**.
Claude Code and Cursor already implement all four — but only if you deliberately wire them up.
Without that wiring, each session starts cold, re-derives conventions, and corrupts its own
outputs with stale facts.

The five most common memory failures in production (2026 data, sitepoint.com):
1. **Context poisoning** — wrong fact from a previous step survives to the final output
2. **Session amnesia** — agent re-derives decisions you confirmed two sessions ago
3. **Stale semantic memory** — CLAUDE.md says X but the codebase now does Y; agent follows the file
4. **Procedural drift** — AGENTS.md build commands are months out of date; agent runs the wrong test command
5. **Episodic flooding** — HANDOFF.md or scratch notes grow without pruning until they're useless

---

## The four memory types mapped to files on disk

| Memory type | What it holds | Claude Code file | Cursor file | Risk if neglected |
|-------------|--------------|-----------------|-------------|-------------------|
| **Working** | Active task, current conversation, open files | Context window (ephemeral) | Active tab / @-mentions | Too full → truncation / lost instructions |
| **Semantic** | Facts, conventions, domain rules, vocab | `CLAUDE.md` + `memory/` folder | `.cursorrules` + Cursor Rules | Stale facts corrupt outputs silently |
| **Procedural** | How to do things: build, test, deploy, run | `AGENTS.md` (commands) | `.cursorrules` (how-to sections) | Wrong commands; agent guesses flags |
| **Episodic** | What happened last session; decisions made | `HANDOFF.md` + session logs | `SCRATCH.md` / chat export | Session amnesia; re-derives everything |

**The key discipline:** treat each layer as a separate file with a separate update schedule. Conflating them (e.g., pasting episodic session notes into your semantic CLAUDE.md) is the root cause of most memory failures.

---

## Layer 1 — Working Memory (the context window)

This is the only layer the model *directly* reads during a session. Everything else must be loaded into it.

### Rules

1. **Load selectively** — never paste a full file when a section will do. Use `grep` or MCP tools to find the relevant 20 lines.
2. **Stable content first** — put SPEC, rules, and constraints at the top of the context (before any files or history). This maximises KV-cache hits on Claude and GPT-4o.
3. **Compress at checkpoints** — when the session has been running > 30 minutes, ask the agent to write a 3-bullet summary of confirmed facts before continuing. This avoids truncation of early decisions.
4. **Never re-paste** — if a file is already in context, reference it by name. Re-pasting restarts the cache and bloats the window.

### Try asking:
```
Before we continue, summarise in 3 bullets: (1) what we've confirmed is true, (2) what we've changed so far, (3) what's still open. Then continue.
```
```
Don't open any files yet. Tell me which 3 files are most likely relevant to this change, and why.
```

---

## Layer 2 — Semantic Memory (facts and conventions)

This is what the agent "knows" about your project that isn't obvious from the code. It lives in `CLAUDE.md` (Claude Code) or Cursor Rules.

### What belongs here

- Team conventions that aren't enforced by linting (e.g., "error messages are sentence case, no trailing period")
- Vocabulary: what "TaskKey", "DLP", "Boostly segment" mean in your context
- Data shape facts: column names, ID formats, enum values
- Architectural rules: which layers may import from which
- "Always" and "never" rules for the domain

### What does NOT belong here

- Session-specific decisions (that's episodic) → put in HANDOFF.md
- How to run the build (that's procedural) → put in AGENTS.md
- Open todos or in-progress work → put in SCRATCH.md

### Update discipline — the stale-fact problem

Semantic memory goes stale silently. An agent following an outdated `CLAUDE.md` will produce confidently wrong output. Schedule a review:

- **After any architecture change:** update CLAUDE.md that day
- **Monthly:** scan for facts that are no longer true (removed columns, renamed modules, changed APIs)
- **When an agent gets something wrong twice:** that's a signal the convention is either missing or wrong in CLAUDE.md

### Try asking:
```
Read CLAUDE.md. Are there any facts here that conflict with what you can see in the actual codebase? List any discrepancies.
```
```
We just confirmed that the "region" column uses ISO 3166-1 alpha-2 codes (not full names). Add that as a semantic fact to CLAUDE.md under the "Data Conventions" section.
```
```
I want to update our semantic memory. What conventions have we used in this session that aren't captured in CLAUDE.md yet?
```

---

## Layer 3 — Procedural Memory (how to do things)

This is operational knowledge: exact commands, scripts, deployment procedures. Lives in `AGENTS.md`.

### What belongs here

- Build, test, lint, deploy commands — with exact flags
- How to run a single test file (agents use this constantly)
- Which tools to use for which task (e.g., "use DuckDB MCP for CSV queries, never Excel for data > 10k rows")
- Agent-specific routing rules (see `mcp-routing.md`)

### Minimal AGENTS.md template for a finance/data project

```markdown
## Build & Test
```bash
# Run all tests
pytest tests/ -v

# Single file
pytest tests/test_reconciliation.py -v

# Lint (must pass before PR)
ruff check . --fix
```

## Data Rules
- Never open raw CSV in Excel — use DuckDB MCP for any file > 5k rows
- Column naming: snake_case throughout; no spaces in headers
- Date columns: always ISO 8601 (YYYY-MM-DD)

## Forbidden Zones
- NEVER touch /archive — frozen historical data
- NEVER overwrite source files — write to /output only

## MCP Routing
- Library docs → context7 MCP
- SharePoint files → ms-365 MCP
- SQL on CSV/Parquet → duckdb MCP
- PDF → markitdown MCP
```

### Try asking:
```
Read AGENTS.md and run the lint check. Tell me what the exact command is before you run it, then run it and report results.
```
```
Our build command changed — it's now `npm run build -- --mode staging`. Update AGENTS.md to reflect this and tell me what you changed.
```

---

## Layer 4 — Episodic Memory (what happened)

This is the session log: decisions made, paths explored and rejected, what changed. Without it, every new session re-derives everything from scratch.

The key file is **HANDOFF.md** — regenerated at the end of every session. See `agent-handoff.md` for full details. Key rules:

- **Always overwrite, never append.** Handoffs that grow become unusable.
- **One decision per bullet.** Not prose — not "we discussed the billing module" but "decided: billing module uses UTC timestamps, not local time, because DLP exports in UTC".
- **Include the next concrete action.** The session starting from HANDOFF.md should know its first step without any clarification.
- **Date-stamp every entry.** Stale episodic memory is the second most common failure mode.

### Episodic memory for long projects (the SCRATCH pattern)

For projects running over multiple weeks, maintain a `SCRATCH.md` alongside HANDOFF.md:

```markdown
# SCRATCH.md — Working notes (not authoritative)

## Decisions log (newest first)
- 2026-07-10: Confirmed: labour costs allocated by headcount ratio, not hours
- 2026-07-09: Rejected: real-time DLP pull — too slow. Use nightly export instead.
- 2026-07-08: Agreed: report output in /reports/2026/ — never overwrite previous months

## Paths explored and abandoned
- Tried: Graph API direct read of SharePoint list — throttling at 1k rows, use CSV export instead
- Tried: Power Query + DuckDB bridge — too fragile, use Python connector instead

## Open questions (not yet decided)
- [ ] Should variance > 10% trigger an email or just a flag in the report?
- [ ] Confirm with Andrew: is the "region" breakdown by state or by territory?
```

### Try asking:
```
We're done for today. Update HANDOFF.md with: (1) what we confirmed is true, (2) what we changed (files + what changed), (3) what's blocked and why, (4) the next concrete step to start fresh tomorrow. Overwrite the old file completely.
```
```
Read HANDOFF.md and SCRATCH.md. Tell me: what decision did we make about the data refresh cadence? I want to confirm it's still right.
```
```
I'm noticing SCRATCH.md has decisions from 3 months ago. Archive anything older than 30 days to SCRATCH-archive.md and summarise what's left in SCRATCH.md.
```

---

## Memory health checklist (run monthly or after any major change)

| Check | How to run it |
|-------|--------------|
| Semantic freshness | Ask agent: "Does CLAUDE.md contradict anything in the actual codebase?" |
| Procedural accuracy | Run each command in AGENTS.md manually; update any that fail |
| Episodic bloat | If HANDOFF.md > 100 lines, it's too old — regenerate from current state |
| Working memory overload | If sessions routinely exceed 20 tool calls before finishing, compress context mid-session |
| Stale SCRATCH entries | Archive decisions older than 30 days |

### Try asking:
```
Perform a memory health check: read CLAUDE.md, AGENTS.md, and HANDOFF.md. For each, flag any statement that looks stale, contradictory, or missing based on what you can see in the repo.
```

---

## Practical setup — the five files to create today

| File | Memory type | Location | Update when |
|------|------------|----------|-------------|
| `CLAUDE.md` or `.cursorrules` | Semantic | Repo root | Architecture changes; monthly review |
| `AGENTS.md` | Procedural | Repo root | Build/deploy command changes |
| `HANDOFF.md` | Episodic | Repo root | End of every session |
| `SCRATCH.md` | Episodic (working notes) | Repo root | During session (live notes) |
| `memory/` folder | Semantic (long-term) | Repo root | When conventions need more space than CLAUDE.md allows |

**Start here:** If you have none of these, create `CLAUDE.md` first (team conventions) and `AGENTS.md` second (build commands). Add HANDOFF.md discipline third. SCRATCH.md is optional but valuable for projects lasting more than a week.

---

## Anti-patterns (what goes wrong and how to fix it)

| Anti-pattern | Symptom | Fix |
|-------------|---------|-----|
| Single-file everything | CLAUDE.md has build commands, session notes, AND conventions — 500 lines and growing | Split into CLAUDE.md (semantic), AGENTS.md (procedural), HANDOFF.md (episodic) |
| Append-only HANDOFF.md | HANDOFF.md is 200 lines; agent takes 3 minutes to parse it | Overwrite every session — it's a current-state snapshot, not a log |
| Stale semantic facts | Agent confidently uses the old column name after a schema migration | Review CLAUDE.md after every structural change; ask agent to flag contradictions |
| No episodic memory | Every Monday session starts with "where were we?" | Generate HANDOFF.md at end of every session without exception |
| Working memory overload | Agent starts forgetting instructions from earlier in the same session | Compress at checkpoints: ask for 3-bullet summary before continuing |
| Mixing episodic and semantic | Session decisions accumulate in CLAUDE.md | Only promote to CLAUDE.md if the decision is now a permanent convention; otherwise it goes in HANDOFF.md |

---

## Quick reference: which layer answers which question?

| Question | Layer | File |
|----------|-------|------|
| "What are our naming conventions?" | Semantic | CLAUDE.md |
| "How do I run the tests?" | Procedural | AGENTS.md |
| "What did we decide last Tuesday?" | Episodic | HANDOFF.md / SCRATCH.md |
| "What is the agent working on right now?" | Working | Context window (no file) |
| "What does 'TaskKey' mean in this project?" | Semantic | CLAUDE.md |
| "Is this column still named 'dept_code'?" | Semantic | CLAUDE.md (check against codebase) |
| "What's the next concrete step?" | Episodic | HANDOFF.md |
