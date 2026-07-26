---
name: powerbi-custom-visual-development
description: Develop, validate, package, and regression-test Power BI custom visuals built with powerbi-visuals-tools and pbiviz. Use when working with pbiviz.json, capabilities.json, custom visual TypeScript, formatting models, data roles, .pbiviz packages, or Power BI Desktop developer visuals.
---

# Power BI Custom Visual Development

Use for custom visual projects, not ordinary PBIR report authoring or semantic-model changes.
Follow the repository's scripts first; do not install or upgrade tooling without approval.

## 1. Orient to the visual contract

Read:

- `package.json` scripts and pinned versions
- `pbiviz.json` metadata, API version, asset paths, and visual class
- `capabilities.json` data roles, mappings, objects, and privileges
- `src/visual.ts` update/render lifecycle
- formatting settings/model files
- existing development, package, import, and ship scripts

If a Graphify graph exists, query it before broad source inspection.

## 2. Validate metadata and capabilities

Check that:

- `pbiviz.json` paths exist and version uses four numeric parts
- visual `guid` and class name are stable
- placeholder author, repository, support, or description values are resolved before release
- each data-role name matches its `dataViewMappings` references
- categorical, table, or matrix mapping matches the parser in `Visual.update`
- reduction limits are deliberate for expected report sizes
- formatting object/property names match the formatting model and persistence selectors
- `privileges` is empty unless the visual genuinely requires declared access

Do not change a GUID or data-role name casually; existing reports can depend on them.

## 3. Exercise representative data shapes

Test the smallest useful matrix for the visual:

- no data and missing required roles
- one row/category and one measure
- multiple series, groups, or hierarchy levels
- null, blank, zero, negative, and large values
- duplicate labels and unsorted periods
- highlighted/selected data when supported
- data beyond reduction limits

For matrix visuals, test collapsed/expanded hierarchy, subtotals, grand totals, and changing
column groups. For categorical visuals, test category/measure length mismatch and grouped
values.

## 4. Test the visual lifecycle

Verify repeated `update` calls do not leak DOM nodes, event handlers, or stale state. Test:

- resize from narrow to wide and back
- formatting changes without data changes
- theme and high-contrast behavior
- selection, tooltips, and keyboard/accessibility behavior where implemented
- persisted formatting after reopening the report
- performance with realistic row counts

Keep parsing, layout, and rendering failures distinguishable; an empty visual should provide a
useful message rather than silently fail.

## 5. Run the repository validation ladder

Use available scripts in this order:

1. lint
2. repository-specific typecheck or development check
3. focused tests, if present
4. `pbiviz package` through the repository's package script

The official tooling commands are:

```powershell
pbiviz
pbiviz start
pbiviz package
```

Prefer `npm run start` / `npm run package` when defined so pinned project tooling and wrappers
are honored. Do not run `npm i -g powerbi-visuals-tools@latest` unless the user approves an
upgrade.

## 6. Verify in Power BI

Packaging success does not prove report behavior. Import the generated `.pbiviz` into a safe
Power BI Desktop test report (or use the repository's import script), bind each supported data
shape, and verify:

- field wells and display names
- formatting pane controls and defaults
- resize, filtering, highlighting, and drill/expand behavior
- save, close, reopen persistence
- no unexpected network or file privileges

Do not overwrite a user's production report or installed visual without explicit approval.

## 7. Release result

Report:

1. visual and package version
2. commands run and results
3. capabilities/data-shape coverage
4. Desktop checks completed
5. blocking defects and residual risk
6. generated `.pbiviz` path, if packaging was requested

## Anti-patterns

- Editing `capabilities.json` without tracing the parser and formatting model
- Treating package success as regression coverage
- Testing only the happy-path dataset
- Changing the GUID to fix an import problem
- Installing latest global tooling over a pinned project without approval
