# Power Query Error Diagnostic Playbook

**Purpose:** Fast, structured diagnosis and repair of broken Power Query queries — column errors, type errors, expansion failures, formula firewall, refresh failures. Companion to `power-query-transformations.md` (which covers *building* queries; this covers *fixing* them).

**When to use:** A query that worked yesterday is broken today, a refresh failed in the Service, a folder combine started returning fewer rows, or the editor shows red error rows.

---

## The Golden Rule of Power Query Debugging

**Read the error message literally, then walk the query steps from the bottom up.**

90% of "mystery" Power Query errors are one of:
1. A source schema changed (new/renamed/removed column)
2. A bad row entered the data (text in a number column, blank where date expected)
3. A sample file in a folder combine no longer matches production files
4. A hardcoded reference (column name, file path, sheet name) drifted

Do NOT start by opening source files. Start by reading the query steps.

---

## Step-by-Step Diagnostic Workflow

Always do these in order. Do not skip ahead.

1. **Read the full error message.** Note the error type (`Expression.Error`, `DataFormat.Error`, `DataSource.Error`, `Formula.Firewall`) and any column/value mentioned.
2. **Identify the failing step.** In the editor, the broken step is highlighted; the step *before* it is the last good state.
3. **Click the last good step.** Confirm the data looks right at that point. This tells you the failure is in the transition to the next step.
4. **Inspect the failing step in the formula bar.** Look at column names, hardcoded values, function arguments.
5. **Compare against the source.** Only now should you open the source file/database — and only to verify the specific thing the step expects.
6. **Fix at the right layer.** Cosmetic fixes (rename in step) are quick but fragile; structural fixes (update sample file, fix source) are durable.

---

## Error Catalogue: What It Means and How to Fix It

### `Expression.Error: The column 'X' of the table wasn't found.`

**Cause:** A step references a column name that no longer exists at that point in the query.

**Most common reasons:**
- Source file was modified (column renamed, removed, or reordered)
- A "Changed Type" step was auto-generated against an old schema and still hardcodes the old names
- An earlier "Removed Columns" or "Renamed Columns" step deleted/renamed the column the failing step is looking for
- A folder combine's sample file has different column names than the actual files

**Fix recipe:**
1. Click each prior step from top down — find the first step where column `X` exists.
2. If it never appears: the source no longer provides it. Either remove the downstream reference, or restore the column upstream.
3. If it appears then disappears: a step in between is dropping/renaming it. Edit that step.
4. If folder combine: fix the **sample file** in the helper queries (look in the Queries pane → "Transform Sample File" group), not the main query.

**Trap:** "Changed Type" steps reference *every* column by name. If a source column was renamed, edit the M code directly to update the column name in the `TransformColumnTypes` list — don't just delete and re-add the step (you'll lose all downstream type info).

---

### `Expression.Error: The column 'Column1' (or 'Column18') of the table wasn't found.`

**Cause:** A CSV or text file lost a column, and Power Query is now finding fewer columns than the schema expects. `Column1`/`Column18` are the default unnamed-column placeholders.

**Most common scenarios:**
- A blank trailing column in the source vanished
- Delimiter changed (comma → semicolon, tab → comma) so columns are merging
- Encoding mismatch is splitting columns wrong (UTF-8 vs Windows-1252)
- A header row was added or removed at the source

**Fix recipe:**
1. Look at the `Source` step — is the file size/structure roughly the same as before?
2. Click `Source` and inspect: how many columns are detected?
3. If wrong number → fix the `Csv.Document` call: check `Delimiter`, `Encoding`, `QuoteStyle`, `Columns` parameters.
4. If correct number but `Promoted Headers` step fails → the header row may have shifted up/down. Adjust `Table.Skip` before `Table.PromoteHeaders`.

```m
// Robust CSV source — explicit about everything
Source = Csv.Document(
    File.Contents("C:\Data\file.csv"),
    [Delimiter=",", Columns=12, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
),
PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
```

---

### `DataFormat.Error: We couldn't convert to Number/Date/etc.`

**Cause:** A value in a typed column can't be coerced to the target type.

**Most common reasons:**
- A blank cell appearing where a number is expected
- Text like "N/A", "-", or "TBD" in a numeric column
- Date column where some rows are `dd/mm/yyyy` and others are `mm/dd/yyyy` (locale drift)
- Currency symbol or thousand-separator embedded in number text
- Excel showing `#N/A` or `#REF!` that lands as text in the import

**Fix recipe:**
1. Click the step **before** the `Changed Type` step — find the row(s) the editor highlights with `Error` once the type is applied.
2. Decide your policy:
   - **Drop bad rows:** `Table.RemoveRowsWithErrors(prevStep, {"Amount"})`
   - **Replace with null:** add a `Replace Values` step before `Changed Type` to swap `"N/A"`, `"-"`, etc. with `null`
   - **Clean text first:** for numbers with symbols, `Text.Replace([Col], "$", "")` then `Text.Replace(_, ",", "")` before changing type
3. For dates with mixed locale, use explicit locale in `Table.TransformColumnTypes`:

```m
Table.TransformColumnTypes(prevStep, {{"OrderDate", type date}}, "en-AU")
```

---

### `Expression.Error: We cannot apply field access to the type Table/List/Record.`

**Cause:** You're using `[FieldName]` syntax on something that isn't a record — usually because an expansion step didn't run or returned a nested structure.

**Most common reasons:**
- `Table.ExpandTableColumn` was skipped — column still contains `[Table]` values
- A `Custom Column` returned a record/list instead of a scalar
- Lookup with `Table.NestedJoin` was not expanded after the join

**Fix recipe:**
1. Find the column the error references. Click a cell — does the preview show "Table" or "Record" or "List" instead of a scalar?
2. If yes: add an Expand step. Right-click the column header → Expand → tick the inner fields you want.
3. For `Custom Column` returning a record: wrap in `Record.Field([Col], "FieldName")` or change the expression to return a scalar directly.

---

### `Expression.Error: Token Eof / Token Then / Token Comma expected.`

**Cause:** M syntax error in the advanced editor or formula bar — usually a missing comma, unclosed bracket, or `if/then/else` without all three branches.

**Fix recipe:**
1. Open Advanced Editor (`View → Advanced Editor`).
2. M requires: every `let` step (except the last) ends with a comma. Every `if` needs `then` AND `else`. Brackets `[]`, braces `{}`, parens `()` must balance.
3. Power Query Editor highlights the offending character — start there, not at the top.

```m
// ✅ Correct
if [Status] = "Active" then 1 else 0

// ❌ Missing else — fails with "Token Else expected"
if [Status] = "Active" then 1
```

---

### `Formula.Firewall: Query 'X' references other queries or steps, so it may not directly access a data source.`

**Cause:** Power Query's privacy engine is blocking a query that combines two data sources with different privacy levels (or one set to "None").

**Fix recipe (in order of preference):**
1. **File → Options → Current File → Privacy → "Ignore the Privacy Levels"** — fastest fix for a single workbook/PBIX you trust.
2. **File → Options → Global → Privacy → "Always combine data according to your Privacy Level settings"** then set all sources to `Organizational` or `Public`.
3. **Refactor the query** so the dynamic source (e.g., a value used to parameterize a SQL/web call) is in the SAME query as the source call, not a separate query. The firewall fires when one query feeds parameters into another query's source.
4. **Convert helper query to a function** that takes its inputs as arguments — this lets Power Query reason about the data flow safely.

**Don't:** disable privacy globally on a shared machine without thinking. It's there because chaining a private source into a public web call could leak data.

---

### `DataSource.Error: The key didn't match any rows in the table.`

**Cause:** An `Excel.Workbook` or `Excel.CurrentWorkbook` reference is looking for a sheet/named range/table that has been renamed, deleted, or never existed.

**Fix recipe:**
1. The error message tells you the lookup key — e.g., `{[Item="Sheet1",Kind="Sheet"]}` or `{[Name="MyTable"]}`.
2. Open the source workbook and confirm: does that sheet/table exist with that exact name? Case-sensitive.
3. Fix the step's M code, or rename the sheet/table back in the source.

**Folder combine variant:** if the *sample file* in a folder combine has a table the others don't, the helper function will fail on every other file. Either standardize source files, or rebuild the combine off a representative sample.

---

### `Folder combine returns fewer rows than expected` (no error, but data missing)

**Cause:** Silent — usually a sample file mismatch, file filter, or a transformation in the helper function dropping rows.

**Diagnostic recipe:**
1. Open Queries pane → expand the `Transform Sample File` and helper function groups.
2. Click `Sample File`. Is it still pointing at a representative file?
3. Open `Transform Sample File`. Walk its steps — is one filtering rows in a way that's appropriate for the sample but wrong for production?
4. Back in the main query, check the `Filtered Hidden Files` step — is a folder/file name pattern excluding what you need?
5. Add a diagnostic column early: `Table.AddColumn(combinedStep, "SourceFile", each [Source.Name])` — then group by it to see row counts per file.

---

### `Refresh fails in Power BI Service but works in Desktop`

**Cause:** Service can't see the data source the way Desktop can.

**Top causes (check in order):**
1. **On-prem source, no gateway configured** — install/configure On-premises Data Gateway and map the data source in the Service.
2. **Credentials not set in Service** — Workspace → Settings → Datasets → Edit credentials for each source.
3. **Hardcoded local file path** like `C:\Users\Me\...` — Service has no access. Move file to SharePoint/OneDrive and use the Web/SharePoint connector.
4. **Dynamic data sources** — Service doesn't know which source to authenticate. Either set `RelativePath`/`Query` options to keep base URL static, or enable "Skip test connection" in dataset settings.
5. **Privacy level mismatch** — see Formula.Firewall above.

---

## Folder Combine Sample File Drift — The Most Common Production Bug

Folder combines memorize the structure of the first file they ever saw (the "sample file"). When later files differ, the combine either errors or silently drops columns.

**Symptoms:**
- "Column not found" only on certain files
- Row counts inconsistent with source folder size
- New columns added at source don't appear in output

**Permanent fix:**
1. Establish a **schema contract** — document expected column names, order, and types in a README in the source folder.
2. Add a **validation step** in the query that checks column count and names:

```m
ValidateSchema = if Table.ColumnCount(Expanded) <> 12
    then error "Schema drift: expected 12 columns, got " & Number.ToText(Table.ColumnCount(Expanded))
    else Expanded
```

3. For new columns you want to absorb gracefully, use `Table.ExpandTableColumn` with a dynamic column list:

```m
AllColumns = List.Distinct(List.Combine(List.Transform(Source[Content], each Table.ColumnNames(_)))),
Expanded = Table.ExpandTableColumn(Source, "Content", AllColumns)
```

---

## Inspection Order for "Column X not found" (cheat sheet)

Use this order — don't skip steps, don't go to source files first.

1. **Transform Sample File** query — is the sample file representative?
2. **Changed Type** steps — does column list match current source?
3. **Removed Columns** steps — was the missing column removed here?
4. **Expand Table Column** steps — is expected column list out of date?
5. **Renamed Columns** steps — was it renamed away?
6. **Source step** — has the file/folder/database actually lost the column? (Last resort.)

---

## Token & Performance Discipline

When debugging a broken query, do NOT:
- Open every file in the source folder before checking the query steps
- Run full data previews on multi-million row queries to "see what's there"
- Rebuild the query from scratch — you'll lose downstream logic and create new bugs

Do:
- Use the editor's row count indicator in the bottom-left as a sanity check
- Use `Table.FirstN(step, 100)` temporarily to test transformations on a sample
- Use `try ... otherwise ...` around suspect steps to catch and tag errors without halting the query

```m
SafeStep = Table.AddColumn(prevStep, "ParsedDate",
    each try Date.FromText([DateText]) otherwise null,
    type nullable date)
```

---

## Pre-Commit Checklist When Fixing a Broken Query

- [ ] Identified the root cause (don't just patch the symptom)
- [ ] If a schema changed, documented it in the query comments
- [ ] If a sample file was bad, replaced it with a known-good representative file
- [ ] Added error handling around the previously-failing step if appropriate
- [ ] Verified row count is consistent with expectations
- [ ] Tested refresh end-to-end (not just the editor preview)
- [ ] Recorded the fix in handover notes if it's a recurring source issue

---

## See Also

- `power-query-transformations.md` — building robust queries, query folding, folder connectors, incremental refresh
- `powerbi-model-editing.md` — model-side errors (relationships, DAX) that look like Power Query errors but aren't
- `excel-live-editing.md` — Excel-side equivalents (Get Data UI, refresh behaviour)
