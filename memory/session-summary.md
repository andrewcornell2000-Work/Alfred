# Alfred Session Summary  
*Last updated: 2026-05-28*

## Current Architecture

- **Entry point:** `backend/main.py` (all logic consolidated in one file)  
- **API clients:** `openai_client` (GPT-4.1-mini, actively used) + `anthropic_client` (Anthropic SDK present but unused for inference); Claude fallback active when OpenAI is unavailable  
- **Brave Search:** Integrated for GENERAL category responses, providing live web search results  
- **Claude execution:** Headless Claude Code CLI via `subprocess.run(["claude", "-p", prompt])`  
- **Codex execution:** Headless Codex CLI via subprocess; currently fails with "stdout is not a terminal" in non-TTY environments  
- **Terminal UI:** Utilizes `rich.console.Console` for user interaction; API token input is masked  
- **Environment:** `.env` file manages `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`; virtual environment `.venv` used; private/credential files untracked from git  
- **Skill files:** Markdown files in `skills/` folder, auto-loaded by filename and first-line title keyword matching  
- **SSL handling:** Corporate Maersk network SSL cert error patched in setup/invocation path  
- **Install paths:** No-admin install support added (`winget --scope user`, portable Node.js, user-scope Python)  
- **Installer:** Alfred packaged via PyInstaller; root path for MCP config resolved correctly  
- **Publish Update:** Uses GitHub REST API directly (gh CLI removed from this path)  

## Request Flow

1. **Classify:** Function `classify_task()` uses GPT-4.1-mini with `CLASSIFIER_PROMPT` to categorize input as `GENERAL`, `POWERBI`, `CLAUDE_EXECUTION`, or `QUANT`  
2. **Skill loading:** `load_relevant_skills()` matches keywords against filenames and first-line titles in `skills/*.md` to inject relevant skill content into prompts  
3. **Scope generation:** `generate_claude_scope()` uses GPT-4.1-mini with `CLAUDE_SCOPE_PROMPT`, current memory summary, and skills context to generate a structured plan  
4. **Dispatch decision:** `should_send_to_claude()` prevents auto-dispatch if dangerous keywords detected; `detect_provider_override()` (hardened) handles explicit `use claude` / `use codex` phrases  
5. **Web search:** GENERAL responses augmented with Brave Search results where relevant  
6. **Logging:** Interaction logged with timestamp at `logs/interactions.md` via `append_interaction_log()`  
7. **Memory consolidation:** After ~10 log entries, `consolidate_memory_if_needed()` uses GPT-4.1-mini to merge logs into `memory/session-summary.md`, retaining last 5 logs  

## Safety Rules

- **Dangerous keywords** block automatic dispatch: `delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`  
- **Action keywords** trigger POWERBI dispatch: `inspect`, `run`, `edit`, `use mcp`, `use claude`  
- **Scope prompt design:** Emphasizes minimal MCP usage; precludes broad file/data scans; sets hard stop conditions; prioritizes Power Query transformation inspection before source file inspection  
- **Token input masking:** API keys and tokens masked in terminal input  
- **Private file hygiene:** Credential/private files untracked from git repository  

## Current Features

- Automatic task classification with GPT-4.1-mini across four categories: `GENERAL`, `POWERBI`, `CLAUDE_EXECUTION`, `QUANT`  
- Dynamic skill loading from Markdown files by keyword matching  
- Scope generation that carefully scopes and structures Claude prompts  
- Blocking of risky commands to prevent unsafe dispatches  
- Automatic interaction logging and memory consolidation after threshold interactions  
- Headless invocation of Claude CLI and Codex CLI for execution when appropriate  
- Terminal user interface based on `rich`  
- **Brave Search integration** for GENERAL category responses (live web results)  
- Partial context handling for incomplete or fragmented user inputs, especially for Power BI DAX snippets  
- Incremental recognition and scoped inspection targets for fragmentary DAX expressions  
- Enhanced scope generation for incomplete DAX expressions (hypotheses, inspection targets, forbidden scopes)  
- Detailed diagnostic explanations for complex DAX measures (context transition, filter propagation, relationship misalignment, `SELECTEDVALUE` in FILTER)  
- Claude fallback when OpenAI is unavailable  
- SSL certificate error handling for corporate (Maersk) network environments  
- No-admin installation paths: `winget --scope user`, portable Node.js, user-scope Python  
- Hardened explicit provider override parsing (`use claude ...` / `use codex ...` bypass keyword scoring)  
- QUANT category routing defined; currently falling back to `openai_mini` â€” Quant plugin API path not yet fully connected  
- Security hardening: private files untracked from git, API token input masked in terminal  
- Alfred packaged as standalone installer via PyInstaller (MCP config root path resolved)  
- Publish Update flow uses GitHub REST API directly (gh CLI dependency removed)  

## Current Skills

- `skills/powerquery-column-errors.md` â€” specialized logic to diagnose Power Query column errors by inspecting Transform steps before source inspection  

## Memory & Logging

- `memory/session-summary.md` â€” consolidated memory summary updated periodically  
- `logs/interactions.md` â€” append-only log, trimmed to last 5 after consolidation  
- Consolidation model: GPT-4.1-mini  
- Consolidation threshold: 10 interactions  

## Placeholder Directories

- `skills/` â€” hosts `.md` skill files, auto-loaded via keyword matching  
- `templates/` â€” currently empty, planned for prompt templates  
- `logs/` â€” auto-created at first interaction  

## Implemented Commits (chronological)

1. Initial working orchestrator design  
2. Exclude `.venv` from git tracking  
3. Handle EOFError on piped stdin; add CLAUDE.md documentation  
4. Automatic Claude dispatch with dangerous keyword blocking  
5. Deterministic skill loading via filename and first-line title keyword matching  
6. Memory context injection and interaction logging  
7. Automatic memory consolidation with GPT-4.1-mini  
8. Improved partial user input recognition in POWERBI category, handling incomplete DAX snippets  
9. Enhanced scope generation for partial/fragmentary DAX expressions  
10. Added detailed diagnostic handling of complex DAX measures with nested FILTER and SELECTEDVALUE  
11. Hardened explicit provider override parsing  
12. Fix SSL certificate error on corporate Maersk network  
13. Fix claude login and add Claude fallback when OpenAI is unavailable  
14. No-admin installs: `--scope user` winget + portable Node.js + user Python  
15. Rebuild Alfred installer  
16. Fix PyInstaller root path for MCP config  
17. Replace gh CLI with GitHub REST API in Publish Update  
18. Security hardening: untrack private files, mask token input  
19. Add Brave Search to Alfred general chat responses  

## Next Planned Features

- **Codex TTY fix:** Resolve "stdout is not a terminal" error when invoking Codex headlessly (pty wrapper or `-p` flag equivalent)  
- **QUANT plugin routing:** Connect QUANT-classified tasks to the Quant Intelligence plugin API instead of falling back to openai_mini  
- **Anthropic inference:** Replace GPT-4.1-mini in scope generation with Claude API (Haiku for low cost, Sonnet for quality), incorporating prompt caching on `CLAUDE_SCOPE_PROMPT`  
- **pbi-cli integration:** Route `POWERBI` classified tasks through `pbi-cli` tool  
- **Expanded skillset:** Add skill files such as `excel-errors.md`, `mcp-usage.md`  
- **MCP governance:** Implement allowlist/blocklist controls for MCP usage in generated prompts  
- **Structured output:** Transition scope plans to JSON schema outputs for safer downstream parsing  
- **User interface/dashboard:** Web or terminal UI dashboard for plan review and dispatch confirmation