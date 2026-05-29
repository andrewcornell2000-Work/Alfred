# Recent Context
*Last updated: 2026-05-29*

- Weather query on 2026-05-28 still returned "web search isn't permitted" despite the Brave Search commit â€” Tavily `needs_search` gate is not consistently firing for GENERAL weather/current-event queries; needs investigation in `generate_general_response()`.
- `alfred_brain()` is intermittently returning `"claude"` as the provider token (seen in 2026-05-28 and 2026-05-29 autosave entries) instead of the expected `"claude_code"` or `"openai_mini"` â€” provider normalisation step is missing in `choose_provider()`.
- Python version query on 2026-05-28 was first misclassified as `CLAUDE_EXECUTION` (claude_code dispatched, returned a JSON error about no task), then re-entered and correctly handled as `GENERAL` via openai_mini â€” signals the Brain prompt needs a tighter boundary between factual lookups and execution tasks.
- Excel/Power Query request on 2026-05-29 routed correctly to `POWERBI/claude_code` but Claude responded with Alfred's own self-description instead of helping with the document â€” the scope prompt is injecting Alfred identity context rather than the user's task; `generate_claude_scope()` or the system prompt passed to `run_claude()` needs to be reviewed.
- No persistent MCP servers are installed; Alfred adds them on-demand per session via `claude mcp add` as documented in `requirements/mcp-tools.md`.
- Alfred confirmed operational on 2026-05-29 for basic GENERAL queries via the `"claude"` provider path.
- Next priorities: (1) fix provider normalisation for `"claude"` token, (2) fix POWERBI scope prompt leakage so Excel tasks actually execute, (3) ensure Tavily fires for weather/current-event GENERAL queries, (4) fix Codex TTY error, (5) wire QUANT routing to plugin API.