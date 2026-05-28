# Recent Context
*Last updated: 2026-05-28*

- Brave Search was added to Alfred general chat responses (commit ba78993), enabling live web results for GENERAL-category queries â€” earlier in this session a weather query failed with "web search not permitted," which this commit resolves.
- Security hardening committed: private/credential files untracked from git repository, and API token input is now masked in the terminal (commit c4bd590).
- Publish Update flow migrated from gh CLI to GitHub REST API directly (commit 51fc412), removing the gh CLI dependency from that path.
- Alfred installer rebuilt and PyInstaller root path for MCP config fixed (commits 98d1e3b, c05c922), resolving packaged-app MCP configuration resolution.
- Codex invocation still failing with `Error: stdout is not a terminal` on all headless `use codex` and `CLAUDE_EXECUTION â†’ codex` paths â€” PTY wrapper or alternative invocation needed.
- QUANT-classified tasks still routing to `openai_mini` instead of the Quant plugin API â€” this dispatch path remains unconnected.
- Alfred confirmed operational on 2026-05-28; general queries (online check, Claude 4 capabilities) responded correctly via openai_mini.
- Next priorities: fix Codex TTY error, wire QUANT routing to the plugin API, and consider upgrading scope generation to Claude Sonnet/Haiku with prompt caching.