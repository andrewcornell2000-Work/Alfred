# MCP Tools

Documents MCP (Model Context Protocol) server tools used or evaluated for Alfred.
Alfred provisions a **lean stack** via `cursor/mcp.json` and `Provision-Cursor.ps1`.

## Routing (avoid overlap)

See **`.cursor/rules/00-agent-tooling.mdc`** (and `cursor/rules/00-agent-tooling.mdc`) — decision table, Excel anti-ping-pong rules, and one-primary-path doctrine.

## Currently Configured (cursor/mcp.json)

**10 domain MCPs**. Tavily web search is optional via `TAVILY_API_KEY` in `.env` (not provisioned as an MCP).

| Server | Role |
|--------|------|
| powerbi-modeling-mcp | Live Desktop semantic model |
| excel | Live **open** workbooks (excellm) |
| excel-mcp | **Closed** workbook / Power Query / COM batch |
| github | Remote GitHub API |
| playwright | Browser automation |
| parallel-search | Web search + page fetching (opt-in `web` bucket) |
| context7 | Library/SDK docs |
| markitdown | Local file → markdown |
| fetch | Single URL → markdown |
| filesystem | Finance OneDrive folder **only** |
| duckdb | SQL on CSV/Parquet/exports |
| supabase | Supabase project — SQL, migrations, edge functions (Cursor OAuth) |
| vercel | Vercel deployments, logs, docs (Cursor OAuth) |

### Retired (removed from template — Provision-Cursor strips from machine configs)

| Server | Why removed |
|--------|-------------|
| sequential-thinking | Inflated responses with multi-step planning loops |
| memory | Low value vs native notes / project docs |
| time | Low value; native reasoning suffices |
| codegraph | Prefer graphify (local AST graph) + native Grep |
| sqlite | Overlapped duckdb for analytics workloads |
| outlook-calendar | Removed from catalog |

**Not in template:** `ms365` (needs Graph key), `git` (overlaps bash git + github MCP).

### powerbi-modeling-mcp
- **Source:** VS Code extension `analysis-services.powerbi-modeling-mcp` (Microsoft Analysis Services)
- **Command:** `<extension-path>\server\powerbi-modeling-mcp.exe --start`
- **Purpose:** Read and edit Power BI data models — measures, columns, tables, relationships, hierarchies, calculation groups
- **Trust:** official (Microsoft)
- **Destructive:** true (can modify live Power BI models — see `requirements/safety-gates.md`)
- **Install:** Install VS Code extension `analysis-services.powerbi-modeling-mcp` — Alfred installer auto-detects the path

### excel
- **Source:** pip package `excellm`
- **Command:** `python -m excellm`
- **Purpose:** Read and write live open Excel workbooks — cells, ranges, formatting, charts, pivot tables, VBA
- **Trust:** official
- **Destructive:** true (can write to open workbooks)
- **Install:** `pip install excellm` - Alfred installer handles this automatically

### excel-mcp
- **Source:** GitHub release `sbroenne/mcp-server-excel` → `Alfred\bin\excel-mcp\mcp-excel.exe`
- **Purpose:** Closed-workbook COM automation — Power Query, M code, VBA, pivots (exclusive access)
- **Trust:** community
- **Destructive:** true
- **Install:** `setup.ps1` downloads the self-contained exe

### github
- **Source:** Official [github/github-mcp-server](https://github.com/github/github-mcp-server) (`ghcr.io/github/github-mcp-server`)
- **Command:** `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server`
- **Fallback (no Docker):** `npx -y @modelcontextprotocol/server-github` (deprecated but still works)
- **Purpose:** GitHub operations - PRs, issues, repo search, file operations, diffs
- **Trust:** official
- **Destructive:** true
- **Requires:** `GITHUB_PERSONAL_ACCESS_TOKEN`

### playwright
- **Source:** npm package `@playwright/mcp`
- **Command:** `npx -y @playwright/mcp --browser chromium`
- **Purpose:** Browser automation - navigate pages, fill forms, scrape data, take screenshots
- **Trust:** official
- **Destructive:** false

### parallel-search
- **Source:** [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp)
- **Command:** `npx -y mcp-remote@latest https://search.parallel.ai/mcp`
- **Purpose:** Search the live web with `web_search`, then read selected pages with `web_fetch`
- **Bucket:** `web` (excluded from the work profile's `core,powerbi,data` selection)
- **Requires:** Node.js/npm (`npx`), installed by Alfred setup; no Parallel account or API key
- **Destructive:** false (read-only search and page extraction)

To add web research to a work-profile install, run this from the Alfred repository
root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -Buckets "core,powerbi,data,web"
```

`-Buckets` replaces and saves the machine's bucket selection in Alfred `.env` as
`ALFRED_BUCKETS`. Keep any other buckets you already use in that list. This enables
the entire `web` bucket, including Playwright and fetch (and Firecrawl when its key
is set), plus the corresponding skills. Alfred registers the catalog's
`parallel-search` entry independently in Cursor, Claude Code, and Codex; do not add
a second copy at project scope.

After provisioning, restart your host and check its MCP connection:

- **Cursor:** find `parallel-search` in Settings → Tools & MCP and check its tools.
- **Claude Code:** run `claude mcp get parallel-search`, or inspect `/mcp` in a session.
- **Codex:** run `codex mcp list`, then inspect `/mcp` in a session.

The server exposes two separate tools, `web_search` and `web_fetch` (the host may
prefix their names). Try asking:

> Use parallel-search to find the official Python 3.14 release announcement, then
> fetch that page and report its release date with the source URL.

Anonymous search uses Fast mode. Free access has rate limits; if a call is limited,
wait before retrying. For library/SDK syntax use context7, and for interactive
browser work use Playwright, following the routing table above.

**Authentication:** Alfred's current catalog entry connects anonymously. Setting
`PARALLEL_API_KEY` in Alfred `.env` or the machine environment alone does not
authenticate it: the entry does not forward an `Authorization` header. Higher
limits require an authenticated connection; see the [Parallel authentication
options](https://docs.parallel.ai/integrations/mcp/search-mcp#installation).

### context7
- **Source:** npm `@upstash/context7-mcp`
- **Purpose:** Version-specific library/SDK documentation
- **Trust:** official
- **Destructive:** false

### markitdown
- **Source:** uvx `markitdown-mcp`
- **Purpose:** Local PDF/Office/image → markdown
- **Trust:** official (Microsoft)
- **Destructive:** false

### fetch
- **Source:** uvx `mcp-server-fetch`
- **Purpose:** Single URL → markdown
- **Trust:** official
- **Destructive:** false

### filesystem
- **Install:** `npx -y @modelcontextprotocol/server-filesystem <finance-dir>`
- **Purpose:** Scoped finance OneDrive access — **not** Alfred repo code (use native Read/Grep there)
- **Trust:** official
- **Destructive:** true

### duckdb
- **Source:** uvx `mcp-server-duckdb`
- **Purpose:** Fast SQL on CSV, Parquet, Excel exports
- **Trust:** community
- **Destructive:** false

### supabase
- **Source:** Remote MCP `https://mcp.supabase.com/mcp?project_ref=...`
- **Purpose:** Supabase project management — SQL, migrations, edge functions, advisors, logs
- **Trust:** official
- **Destructive:** true (schema changes, migrations)
- **Requires:** `SUPABASE_PROJECT_REF` in Alfred `.env`
- **Auth:** OAuth in Cursor on first use
- **Also install:** `npx skills add supabase/agent-skills` (Provision-Cursor.ps1)
- **Skill:** `skills/supabase.md`
- **Note:** Set `SUPABASE_DATABASE_URL` in `.env` for direct Postgres access in apps. Provisions to Cursor, Claude Code, and Codex via HTTP transport.

### vercel
- **Source:** Remote MCP `https://mcp.vercel.com`
- **Purpose:** Deployments, projects, build/runtime logs, Vercel docs search
- **Trust:** official
- **Destructive:** true (deploy actions)
- **Auth:** OAuth in Cursor on first use
- **Also install:** `npx plugins add vercel/vercel-plugin` (Provision-Cursor.ps1)
- **Skill:** `skills/vercel.md`
- **Docs:** https://vercel.com/docs/agent-resources/vercel-plugin
- **Note:** Provisions to Cursor, Claude Code, and Codex via HTTP transport. Plugin adds skills, specialist agents, and slash commands.

### Web search (Tavily — optional, not an MCP)
- **Source:** Optional `TAVILY_API_KEY` in Alfred `.env` (not provisioned via `cursor/mcp.json`)
- **Requires:** `TAVILY_API_KEY` in Alfred `.env`
- **Purpose:** Live web search for latest docs, versions, news, and current public information
- **Skill:** `skills/web-search.md`

---

## Learning Mode: Adding MCP Tools

When Alfred encounters or learns about a new MCP server during a session:

1. **Check overlap first** — read `00-agent-tooling` rule; do not add redundant servers.
2. **Add an entry** in the Candidate Tools section below.
3. **Update `alfred-tools.json`** — add the tool to the `mcp.tools` array.
4. **Update install manifests** if a persistent install step is needed.
5. **Update `README.md`** if the tool changes the user-facing setup flow.
6. **Commit all manifest changes before the session ends.**

### Hard Rules

- Never store MCP server credentials, tokens, or API keys in this file or any manifest.
- Tools marked `destructive: true` must be documented in `requirements/safety-gates.md` and skill safety notes before they are provisioned.
- Never auto-pull from GitHub or auto-install tools without explicit user approval.

---

## Candidate Tools

Candidate tools must pass an overlap review before joining `cursor/mcp.json`.
