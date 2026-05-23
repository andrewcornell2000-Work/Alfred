\# Power Query Column Errors



\## Purpose

Diagnose Power Query errors where columns are missing, renamed, or removed unexpectedly.



\## Common Errors

\- Column not found

\- Column18 not found

\- Expression.Error: The column 'X' of the table wasn't found

\- Expanded column missing

\- Changed Type references missing column



\## Inspection Order

1\. Transform Sample File query

2\. Changed Type steps

3\. Removed Columns steps

4\. Expanded Table Column steps

5\. Renamed Columns steps

6\. Source file headers only if query logic does not explain the issue



\## Important Rules

\- Do not scan all source files immediately

\- Prefer query-step diagnosis before file inspection

\- Avoid broad folder scans unless necessary

\- Stop after identifying root cause unless fixes are requested



\## Common Root Causes

\- Source schema changed

\- Sample file differs from production files

\- Removed columns step references deleted column

\- Expanded table step expecting outdated schema

\- Changed Type auto-generated against old schema

\- Folder combine function cached old headers



\## Token Optimization

\- Inspect metadata and query steps first

\- Only inspect actual source files when query logic is inconclusive

\- Avoid full data previews unless required

