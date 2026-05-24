# Alfred Session Summary  
*Last updated: 2026-05-23*

## Current Architecture

- **Entry point:** `backend/main.py` (all logic consolidated in one file)  
- **API clients:** `openai_client` (GPT-4.1-mini, actively used) + `anthropic_client` (Anthropic SDK present but unused for inference)  
- **Claude execution:** Headless Claude Code CLI via `subprocess.run(["claude", "-p", prompt])`  
- **Terminal UI:** Utilizes `rich.console.Console` for user interaction  
- **Environment:** `.env` file manages `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`; virtual environment `.venv` used without requirements.txt  
- **Skill files:** Markdown files in `skills/` folder, auto-loaded by filename and first-line title keyword matching  

## Request Flow

1. **Classify:** Function `classify_task()` uses GPT-4.1-mini with `CLASSIFIER_PROMPT` to categorize input as `GENERAL`, `POWERBI`, or `CLAUDE_EXECUTION`  
2. **Skill loading:** `load_relevant_skills()` matches keywords against filenames and first-line titles in `skills/*.md` to inject relevant skill content into prompts  
3. **Scope generation:** `generate_claude_scope()` uses GPT-4.1-mini with `CLAUDE_SCOPE_PROMPT`, current memory summary, and skills context to generate a structured plan (issue identification, inspection targets, forbidden scope, optimized prompt)  
4. **Dispatch decision:** `should_send_to_claude()` prevents auto-dispatch if dangerous keywords detected; auto-dispatches based on category and presence of action keywords  
5. **Logging:** Interaction logged with timestamp at `logs/interactions.md` via `append_interaction_log()`  
6. **Memory consolidation:** After ≥10 log entries, `consolidate_memory_if_needed()` uses GPT-4.1-mini to merge logs into concise `memory/session-summary.md`, retaining last 5 logs  

## Safety Rules

- **Dangerous keywords** block automatic dispatch: `delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`  
- **Action keywords** trigger POWERBI dispatch: `inspect`, `run`, `edit`, `use mcp`, `use claude`  
- **Scope prompt design:**  
  - Emphasizes minimal MCP usage  
  - Precludes broad file or data scans  
  - Sets hard stop conditions for safety and efficiency  
  - Prioritizes inspection of Power Query transformations before source file inspection  

## Current Features

- Automatic task classification with GPT-4.1-mini  
- Dynamic skill loading from Markdown files by keyword matching  
- Scope generation that carefully scopes and structures Claude prompts to optimize inspection and minimize resource use  
- Blocking of risky commands to prevent unsafe dispatches  
- Automatic interaction logging and memory consolidation after a threshold number of interactions  
- Headless invocation of Claude CLI for execution when appropriate  
- Terminal user interface based on `rich`  
- Partial context handling for incomplete or fragmented user inputs, especially for Power BI DAX snippets  
- Incremental recognition and scoped inspection targets for fragmentary DAX expressions (e.g., `DIVIDE(`, `CALCULATE(`, `FILTER(`, `DISTINCTCOUNT(...)`), focusing on syntax issues, context, and targeted inspection rather than broad scanning  
- Enhanced scope generation for incomplete DAX expressions, producing:  
  - Likely issue hypotheses for partial or out-of-context DAX inputs  
  - Precise first inspection targets based on measure/formula context, table relationships, and filter conditions  
  - Forbidden scopes explicitly excluding scanning of all source files or entire data models to avoid performance overhead and potential data leakage  
  - Optimized Claude prompt construction that is minimal, focused, and safety-conscious  
- Detailed diagnostic explanations for complex DAX measures, identifying potential context transition issues, filter propagation problems, and relationship misalignments, with a focus on `SELECTEDVALUE` usage inside FILTER conditions  

## Current Skills

- `skills/powerquery-column-errors.md` — specialized logic to diagnose Power Query column errors by inspecting Transform steps before source inspection  

## Memory & Logging

- `memory/session-summary.md` — consolidated memory summary updated periodically  
- `logs/interactions.md` — append-only log, trimmed to last 5 after consolidation  
- Consolidation model: GPT-4.1-mini  
- Consolidation threshold: 10 interactions  

## Placeholder Directories

- `skills/` — hosts `.md` skill files, auto-loaded via keyword matching  
- `templates/` — currently empty, planned for prompt templates  
- `logs/` — auto-created at first interaction  

## Implemented Commits (chronological)

1. Initial working orchestrator design  
2. Exclude `.venv` from git tracking  
3. Handle EOFError on piped stdin; add CLAUDE.md documentation  
4. Automatic Claude dispatch with dangerous keyword blocking  
5. Deterministic skill loading via filename and first-line title keyword matching  
6. Memory context injection and interaction logging  
7. Automatic memory consolidation with GPT-4.1-mini  
8. Improved partial user input recognition in POWERBI category, handling incomplete DAX snippets to produce scoped inspection plans and partial diagnostic guidance  
9. Enhanced scope generation for partial and fragmentary DAX expressions providing detailed issue hypotheses, targeted inspection scopes, and forbidden scopes to avoid broad scanning  
10. Added detailed diagnostic handling of complex DAX measures involving nested FILTER and SELECTEDVALUE calls revealing context transition and filter relationship issues  

## Next Planned Features

- **Anthropic inference:** Replace GPT-4.1-mini in scope generation with Claude API (Haiku for low cost, Sonnet for quality), incorporating prompt caching on `CLAUDE_SCOPE_PROMPT`  
- **pbi-cli integration:** Route `POWERBI` classified tasks through `pbi-cli` tool instead of Claude CLI execution  
- **Expanded skillset:** Add skill files such as `excel-errors.md`, `mcp-usage.md` into `skills/` directory  
- **MCP governance:** Implement allowlist/blocklist controls for Managed Code Process (MCP) usage within generated prompts  
- **Structured output:** Transition from free-text scope plans to JSON schema outputs defining issue, target, forbidden scope, and prompt for safer parsing downstream  
- **User interface/dashboard:** Develop web or terminal UI dashboard for plan review and dispatch confirmation before execution