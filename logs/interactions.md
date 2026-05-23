
## 2026-05-23 14:08:24
**Category:** POWERBI
**Input:** ï»¿My Power BI report shows a column missing error in the sales query
**Scope:** 1. Likely issue: A Power Query step in the sales query references a column that is missing, removed, renamed, or not present in the expected schema.

2. First inspection target: The Transform Sample File query associated with the sales query to check if the missing column is present or manipulated early in the query pipeline.

3. Forbidden scope: Do not scan all source files or unrelated queries; avoid inspecting all file contents before confirming query logic issues.

4. Optimized Claude prompt
