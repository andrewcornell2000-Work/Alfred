# Recent Context
*Last updated: 2026-06-01*

- POWERBI connection workflow tested successfully on 2026-06-01 with "zac dash" PBIX file; multi-step execution (3–4 steps) completed without scope leakage issues previously observed on 2026-05-29.
- MCP tools confirmed pre-installed and operational; Alfred directly connected to open PBIX and enumerated tables/queries without requiring manual MCP server setup.
- User granted full PC access permission on 2026-06-01 10:10:33; Alfred acknowledged and confirmed permission to read, write, and modify files anywhere on the system.
- GENERAL/claude provider path confirmed operational for basic queries and permissions discussion.
- Outstanding bugs remain: (1) `"claude"` provider token normalisation, (2) Tavily `needs_search` gate for weather/current-event GENERAL queries, (3) Codex TTY error, (4) QUANT routing to plugin API.
- POWERBI scope leakage issue may have self-resolved; latest multi-step executions (2026-06-01 09:57–10:13) show correct task execution against user documents rather than Alfred self-description.
- Next priorities: validate POWERBI scope fix is consistent, resolve provider normalisation, enable Tavily for GENERAL weather queries, fix Codex TTY, wire QUANT routing.