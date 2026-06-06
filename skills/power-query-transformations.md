# Power Query Data Transformations

**Source:** Microsoft Learn Power Query best practices (2025), community patterns from data teams building multi-file pipelines, incremental refresh workflows, and performance optimization guides.

---

## When This Skill Applies

Use this skill when building or maintaining Power Query transformations that:

- Combine data from multiple files or folders (folder connectors, append queries)
- Clean, reshape, or enrich raw data before loading to Excel or Power BI
- Need to perform efficiently at scale (query folding, step optimization, incremental refresh)
- Require error handling or conditional transformations
- Must be maintainable and auditable for other users

---

## Non-Negotiable Standards

### 1. Query folding awareness
Power Query only pushes filtering and column selection back to the data source if you write it correctly. **Breaking query folding** kills performance on large datasets.

**Folding-safe operations:**
- Filter rows (before any transformations)
- Select and remove columns
- Rename columns (if using built-in rename, not Text.Replace)
- Simple type conversions close to the source

**Folding-breaking operations:**
- Custom columns with M functions (use Add Column conditionally)
- Text.Replace, Text.Split, Table.NestedJoin done after filtering
- Unpivoting or pivoting transformations
- Grouping, rolling sums, or window functions

**How to test:** Right-click the query step → View Native Query. If you see SQL, folding is working. If you see nothing, it's broken.

```m
// ✅ GOOD — folding-safe, filter before transform
#"Source" = Excel.Workbook(File.Contents("data.xlsx"), null, true),
#"Sheet1_Sheet" = Source{[Item="Sheet1",Kind="Sheet"]}[Data],
#"Filtered Rows" = Table.SelectRows(#"Sheet1_Sheet", each [Status] = "Active"),  // folding works here
#"Removed Columns" = Table.RemoveColumns(#"Filtered Rows", {"TempField"}),        // folding works here
#"Changed Type" = Table.TransformColumnTypes(#"Removed Columns", ...)             // folding may work
in
#"Changed Type"

// ❌ BAD — broken folding, custom transform before filter
#"Added Custom" = Table.AddColumn(#"Source", "Length", each Text.Length([Name])),
#"Filtered Later" = Table.SelectRows(#"Added Custom", each [Status] = "Active")   // folding broken — too late
```

### 2. Folder connectors for multiple files
Use the Folder connector (Get Data → From File → From Folder) to combine CSV/Excel files. Structure matters:

**Requirements for folder combine:**
- All files have identical column names and order
- Files are in a single folder (PowerQuery cannot recurse subfolder trees natively)
- Sample file is named correctly (PowerQuery inspects the first file to infer schema)

**Pattern:**
```m
// Step 1: Connect to folder
#"Source" = Folder.Files("C:\Data\Exports"),

// Step 2: Add a column to track source file
#"Added Source" = Table.AddColumn(#"Source", "Source File", each [Name], type text),

// Step 3: Combine binary contents (Excel) or text (CSV)
#"Combined Data" = Table.CombineBuffersWithErrors(#"Added Source", "Content"),

// Step 4: Expand the table from the binary — this auto-detects schema from first file
#"Expanded Content" = Table.ExpandTableColumn(
    #"Combined Data",
    "Content",
    {"Column1", "Column2", "Column3"},  // column names inferred from sample
    {"Data_Column1", "Data_Column2", "Data_Column3"}
),

// Step 5: Filter and transform downstream
#"Filtered Rows" = Table.SelectRows(#"Expanded Content", each [Data_Column1] <> null),
#"Removed Columns" = Table.RemoveColumns(#"Filtered Rows", {"Source File"})  // keep source if needed for audit

in
#"Removed Columns"
```

**When folder combines fail:** usually the sample file differs from production files (extra columns, different names, new headers). Always version-control your folder contents or document the schema contract.

### 3. Error handling and tolerant transformations
Power Query fails loudly. For production pipelines, catch errors early:

```m
// Approach 1: Try-catch with fallback value
#"Safe Type Conversion" = Table.TransformColumns(
    #"Source",
    {
        {"Amount", each try Number.FromText(_) otherwise null},
        {"Date", each try Date.FromText(_) otherwise #date(2000, 1, 1)}
    }
),

// Approach 2: Catch expansion errors when combining folders
#"Expanded Rows" = Table.ExpandTableColumn(
    #"Source",
    "Details",
    {"SubField1", "SubField2"},
    {"Details_SubField1", "Details_SubField2"}  // uses same names if missing column
),

// Approach 3: Document assumptions, flag nulls
#"Added Flag" = Table.AddColumn(
    #"Source",
    "Data Quality",
    each if [Amount] = null then "MISSING" else if [Date] < #date(2000,1,1) then "INVALID" else "OK",
    type text
),

// Load with flag column for audit trail
#"Filtered Quality" = Table.SelectRows(#"Added Flag", each [Data Quality] = "OK" or [Data Quality] = "INVALID")
// ^ preserve invalid rows so finance can see what was excluded and why

in
#"Filtered Quality"
```

### 4. Incremental refresh setup (for Power BI)
Incremental refresh must preserve query folding. Structure your refresh parameters correctly:

```m
// Define refresh window in parameters (do NOT hardcode dates in the query)
#"RangeStart" = RangeStart,    // Power BI injects these parameters
#"RangeEnd" = RangeEnd,

#"Source" = Sql.Database("server.database.windows.net", "Database", 
    [Query = "SELECT * FROM [FactTable] WHERE [LoadDate] >= '" & 
             Date.ToText(#"RangeStart") & "' AND [LoadDate] < '" & 
             Date.ToText(#"RangeEnd") & "'"]),

// Remaining steps must preserve folding — no Custom Columns before this filter completes
#"Changed Type" = Table.TransformColumnTypes(#"Source", ...)

in
#"Changed Type"
```

**Rules for incremental refresh:**
- Use RangeStart and RangeEnd parameters (Power BI injected)
- Apply the date filter as close to the source as possible (in SQL, if using SQL connector)
- Keep transformations lightweight until after source filtering is done
- Test in Power BI → Data refresh settings → ensure "Query folding" checkbox appears
- If no "Query folding" checkbox, your query is broken for incremental refresh

### 5. Performance: steps to audit before loading
Run this checklist before publishing any query to production:

- [ ] View Native Query on final step → confirm SQL appears (folding working) or document why it's intentionally broken
- [ ] Remove all unused columns before final load (not after)
- [ ] Filter rows at source, not downstream
- [ ] No Custom Columns that could be a simple column reference
- [ ] No List.Generate or recursive loops in the query
- [ ] Table row count: load a small sample first (limit to 10K rows initially, verify shape, then remove limit)
- [ ] Column data types are final (avoid TransformColumnTypes multiple times)

Example audit query:
```m
// Count rows and columns as a quick sanity check
#"Check Dimensions" = #"Final Query",
#"Row Count" = Table.RowCount(#"Check Dimensions"),
#"Column Count" = Table.ColumnCount(#"Check Dimensions"),
#"Metadata" = 
    #table({"Rows", "Columns"}, {{#"Row Count", #"Column Count"}})
in
#"Metadata"  // load this first to validate shape before loading full data
```

---

## Common Transformation Patterns

### Pattern 1: Split date column into year-month components (for Power BI aggregate)

```m
#"Added Year" = Table.AddColumn(#"Source", "Year", each Date.Year([Date]), type number),
#"Added Month" = Table.AddColumn(#"Added Year", "Month", each Date.Month([Date]), type number),
#"Added Month Name" = Table.AddColumn(#"Added Month", "MonthName", 
    each Text.ProperCase(Date.ToText([Date], "MMMM")), type text),
#"Added Year-Month" = Table.AddColumn(#"Added Month Name", "YearMonth", 
    each Date.Year([Date]) * 100 + Date.Month([Date]), type number)  // 202501, 202502 for sorting
in
#"Added Year-Month"
```

**Why:** Power BI can't group by extracted dates dynamically. Pre-compute in Power Query, then create hierarchies in the data model.

---

### Pattern 2: Deduplicate on latest date per ID (e.g., most recent snapshot)

```m
#"Sorted by Date" = Table.Sort(#"Source", {{"EffectiveDate", Order.Descending}}),
#"Removed Duplicates" = Table.Distinct(#"Sorted by Date", {"ID"}),  // keeps first row after sort = latest date
#"Re-Sorted" = Table.Sort(#"Removed Duplicates", {{"ID", Order.Ascending}, {"EffectiveDate", Order.Descending}})
in
#"Re-Sorted"
```

**Why:** For operational snapshots (e.g., daily headcount extract), you want the latest record per employee, not all historical versions.

---

### Pattern 3: Rename columns programmatically (especially for folder combines)

```m
// After expanding folder combine, column names are [Data_Column1], [Data_Column2]...
// Rename to human-readable names

#"Renamed Columns" = Table.RenameColumns(#"Expanded Content", {
    {"Data_Column1", "EmployeeID"},
    {"Data_Column2", "FirstName"},
    {"Data_Column3", "LastName"},
    {"Data_Column4", "Department"},
    {"Data_Column5", "Salary"},
    {"Data_Column6", "LoadDate"}
})
in
#"Renamed Columns"
```

---

### Pattern 4: Text cleaning (remove spaces, trim, standardize case)

```m
#"Trimmed Text" = Table.TransformColumns(
    #"Source",
    {
        {"Name", Text.Trim, type text},
        {"Department", Text.Trim, type text},
        {"Email", Text.Lower, type text}
    }
),

#"Removed Extra Spaces" = Table.TransformColumns(
    #"Trimmed Text",
    {
        {"Name", each Text.Replace(_, "  ", " "), type text}  // double space to single
    }
),

// Flag suspicious values
#"Added Flags" = Table.AddColumn(#"Removed Extra Spaces", "Name_Quality", 
    each if Text.Length([Name]) < 3 then "TOO_SHORT" 
         else if Text.Contains([Name], "test", Comparer.OrdinalIgnoreCase) then "LIKELY_TEST" 
         else "OK", 
    type text)
in
#"Added Flags"
```

---

### Pattern 5: Unpivot and re-pivot (reshape transposed data)

```m
// If data comes in wide format (months across columns), reshape to long
#"Unpivoted Columns" = Table.Unpivot(
    #"Source",
    {"Jan", "Feb", "Mar", "Apr", "May"},  // column names to unpivot
    "Month",      // new column name for pivot headers
    "Amount"      // new column name for values
),

#"Mapped Month Names" = Table.AddColumn(#"Unpivoted Columns", "MonthNumber",
    each if [Month] = "Jan" then 1 
         else if [Month] = "Feb" then 2 
         else 3,  // etc.
    type number),

#"Final Reshape" = Table.RemoveColumns(#"Mapped Month Names", {"Month"})
in
#"Final Reshape"
```

---

## Debugging Workflow

**Problem: Query times out or takes > 1 minute**

1. Right-click each step, select "Delete until here" to isolate the slow step
2. If it's a Folder.Files() combine, check the folder size → consider pre-filtering before combine
3. If it's a database query, View Native Query → run that SQL in the database directly to confirm it's fast
4. If it's a Custom Column with List operations, replace with Table functions (faster)
5. Consider splitting into multiple smaller queries instead of one mega-query

**Problem: "Column not found" after connecting to a new data source**

1. Check Source step → is it still pointing to the right file/folder?
2. Does the sample file (folder combines) match production schema?
3. Expanded table step → do the column names match what's in the source?
4. If using a SQL connector, verify the table name and column list are correct in the SQL statement

**Problem: "Unexpected format" errors when expanding CSV**

1. Folder connector treating CSV as binary — need to parse as Text first
2. Use Csv.Document(Content, [Delimiter=",", Encoding=1252]) before expanding

---

## Tools

| Task | Tool | Notes |
|------|------|-------|
| Build and test queries | Power BI Desktop (free) or Excel Power Query | Desktop better for DAX and larger datasets |
| Schedule refreshes | Power BI Service, Fabric Dataflow Gen 2 | Gen 2 has better error handling and logging |
| Monitor refresh failures | Power BI Service → Datasets → Refresh history | Scroll to see error messages |
| Optimize incremental refresh | `pbi-cli` / Power BI REST API | Check refresh window settings |

---

## Checklist Before Publishing

- [ ] All column names are human-readable and documented
- [ ] Row count is accurate (spot-check with source)
- [ ] Data types are set explicitly (no "any" type in final step)
- [ ] null values are handled (either removed or flagged)
- [ ] Source schema changes are documented (e.g., "EffectiveDate added in June 2025")
- [ ] Folder combines have a documented column order contract
- [ ] Incremental refresh (if used) has RangeStart/RangeEnd parameters and preserves folding
- [ ] Query folding is verified (View Native Query shows SQL or error is documented)
- [ ] No hardcoded file paths (use parameters for reusability)
- [ ] Error rows are either removed or have a flag column for audit

