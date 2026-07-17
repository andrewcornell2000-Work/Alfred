---
name: jean-paul-design
description: Jean Paul design stack — theme resolution, skill precedence, between-steps UX, impeccable critique. Use when working on UI or invoking design-agent.
---

# Jean Paul design stack

When working on UI or invoking **Jean Paul** (`design-agent`):

## Theme resolution (first match wins)

1. User explicitly names a theme
2. `<repo>/.alfred-theme` — one-line id (e.g. `boostl`)
3. **Project paths** in `Alfred/themes/<id>/THEME.md`
4. Ask user

Then read `Alfred/themes/<id>/THEME.md`.

## Skill precedence

1. **Project brand rules** (`*-ui.mdc`, `DESIGN.md`) — when present, they win
2. **Alfred theme** (`themes/<id>/THEME.md`)
3. **`between-steps-ux`** — if in repo `.cursor/skills/` (async/state-transition UX)
4. **`impeccable`** — critique + audit before merge
5. **`ui-design-brain`**, **`frontend-design`**, **`accessibility`** in `~/.agents/skills`
6. **`design-taste-frontend`** — anti-slop only; never override project/theme palette
7. **Magic UI MCP** — when it improves UX without breaking brand

## Global subagents (Alfred `agents/`, synced to `~/.cursor/agents`)

| Name | Invoke |
|------|--------|
| Jean Paul | `design-agent` / "Jean Paul, …" |
| Handoff prompts | Skill `alfred-prompt-handoff`. Ordinary plans → Cursor Plan Mode. |

Project-only subagents stay in `<repo>/.cursor/agents/` (e.g. `session-hub`, `competitive-analyst`).

## Between-steps rule

Before shipping multi-step UI, verify: upfront controls, lock-on-commit, undo, usage pre-flight, aggregate progress. See repo `between-steps-ux` checklist when present.

## Provision on new machine

Set `ALFRED_PROJECT_PATHS` to project clone path(s) in Alfred `.env`, then:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
```

---

## Boostl override (when theme id is `boostl`)

- Canonical UI rule: `.cursor/rules/boostly-ui.mdc`
- Impeccable: `DESIGN.md`, `PRODUCT.md` (Maria persona)
- Logo: `app/components/boostly-logo.tsx` only
- Coral palette: `#FF6B4A` → `#FF8F6B`, bg `#FFFBF7`, borders `#f0e6df`
- See `Alfred/themes/boostl/THEME.md` for full tokens
