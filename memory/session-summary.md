# Alfred Session Summary
*Last updated: 2026-05-23*

## Current Architecture

- **Entry point:** `backend/main.py` (all logic in one file)
- **API clients:** `openai_client` (GPT-4.1-mini — active) + `anthropic_client` (Anthropic SDK — imported, unused for inference)
- **Claude execution:** `subprocess.run(["claude", "-p", prompt])` — headless Claude Code CLI
- **Terminal UI:** `rich.console.Console`
- **Env:** `.env` with `OPENAI_API_KEY` + `ANTHROPIC_API_KEY`; deps in `.venv` (no requirements.txt)

## Request Flow

1. **Classify** — `classify_task()`: GPT-4.1-mini + `CLASSIFIER_PROMPT` → `GENERAL` | `POWERBI` | `CLAUDE_EXECUTION`
2. **Skill load** — `load_relevant_skills()`: keyword-matches user input against filename stems + first-line title of each `skills/*.md`; injects matching skills into scope prompt
3. **Scope** — `generate_claude_scope()`: GPT-4.1-mini + `CLAUDE_SCOPE_PROMPT` + memory summary + skills context → structured plan (likely issue / first target / forbidden scope / optimized prompt)
4. **Dispatch** — `should_send_to_claude()`: blocks on dangerous keywords; auto-dispatches if `CLAUDE_EXECUTION` or if `POWERBI` + action keyword present
5. **Log** — `append_interaction_log()`: appends timestamped entry to `logs/interactions.md`
6. **Consolidate** — `consolidate_memory_if_needed()`: at ≥10 log entries, GPT-4.1-mini merges log into `memory/session-summary.md`, trims log to last 5 entries

## Safety Rules

- **Dangerous keywords** (block auto-dispatch): `delete`, `remove`, `overwrite`, `credentials`, `password`, `entire onedrive`, `all folders`, `whole workspace`
- **Action keywords** (trigger POWERBI dispatch): `inspect`, `run`, `edit`, `use mcp`, `use claude`
- **Scope prompt rules:** minimize MCP, no broad file scans, inspect minimum scope, include hard stop condition, inspect Power Query steps before source files

## Current Skills

- `skills/powerquery-column-errors.md` — Power Query column error diagnosis (inspect Transform steps first)

## Memory & Logging

- `memory/session-summary.md` — rolling consolidated summary (this file)
- `logs/interactions.md` — append-only interaction log; auto-trimmed to last 5 after consolidation
- Consolidation threshold: 10 interactions; model: GPT-4.1-mini

## Placeholder Directories

- `skills/` — add `.md` files; auto-loaded by keyword match
- `templates/` — empty (planned: prompt templates)
- `logs/` — auto-created on first interaction

## Implemented Commits (chronological)

1. Initial working orchestrator
2. Remove venv from git tracking
3. Handle EOFError for piped stdin; add CLAUDE.md
4. Automatic Claude dispatch rules + dangerous keyword blocking
5. Deterministic skill loading (keyword match on filename + title)
6. Memory context injection + interaction logging
7. Automatic memory consolidation (threshold-based, GPT-4.1-mini)

## Next Recommended Milestones

- **Anthropic inference:** Replace GPT-4.1-mini scope generation with Claude API (Haiku for cost, Sonnet for quality); use prompt caching on `CLAUDE_SCOPE_PROMPT`
- **pbi-cli integration:** Route `POWERBI` tasks to pbi-cli tool instead of Claude Code CLI
- **More skills:** Add `excel-errors.md`, `mcp-usage.md`, etc. to `skills/`
- **MCP governance:** Add allowlist/blocklist for MCP tool usage in generated prompts
- **Structured output:** Replace free-text scope with JSON schema (issue / target / forbidden / prompt) for safer downstream parsing
- **UI/dashboard:** Web or TUI interface for reviewing plans before dispatch
