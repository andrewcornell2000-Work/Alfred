---
name: boostly-jean-paul-design
description: Boostl Jean Paul design stack — between-steps UX, impeccable critique, ui-design-brain, skill precedence over warm coral brand. Use when working on boostly UI, create-ad flows, or invoking design-agent.
---

# Boostl — Jean Paul design stack

When working on **Boostl** (`boostly` repo) or invoking **Jean Paul** (`design-agent`):

## Skill precedence (brand wins)

1. `.cursor/rules/boostly-ui.mdc` + repo `DESIGN.md`
2. `.cursor/skills/between-steps-ux/` — async/state-transition UX (Maria persona)
3. `impeccable` — critique + audit before merge
4. `ui-design-brain`, `frontend-design`, `accessibility` in `~/.agents/skills`
5. `design-taste-frontend` — anti-slop only; never override coral palette

## Subagents (Boostl repo)

| Name | Invoke |
|------|--------|
| Jean Paul | `design-agent` / "Jean Paul, …" |
| Mr Smith | `mr-smith` / "Mr Smith, …" |
| Session Hub | `session-hub` / "Hub: session start" |

Cursor: `.cursor/agents/`. Claude Code: `.claude/agents/` (synced by `tools/sync-claude-agents.ps1`).

## Provision on new machine

Set `ALFRED_PROJECT_PATHS` to the boostly clone path in Alfred `.env`, then:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
```

See boostly `AGENT-TOOLING.md` for full checklist.

## Between-steps rule

Before shipping multi-step UI, verify: upfront controls, lock-on-commit, undo, usage pre-flight, aggregate progress. See boostly `.cursor/skills/between-steps-ux/checklist.md`.
