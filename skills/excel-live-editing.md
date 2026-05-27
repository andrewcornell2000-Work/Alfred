# Excel Live Editing

Use this skill for any task involving reading, writing, or formatting an Excel workbook.

## When to use
- Read or write cells and ranges
- Create or update charts, pivot tables, or tables
- Apply formatting (fonts, colours, borders, number formats)
- Insert or delete rows and columns
- Copy data between sheets or workbooks
- Execute VBA macros
- Sort, filter, find-and-replace data

## Requirements
- Excel must be running on this machine
- The target workbook must already be open in Excel
- MCP: excel (excellm)

## Approach
1. Call `list_open_workbooks` first — confirm which file to target
2. Call `explore` to understand the sheet layout before writing anything
3. Use `read` with batch references for multiple ranges — one call beats many
4. Prefer `write` over VBA for simple cell updates
5. Always confirm with the user before deleting rows, columns, or sheets
6. Use `execute_vba` only when no native tool covers the task

## Key tools
| Tool | What it does |
|---|---|
| `list_open_workbooks` | List all open Excel files and their sheets |
| `explore` | Sheet-level layout: used range, headers, sample data |
| `inspect_workbook` | Workbook-level radar: all sheets, named ranges, tables |
| `read` | Read cells or ranges; supports `batch=[...]` for multiple |
| `write` | Write values or formulas to cells or ranges |
| `format` | Apply font, fill, border, number format |
| `insert` | Insert rows or columns at a position |
| `delete` | Delete rows or columns |
| `copy_range` | Copy a range to another location or workbook |
| `sort_range` | Sort a range by one or more columns |
| `find_replace` | Find and replace values across a range |
| `create_chart` | Create a chart from a data range |
| `create_pivot_table` | Create a pivot table |
| `create_table` | Convert a range into an Excel Table |
| `execute_vba` | Run VBA code in the workbook |

## Safety rules
- Never delete data without user confirmation
- Never overwrite a range that has formulas unless the user explicitly requests it
- Use `get_recent_changes` to review what was modified if the user asks to undo
