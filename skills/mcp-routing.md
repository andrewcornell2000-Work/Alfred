# MCP Routing — Avoid Overlap and Ping-Pong

Use this skill whenever an agent might pick the wrong MCP, retry across servers, or burn tokens on redundant tool calls.

## Golden rules

1. **Pick one primary path per task** — do not chain similar MCPs unless the first path explicitly failed for a documented reason.
2. **Never alternate Excel MCPs** — `excel` (excellm) and `excel-mcp` have opposite file-access rules; switching between them usually wastes turns.
3. **Cursor: native Read/Grep/Shell first** — lean-ctx is optional for large files, re-reads, or compressed shell. If lean-ctx MCP hangs (>5s) or errors, fall back to native tools immediately.
4. **LeanCTX for session memory and heavy reads** — use `ctx_knowledge`, `ctx_read` map mode, `ctx_search`; do not also read the same file via filesystem MCP.
5. **One web/doc path per question** — library docs → context7; live news/versions → parallel-search or Tavily (Alfred CLI); single URL → fetch; local PDF/Office file → markitdown; interactive web UI → playwright.
6. **Plan in native reasoning** — Alfred no longer ships sequential-thinking, memory, time, codegraph, or sqlite MCPs.

## Active MCP stack (16 + LeanCTX)

Core 10 + optional 6 (auto-skipped when keys/commands missing):

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
| parallel-search | Citation-backed web search (Cursor) |
| firecrawl | Crawl/scrape/deep research (needs key) |
| fal-ai | Image/video/audio generation (needs key) |
| magic | Magic UI React components |
| longhand | Claude session history recall |
| outlook-calendar | Local Outlook calendar (Windows) |
| lean-ctx | Optional: large reads, compressed shell, session memory |

## Decision table

| Task | Use | Do NOT use |
|------|-----|------------|
| Read/search Alfred repo code | Native Read/Grep (Cursor) or LeanCTX for large files | filesystem, double-read via MCP + native |
| Finance OneDrive files | filesystem MCP (finance path only) | LeanCTX (repo-oriented) |
| Excel — workbook already open | `excel` (excellm) | excel-mcp |
| Excel — Power Query, closed file | excel-mcp | `excel` (excellm) |
| Excel — offline transform | pandas / openpyxl | Either Excel MCP |
| Power BI semantic model | powerbi-modeling-mcp | pbi-cli |
| Power BI report visuals | pbi-cli | powerbi-modeling-mcp |
| Library/framework API docs | context7 | fetch, Tavily |
| Live web search (Cursor) | parallel-search | fetch, context7, firecrawl |
| Live web search (Alfred CLI) | Tavily via Alfred | fetch, context7 |
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

Alfred ships **16 domain MCPs + LeanCTX** (optional). Prefer one tool from the table above — do not probe multiple servers for the same task.

## When a tool fails

1. Read the error — access denied vs missing prereq vs wrong MCP.
2. Fix the prereq (open/close workbook, `pbi connect`, add `.env` key).
3. Switch MCP only if the decision table says a **different** primary path applies.
