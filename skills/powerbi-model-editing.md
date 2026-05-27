# Power BI Model Editing

Use this skill for any task involving Power BI data models, measures, DAX, tables, or relationships.

## What Alfred can edit via MCP
The Power BI Modeling MCP (powerbi-modeling-mcp) connects directly to a live Power BI Desktop
model and can read and write the semantic layer:

| Area | What can be changed |
|---|---|
| Measures | Create, edit, or delete DAX measures |
| Calculated columns | Add or modify calculated columns on any table |
| Tables | Create calculated tables, edit properties |
| Relationships | Add, remove, or edit relationships (cardinality, direction) |
| Calculation groups | Create/edit calculation items and precedence |
| Hierarchies | Add or edit user hierarchies |
| Perspectives | Create or modify perspectives |
| Security roles | Add or edit RLS row-level security roles and DAX filters |
| Partitions | Inspect or modify table partitions |
| Named expressions | Shared expressions (M functions) used in Power Query |

## Requirements
- Power BI Desktop must be open with the model loaded
- MCP: powerbi-modeling-mcp (VS Code extension from Microsoft Analysis Services)
- A transaction must be opened before writing; commit or rollback when done

## Approach for model edits
1. Use `model_operations` → `getModel` to read the current state before making changes
2. Use `transaction_operations` → `beginTransaction` before any write
3. Make targeted changes (measure, column, relationship)
4. Use `dax_query_operations` → `executeQuery` to verify the result
5. Use `transaction_operations` → `commitTransaction` to save, or `rollbackTransaction` to undo

## DAX measure editing pattern
```
1. Read existing measure: measure_operations → getMeasure
2. Open transaction
3. Update with new DAX: measure_operations → updateMeasure
4. Test with executeQuery: SELECT [MeasureName] FROM $SYSTEM.DISCOVER_…
5. Commit or rollback
```

## Routing note
- **Data model changes** (measures, tables, relationships, DAX) → use powerbi-modeling-mcp via Claude Code
- **Visual layout changes** (chart types, visual formatting, filter pane, report pages) → these require
  editing the .pbix file directly or using the Power BI REST API; not handled by powerbi-modeling-mcp

## Power Query errors
When the user reports missing columns, schema drift, or folder-combine errors:
1. Inspect Transform Sample File query first
2. Check Changed Type steps
3. Check Removed Columns steps
4. Check Expanded Table Column steps
5. Check Renamed Columns steps
6. Only inspect actual source files if query steps are inconclusive
Do NOT scan all source files immediately — always start with query step diagnosis.

## Safety rules
- Always open a transaction before writing; always commit or rollback
- Never drop a table or delete a measure without user confirmation
- Verify DAX with executeQuery after every measure change before committing
- DANGEROUS_KEYWORDS gate in Alfred blocks dispatch if destructive terms are detected
