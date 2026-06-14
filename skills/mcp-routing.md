# MCP Routing — Avoid Overlap and Ping-Pong

Use this skill whenever an agent might pick the wrong MCP, retry across servers, or burn tokens on redundant tool calls.

## Golden rules

1. **Pick one primary path per task** — do not chain similar MCPs unless the first path explicitly failed for a documented reason.
2. **Never alternate Excel MCPs** — `excel` (excellm) and `excel-mcp` have opposite file-access rules; switching between them usually wastes turns.
3. **LeanCTX owns repo reads and session memory** — use `ctx_read` / `ctx_search` / `ctx_knowledge`; do not also read the same file via filesystem MCP.
4. **One web/doc path per question** — library docs → context7; live news/versions → Tavily (Alfred); single URL → fetch; local PDF/Office file → markitdown; interactive web UI → playwright.
5. **Plan in native reasoning** — Alfred no longer ships sequential-thinking, memory, time, codegraph, or sqlite MCPs.

## Active MCP stack (10 + LeanCTX)

| Server | Use for |
|--------|---------|
| powerbi-modeling-mcp | Live Desktop semantic model / DAX |
| excel | Live **open** workbooks (excellm) |
| excel-mcp | **Closed** workbook / Power Query / COM batch |
| github | Remote GitHub API |
| playwright | Browser automation |
| context7 | Library/SDK docs |
| markitdown | Local file → markdown |
| fetch | Single known URL → markdown |
| filesystem | Finance OneDrive folder only |
| duckdb | SQL on CSV, Parquet, exports |
| lean-ctx | Repo code, compressed shell, session memory |

## Decision table

| Task | Use | Do NOT use |
|------|-----|------------|
| Read/search Alfred repo code | LeanCTX `ctx_read`, `ctx_search` | filesystem, raw Read/Grep when LeanCTX is available |
| Finance OneDrive files | filesystem MCP (finance path only) | LeanCTX (repo-oriented) |
| Excel — workbook already open | `excel` (excellm) | excel-mcp |
| Excel — Power Query, closed file | excel-mcp | `excel` (excellm) |
| Excel — offline transform | pandas / openpyxl | Either Excel MCP |
| Power BI semantic model | powerbi-modeling-mcp | pbi-cli |
| Power BI report visuals | pbi-cli | powerbi-modeling-mcp |
| Library/framework API docs | context7 | fetch, Tavily |
| Live web search | Tavily via Alfred | fetch, context7 |
| Single URL to markdown | fetch | playwright (unless JS/login needed) |
| Local PDF/Word/PPT | markitdown | fetch |
| Browser automation | playwright | fetch |
| GitHub PRs/issues | github MCP | filesystem |
| Local git in repo | bash git or LeanCTX shell | github MCP |
| Cross-session facts / handoffs | LeanCTX `ctx_knowledge` | (memory MCP retired) |
| Ad-hoc SQL on CSV/Parquet | duckdb MCP | Excel MCP |
| Token-efficient shell | LeanCTX `ctx_shell` | filesystem |

## Excel MCP — stop ping-pong

| | `excel` (excellm) | excel-mcp |
|---|-------------------|-----------|
| Workbook state | Must be **open** in Excel | Must be **closed** (exclusive COM lock) |
| Best for | Live edits while user watches | Power Query, M steps, deep structure, VBA |
| On COM/access error | Ask user to close or open workbook — **do not silently switch MCP** |

## Web & docs — stop triple-fetch

```
Library API question     → context7 only
"Latest news/version"    → Tavily (Alfred) only
Local PDF on disk        → markitdown only
Known article URL        → fetch once (paginate if truncated)
Interactive web page     → playwright only
```

## Context cost

Alfred ships **10 domain MCPs + LeanCTX**. Prefer one tool from the table above — do not probe multiple servers for the same task.

## When a tool fails

1. Read the error — access denied vs missing prereq vs wrong MCP.
2. Fix the prereq (open/close workbook, `pbi connect`, add `.env` key).
3. Switch MCP only if the decision table says a **different** primary path applies.
