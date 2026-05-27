# Recent Context
*Last updated: 2026-05-27*

- Codex invocation is failing with `Error: stdout is not a terminal` when called headlessly via subprocess â€” affects all `use codex` and `CLAUDE_EXECUTION â†’ codex` paths; needs a PTY wrapper or alternative invocation flag.
- QUANT-classified tasks are routing to `openai_mini` instead of the Quant plugin API, indicating the QUANT dispatch path is not wired up yet â€” high-priority gap to close.
- Fixed SSL certificate error for the corporate Maersk network environment, unblocking Alfred on managed machines.
- Added no-admin install support (`winget --scope user`, portable Node.js, user-scope Python) so Alfred can be set up without elevated privileges.
- Fixed Claude CLI login flow and added Claude API fallback so Alfred remains functional when OpenAI is unavailable.
- Hardened `detect_provider_override()` parsing so explicit `use claude` / `use codex` phrases reliably bypass keyword scoring.
- Next priorities: fix Codex TTY error, connect QUANT routing to the plugin API, and verify end-to-end Claude fallback behavior.