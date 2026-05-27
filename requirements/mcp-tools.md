# MCP Tools

Documents MCP (Model Context Protocol) server tools used or evaluated for Alfred.
Alfred uses Claude Code's built-in MCP runtime; MCP servers are configured per-session
via `claude mcp add` rather than being hard-installed globally.

## Currently Configured

### powerbi-modeling-mcp
- **Source:** VS Code extension `analysis-services.powerbi-modeling-mcp` (Microsoft Analysis Services)
- **Command:** `<extension-path>\server\powerbi-modeling-mcp.exe --start`
- **Purpose:** Read and edit Power BI data models — measures, columns, tables, relationships, hierarchies, calculation groups
- **Trust:** official (Microsoft)
- **Destructive:** true (can modify live Power BI models — represented in Alfred's DANGEROUS_KEYWORDS gate)
- **Install:** Install VS Code extension `analysis-services.powerbi-modeling-mcp` — Alfred installer auto-detects the path

### excel
- **Source:** pip package `excellm`
- **Command:** `python -m excellm`
- **Purpose:** Read and write live open Excel workbooks — cells, ranges, formatting, charts, pivot tables, VBA
- **Trust:** official
- **Destructive:** true (can write to open workbooks)
- **Install:** `pip install excellm` - Alfred installer handles this automatically

### brave-search
- **Source:** npm package `@modelcontextprotocol/server-brave-search`
- **Command:** `npx -y @modelcontextprotocol/server-brave-search`
- **Purpose:** Live web search for latest docs, current versions, news, and current public information
- **Trust:** official
- **Destructive:** false
- **Requires:** `BRAVE_API_KEY`

### github
- **Source:** npm package `@modelcontextprotocol/server-github`
- **Command:** `npx -y @modelcontextprotocol/server-github`
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

---

## Control Tower MCP Stack

These are the next first-class MCP capabilities Alfred should grow into. They are tracked in
`requirements/alfred-tools.json` as planned tools until the installer safely configures them.

### filesystem
- **Install:** `npx -y @modelcontextprotocol/server-filesystem <allowed-dir>`
- **Purpose:** Scoped local file access for PC operator workflows
- **Trust:** official
- **Destructive:** true
- **Safety:** Must always use explicit allowed directories. Never grant the whole home directory by default.

### memory
- **Install:** `npx -y @modelcontextprotocol/server-memory`
- **Purpose:** Persistent knowledge graph memory across Alfred sessions and projects
- **Trust:** official
- **Destructive:** true
- **Safety:** Store memory under Alfred-controlled paths and never commit secrets.

### fetch
- **Install:** `uvx mcp-server-fetch`
- **Purpose:** Clean web page fetching and HTML-to-Markdown conversion for docs and research
- **Trust:** official
- **Destructive:** false

### git
- **Install:** `uvx mcp-server-git`
- **Purpose:** Local repository inspection, history, diffs, and git operations
- **Trust:** official
- **Destructive:** true
- **Safety:** Mutating git operations remain behind Alfred's dispatch safety gates.

### sequential-thinking
- **Install:** `npx -y @modelcontextprotocol/server-sequential-thinking`
- **Purpose:** Structured multi-step reasoning for complex Office, BI, and PC operator tasks
- **Trust:** official
- **Destructive:** false

### time
- **Install:** `uvx mcp-server-time`
- **Purpose:** Time and timezone conversion for scheduling and automation context
- **Trust:** official
- **Destructive:** false

## Learning Mode: Adding MCP Tools

When Alfred encounters or learns about a new MCP server during a session:

1. **Add an entry** in the [Candidate Tools](#candidate-tools) section below with:
   - Install command (npm package, pip package, or Docker image)
   - Purpose and which Alfred routing category it serves
   - Trust level: `official` | `community` | `experimental`
   - Whether it has destructive capabilities (`destructive: true/false`)

2. **Update `alfred-tools.json`** — add the tool to the `mcp.tools` array.

3. **Update install manifests** if a persistent install step is needed:
   - npm package → add to `requirements/npm-tools.txt` and `alfred-tools.json`
   - pip package → add to `requirements/python-requirements.txt` and `alfred-tools.json`

4. **Update `setup.ps1`** only if a new install step is needed that the manifest loop
   does not already handle automatically.

5. **Update `README.md`** if the tool changes the user-facing setup flow (e.g. new
   login step, new API key).

6. **Commit all manifest changes before the session ends.**

### Hard Rules

- Never store MCP server credentials, tokens, or API keys in this file or any manifest.
- Tools marked `destructive: true` must be represented in Alfred's safety gate in
  `backend/main.py` (`DANGEROUS_KEYWORDS` and dispatch checks) before they are
  allowed to dispatch.
- Never auto-pull from GitHub or auto-install tools without explicit user approval.
  The update flow in `check-updates.ps1` always prompts first.

---

## Candidate Tools

Candidate tools now graduate into the Control Tower MCP Stack above before installer automation is added.

<!--
Example entry format:

### mcp-server-filesystem
- **Install:** `npm install -g @modelcontextprotocol/server-filesystem`
- **Command:** `mcp-server-filesystem`
- **Purpose:** Gives Claude Code scoped read/write access to local directories
- **Trust:** official
- **Destructive:** true (can write/delete files - represent in `DANGEROUS_KEYWORDS` and dispatch checks)
- **Notes:** Requires explicit directory allow-list at runtime via --allowed-dir flag
-->
