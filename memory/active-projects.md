# Active Projects
*Backlog for the growth loop. Pick the top undone item that matches the run's mission type.*
*Last updated: 2026-06-10*

## DONE
- [x] markitdown MCP — added to cursor/mcp.json template + registered for Claude & Codex (2026-06-10)

## MCP CATALOG — port proven servers into the portable template (cursor/mcp.json)
These already work in Andrew's local setup but are MISSING from the distributable template,
so teammates don't get them. Add each to cursor/mcp.json (with the right guard / ${env:VAR}),
then a short how-to skill. One per run.
- [ ] filesystem  — npx @modelcontextprotocol/server-filesystem (args: ${financeDir} ${repoRoot})
- [ ] memory      — npx @modelcontextprotocol/server-memory (env MEMORY_FILE_PATH=${memoryDir}\mcp-knowledge-graph.json)
- [ ] sequential-thinking — npx @modelcontextprotocol/server-sequential-thinking
- [ ] fetch       — uvx mcp-server-fetch (_requiresCommand uvx)
- [ ] time        — uvx mcp-server-time (_requiresCommand uvx)
- [ ] sqlite      — npx @modelcontextprotocol/server-sqlite (args: --db-path ${dataDir}\alfred.db)
- [ ] duckdb      — npx @ktanaka101/mcp-server-duckdb (args: --db-path ${dataDir}\analytics.duckdb)

## NEW MCP CANDIDATES — research, then add to template if genuinely useful
- [ ] A PDF/document extraction MCP beyond markitdown (e.g. a table-aware extractor)
- [ ] An MCP for SharePoint / Microsoft Graph file access (finance team uses SharePoint)
- [ ] A web-research MCP (compare to existing Tavily direct integration before adding)

## TOOL HOW-TO SKILLS — write/deepen
- [ ] markitdown skill: how to convert PDFs/Office/images to Markdown, with example prompts
- [ ] GitHub MCP skill: common PR / issue / code-search workflows + gotchas
- [ ] Codex vs Claude routing: when each is the right tool

## NOTES FOR THE LOOP
- Adding a server to cursor/mcp.json is SAFE: it installs nothing on the machine; it becomes active
  for Claude + Codex + Cursor only when Andrew runs Provision-Cursor.ps1.
- Never write secrets — use "${env:VAR}" + "_requires".
- The cloud loop cannot touch Andrew's Windows machine; it improves the repo/template only.
