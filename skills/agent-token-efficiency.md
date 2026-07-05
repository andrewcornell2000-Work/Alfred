# Agent Token Efficiency

Use this skill when driving Claude Code, Codex, or Cursor agents on multi-step tasks.
Goal: same outcome, fewer tokens — without cutting corners on correctness.

## Core rules

1. **Search before read** — use `grep` / `rg` / targeted `SemanticSearch` to find the right file and line range before opening whole files.
2. **Read partial files** — use line offsets and limits; never dump a 2000-line file when 40 lines answer the question.
3. **One tool per job** — prefer the narrowest tool:
   - Live Excel open → `excel` MCP, not bash + openpyxl
   - Power BI model → `powerbi-modeling-mcp` or `pbi`, not re-describing the whole model in chat
   - Web facts → Tavily (Alfred direct API), not pasting long page HTML into context
   - File edits in repo → editor patch, not rewrite entire file in the reply
4. **Batch independent lookups** — parallel tool calls when queries do not depend on each other.
5. **Do not re-read** — if content is already in the conversation, reference it; do not `read_file` again.
6. **Structured output over prose** — tables, bullet deltas, and code citations beat long explanations.

## MCP tools that save tokens

| MCP | Token-saving use |
|-----|------------------|
| **LeanCTX** (`ctx_read`, `ctx_search`, `ctx_knowledge`) | Optional: map-mode reads, cached re-reads, compressed shell, session memory |
| `filesystem` | Finance-folder file ops without pasting directory listings into chat |
| `fetch` | Pull a URL to Markdown instead of browser MCP for read-only docs |
| `duckdb` | Query CSV/exports in SQL instead of loading sheets into context |
| `markitdown` | Convert PDF/Office to Markdown once; work from the text artifact |

## Anti-patterns (burn tokens)

- Reading every file in a directory "to understand the project"
- Pasting full API responses or log files into the reply
- Re-running the same DAX query because the prior result wasn't saved
- Using Playwright when `fetch` or Tavily suffices
- Writing a new skill that duplicates an existing one

## Alfred routing tie-in

Alfred routes by cost: `GENERAL` (cheap) → `CLAUDE_EXECUTION` / `POWERBI` (expensive).
When Alfred dispatches to an agent, the prompt should include **only** the scoped context needed —
not the whole repo state.
