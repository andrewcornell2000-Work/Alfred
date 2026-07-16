# MCP Routing — Avoid Overlap and Ping-Pong

Use this skill whenever an agent might pick the wrong MCP, retry across servers, or burn tokens on redundant tool calls.

## Golden rules

1. **Pick one primary path per task** — do not chain similar MCPs unless the first path explicitly failed for a documented reason.
2. **Never alternate Excel MCPs** — `excel` (excellm) and `excel-mcp` have opposite file-access rules; switching between them usually wastes turns.
3. **Cursor: native Read/Grep/Shell first** — for repo code. Do not route Alfred repo reads through the filesystem MCP.
4. **One web/doc path per question** — library docs → context7; live news/versions → parallel-search (Cursor) or Tavily (Alfred CLI); single URL → fetch (Personal/web bucket); local PDF/Office file → markitdown; interactive web UI → playwright (Personal/web bucket).
5. **Plan in native reasoning** — Alfred no longer ships sequential-thinking, memory, time, codegraph, sqlite, or lean-ctx MCPs.

## Active MCP stack (Work profile core set)

| Server | Use for |
|--------|---------|
| powerbi-modeling-mcp | Live Desktop semantic model / DAX |
| excel | Live **open** workbooks (excellm) |
| excel-mcp | **Closed** workbook / Power Query / COM batch |
| github | Remote GitHub API |
| context7 | Library/SDK docs |
| markitdown | Local file → markdown |
| filesystem | Finance OneDrive folder only |
| duckdb | SQL on CSV, Parquet, exports |
| parallel-search | Live web research (search + excerpts) |
| magic | UI component registry (mediagen) |
| outlook-calendar | Calendar (office365) |

Personal/web adds: playwright, fetch, firecrawl. Personal/cloud adds: supabase, vercel.

## Decision table

| Task | Use | Do NOT use |
|------|-----|------------|
| Read/search Alfred repo code | Native Read/Grep | filesystem MCP |
| Finance OneDrive files | filesystem MCP (finance path only) | Native Read for large OneDrive trees when filesystem is provisioned |
| Excel — workbook already open | `excel` (excellm) | excel-mcp |
| Excel — Power Query, closed file | excel-mcp | `excel` (excellm) |
| Excel — offline transform | pandas / openpyxl | Either Excel MCP |
| Power BI semantic model | powerbi-modeling-mcp | pbi-cli for model edits |
| Power BI report visuals | pbi-cli | powerbi-modeling-mcp |
| Library / SDK docs | context7 | parallel-search / fetch |
| Live web research | parallel-search | context7 |
| Local PDF / Office → markdown | markitdown | fetch |
| SQL on CSV / Parquet | duckdb | Spreadsheet MCPs for bulk analytics |

## Anti-patterns

- Installing the same server in Cursor *and* expecting Claude Desktop to share that process — each client starts its own copy.
- Leaving retired servers (`lean-ctx`, `ms-365`, …) in client configs — re-run provision; they are in `_retiredServers`.
