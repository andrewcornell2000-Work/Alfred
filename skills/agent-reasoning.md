# Agent Reasoning Patterns

Use this skill when a task is ambiguous, multi-step, or easy to get wrong on the first attempt.
Improves answer quality and reduces costly rework.

## When to slow down and structure

- Cross-system reconciliation (Excel vs Power BI vs Tanda)
- DAX / Power Query errors with multiple possible causes
- Refactors touching more than 3 files
- "Why is this number wrong?" root-cause requests
- Any destructive action (delete, overwrite, publish)

## Pattern: decompose → verify → act

1. **State the goal in one sentence**
2. **List unknowns** — what must be true before acting?
3. **Pick the cheapest verification** — row count, single measure, one file grep
4. **Act on one slice** — fix one measure / one query / one file first
5. **Confirm** — re-run the same check; only then broaden scope

## Use `sequential-thinking` MCP for step 2–3

When the problem has more than two plausible causes, call sequential-thinking *before* editing:
- Forces explicit hypotheses
- Surfaces dependencies (e.g. "refresh Silver before checking report")
- Produces a short plan the user can approve

## Use `memory` MCP for stable team knowledge

After confirming a convention (TaskKey format, dataflow order, folder layout), store it in memory
so future sessions do not re-derive it from scratch.

## Reasoning vs token spend

Good reasoning **reduces** tokens overall:
- One structured plan beats five failed attempts
- A targeted DAX query beats pasting whole tables
- Asking one clarifying question beats guessing and undoing

## Hand-off to the right agent

| Task shape | Prefer |
|------------|--------|
| Repo code change | Codex |
| Power BI model / DAX | Claude Code + `pbi` / Power BI MCP |
| Quick factual answer | Alfred GENERAL or SEARCH (Tavily) |
| Live Excel | `excel` MCP |
| Office file creation | python-docx / python-pptx / pandoc |

Alfred's router (`backend/main.py`) scores keywords — Dev Portal changes should update
`TOOL_REGISTRY` keywords when a new tool skill is added.
