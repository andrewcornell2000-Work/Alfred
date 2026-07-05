# Agent Playbook

Consolidated guidance for Cursor, Claude Code, and Codex agents. Use this instead of loading multiple overlapping `agent-*` skills.

For deep dives, see archived copies in `skills/_archive/agent/`.

---

## Reasoning: decompose → verify → act

Use when a task is ambiguous, multi-step, or easy to get wrong.

1. **State the goal in one sentence**
2. **List unknowns** — what must be true before acting?
3. **Cheapest verification first** — row count, one grep, single measure
4. **Act on one slice** — one file / one query / one measure
5. **Confirm** — re-run the same check before broadening

Write a short numbered plan before editing when there are 2+ plausible causes. Ask before destructive changes.

---

## Token discipline

1. **Search before read** — Grep/Glob to find line ranges before opening whole files
2. **Read partial files** — offsets/limits, not 2000 lines when 40 suffice
3. **One tool per job** — see `skills/mcp-routing.md`
4. **Batch independent lookups** — parallel when no dependency
5. **Don't re-read** — reference content already in the conversation
6. **Structured output** — bullets and tables over prose

---

## Loop recovery (when an agent stalls)

| Symptom | Fix |
|---------|-----|
| Wrong MCP / retry loop | Stop; pick one path from `mcp-routing.md`; read the error |
| Context loss | Write checkpoint to file; restart with that file as input |
| Goal drift | Restate original goal in one sentence; cancel unrelated work |
| "Done!" but empty output | Verify file exists and is non-empty before accepting |
| MCP hang >5s | Bail to native tools for the rest of the turn |

Do not restart blindly — find the last successful step first.

---

## Multi-step work

- Prefer **one session with a checklist** over many subprocess spawns
- Write **HANDOFF.md** or update `memory/current-focus.md` at phase boundaries
- For repo changes spanning 3+ files: plan → edit → verify tests/lint

Spec-driven tasks: use `SPEC.md` for design intent (see `skills/_archive/agent/agent-spec-driven.md` if needed).

---

## Web search in agent sessions

Search only when live/external data is required. Do not search for:

- Code already in the repo
- Timeless explanations
- Routine refactors

When searching: one primary web path (`parallel-search` or Tavily via Alfred CLI). See `skills/web-search.md`.

---

## Skill and catalog hygiene

Before creating a skill:

1. Grep `skills/` and `requirements/catalog-index.json`
2. **Update existing** file if topic overlaps
3. Include **"Try asking:"** examples
4. Never duplicate `mcp-routing` or lean-ctx content

Learning workflow: `docs/LEARNING-WORKFLOW.md`

---

## Provider hand-off (Alfred CLI)

| Task | Provider |
|------|----------|
| Repo code | Codex |
| Power BI / Excel MCP | Claude Code |
| Quick chat | Claude (GENERAL) |
| Live facts | SEARCH + Tavily |

Dev Portal changes dispatch to Claude Code after confirmation.
