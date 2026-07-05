# Alfred's Brain
*Living knowledge base. Updated every loop iteration. Never overwritten — only grown.*

**Born:** 2026-06-05  
**Home:** C:\Users\ACO324\Alfred  
**GitHub:** https://github.com/andrewcornell2000-Work/Alfred

---

## What Alfred Is
A Windows-first CLI AI orchestrator for a finance & labour planning team at Maersk.
Routes natural language tasks to the best AI provider (Claude CLI, Codex, OpenAI Mini).
Runs without admin rights. Distributable to teammates via Install-From-GitHub.bat.

## Current Architecture
- `backend/main.py` — core routing engine (classify → choose → scope → dispatch)
- `backend/power_query.py` — Power Query column error handler
- `skills/` — 12+ markdown skill modules Alfred can invoke
- `memory/` — persistent context, learning log, routing rules
- `.claude/settings.json` — Claude Code MCP config for Alfred sessions

## Providers Alfred Routes To
- Claude CLI (`claude` command) — Power BI, deep execution, file work
- Codex — coding, refactoring, Alfred self-modification
- OpenAI Mini — general queries, cheap classification

## What Alfred Can Do (Confirmed Working)
- Route tasks by natural language
- Execute Claude Code scoped prompts
- Edit Excel live via MCP
- Edit Power BI models via pbi-cli
- Web search via Tavily
- Self-update check on every launch (check-updates.ps1)
- Learning / Creator Mode (Dev Portal — menu option 8)
- Teach himself new skills via Dev Portal

## Alfred's Email (for account creation)
Stored in $env:ALFRED_EMAIL — use for signing up to free-tier services that improve Alfred.

## Frontier — What Alfred Is Pushing Toward
- Supabase persistent memory (queryable brain instead of flat files)
- Project Mode (planned, not yet built)
- Multi-agent coordination
- Better skill auto-selection
- Autonomous improvement loop (THIS — the loop writing to this file)

## Open Questions
- What's the best persistent memory backend for an autonomous agent in 2026?
- Can Alfred coordinate multiple Claude Code subagents?
- What MCP servers would most expand Alfred's capabilities?
- How should Alfred handle tasks that span multiple sessions?

## Connections (Cross-Domain Insights)
> Populated as patterns emerge across loop iterations.

## Accounts Alfred Has Created
See memory/accounts.md
