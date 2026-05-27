# Power BI Model Editing and Visual Creation

Use this skill for any task involving Power BI data models, measures, DAX, tables, relationships,
or creating and editing report visuals.

## Two tools — use both together

| Tool | What it handles | Prerequisite |
|---|---|---|
| `powerbi-modeling-mcp` | Semantic model: measures, tables, relationships, RLS, DAX | Power BI Desktop open |
| `pbi-cli` | Report visuals: create, update, delete, bind data, pages | `pbi connect` run in terminal |

## Visual creation with pbi-cli

pbi-cli gives Claude Code 13 Power BI skills and connects directly to Power BI Desktop.

### Connect first
```
pbi connect     # run once per session with Power BI Desktop open
```

### Core visual commands
```
pbi visual list --page "Page Name"           # list all visuals on a page
pbi visual add --page "Overview" --type barChart --x 0 --y 0 --w 400 --h 300
pbi visual update --id <visualId> --title "Sales by Region"
pbi visual delete --id <visualId>
pbi visual bind --id <visualId> --field "Sales[Amount]" --role "Y"
pbi visual bulk-bind --id <visualId> --fields '[{"field":"Date[Year]","role":"X"},{"field":"Sales[Amount]","role":"Y"}]'
```

### Page management
```
pbi page list
pbi page add --name "New Page"
```

### Data queries (for building visuals)
```
pbi dax execute "EVALUATE SUMMARIZE(Sales, Date[Year], \"Total\", SUM(Sales[Amount]))"
pbi measure list
```

## Typical visual creation workflow
1. `pbi connect` — link to Power BI Desktop (user runs this with Desktop open)
2. `pbi dax execute` — query data to confirm field names and values
3. `pbi measure list` — confirm available measures
4. `pbi visual add` — create the visual container on the target page
5. `pbi visual bind` — bind fields to visual roles (X axis, Y axis, Legend, etc.)
6. `pbi visual update` — set title, formatting
7. Ask user to refresh Desktop to see changes

## Semantic model editing with powerbi-modeling-mcp

| Area | What can be changed |
|---|---|
| Measures | Create, edit, or delete DAX measures |
| Calculated columns | Add or modify calculated columns |
| Tables | Create calculated tables, edit properties |
| Relationships | Add, remove, or edit relationships |
| Calculation groups | Create/edit calculation items |
| Hierarchies | Add or edit user hierarchies |
| Security roles | Add or edit RLS DAX filters |

### Model edit pattern
1. `model_operations → getModel` — read current state
2. `transaction_operations → beginTransaction`
3. Make targeted change (measure, column, relationship)
4. `dax_query_operations → executeQuery` — verify result
5. `transaction_operations → commitTransaction` (or rollback)

## Power Query errors
When user reports missing columns, schema drift, or folder-combine errors:
1. Inspect Transform Sample File query first
2. Check Changed Type steps → Removed Columns → Expanded Table → Renamed Columns
3. Only inspect actual source files if query steps are inconclusive — never scan all files first

## Routing note
- **Measures, DAX, tables, relationships** → use `powerbi-modeling-mcp` via Claude Code
- **Visuals, report pages, chart types, data binding** → use `pbi-cli` via Claude Code
- **Visual layout formatting** (colours, fonts, sizes) → `pbi visual update` after `pbi connect`

## Safety rules
- Always open a transaction before model writes; always commit or rollback
- Never drop a table or delete a measure without user confirmation
- Verify DAX with executeQuery after every measure change before committing
- Always run `pbi visual list` before deleting to confirm the target visual ID
