# Agent Planning — Plan before you execute

Use when a task is multi-step, ambiguous, or costly to get wrong. Prefer **Cursor / Claude Plan Mode** when available; this skill is the checklist either way.

*Replaces overlapping `agent-task-decomposition` + `agent-reasoning`. Distinct from `prompt-handoff` (copy-paste executor prompts) and `agent-handoff` (session HANDOFF.md).*

---

## When to plan (two or more)

- Touches more than one file or data source
- Hard to explain in one sentence
- Order-of-operations constraints
- More than ~5 tool calls expected
- Later steps depend on earlier outputs
- Wrong answer is expensive to undo
- Inputs/columns/sheets not confirmed yet

**One-shot is fine for:** lookups, typos, renames, single-row/formula fixes.

---

## Pattern: decompose → verify → act

1. **Goal** in one sentence
2. **Unknowns** — what must be true before acting?
3. **Cheapest verification** — row count, one measure, one grep
4. **One slice** — fix one file / measure / query first
5. **Confirm** — re-run the same check; then broaden

## Plan Mode

- Cursor: switch to Plan mode (read-only) until the user approves
- Claude Code: `Shift+Tab` / `claude --plan`

While planning: no file writes, no side-effecting commands. Present a numbered plan with files, outputs, dependencies, and assumptions — then ask to confirm.

## Numbered plan shape

For each step:

- What you will do (plain English)
- Files / data sources read or written
- What the step produces and what depends on it
- Assumptions to confirm

End with: **Do not execute until the user says go** (when in Plan Mode or when the change is destructive).

## Anti-patterns

- Spawning a planner subagent — stay in the current agent
- Planning MCPs or “thinking servers” — native Plan Mode is enough
- Five failed attempts instead of one short plan
