# Alfred themes

Canonical visual identity files for **Jean Paul** (`design-agent`). Themes are **not bucket-gated** — the full `themes/` tree ships with Alfred on every machine.

## Resolution order (first match wins)

1. User explicitly names a theme ("use the Boostl theme")
2. `<project>/.alfred-theme` — one line, theme id (e.g. `boostl`)
3. **Project paths** in `themes/<id>/THEME.md` — path prefix match
4. Ask the user

After resolving, Jean Paul reads `themes/<id>/THEME.md`, then project overrides (`DESIGN.md`, `.cursor/rules/*-ui.mdc`). **Project overrides win** over the theme file.

## Create a new theme

1. Copy `themes/_template/THEME.md` to `themes/<id>/THEME.md`
2. Fill every section (Identity, Palette, Typography, Components, Spacing, Tone, Anti-patterns, Project paths)
3. Commit to Alfred `main`
4. Add `<id>` as a single line in the target project's `.alfred-theme`
5. Re-run `Provision-Cursor.ps1` or `Alfred-Sync.ps1` — themes are read from the Alfred clone path

## Available themes

| Id | Product |
|----|---------|
| `boostl` | Boostl — warm coral small-business SaaS |

Do not add stub themes for products that are not in active use.
