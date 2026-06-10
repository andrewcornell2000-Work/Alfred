# Alfred Pack

**Alfred is not a chatbot you talk to every day.** Alfred is a **toolchain pack** for Windows that:

1. Installs CLIs (Claude Code, Codex, gh, pbi, LeanCTX, …)
2. Provisions **MCP servers** globally into Cursor, Claude Code, and Codex
3. Syncs **skills** and **rules** into all three agents
4. Runs a **discovery loop** (GitHub Actions) that finds new MCPs and tools you wouldn't think to search for

## What you do day-to-day

**Work in Cursor** (or Claude Code / Codex). Just ask normally — MCPs, LeanCTX, and skills are already wired.

## What Alfred does for you

| When | What |
|------|------|
| Fresh machine | Run `Alfred-Install.exe` once |
| Weekly / after updates | Re-run `.exe` or `run-alfred.bat` (checks git pull → setup → provision) |
| "What's installed?" | Alfred menu → Control Tower, or `lean-ctx doctor` |
| "What can I ask that I don't know?" | Read `requirements/discovered-tools.md` |
| Claude Desktop Connectors empty | Alfred provisions Desktop separately — re-run `Provision-Cursor.ps1`, restart Claude app |

## Provision pipeline (single source of truth)

```
cursor/mcp.json          → MCP template (no secrets)
skills/*.md              → agent how-to skills
cursor/rules/*.mdc       → Cursor rules (optional -ProjectPath)
Provision-Cursor.ps1     → ~/.cursor/mcp.json
                         → claude mcp add --scope user
                         → codex mcp add
                         → ~/.cursor/skills + ~/.claude/skills + ~/.codex/skills
                         → lean-ctx bootstrap (merge, not replace)
```

## Discovery loop (the real value)

Every day, cloud Alfred:

1. Searches the web for new MCPs, CLIs, and techniques for finance/office/AI-dev work
2. Compares against what's already in `cursor/mcp.json` and `discovered-tools.md`
3. Ships a **complete** skill or catalog entry with **"Try asking:"** example prompts
4. Commits to GitHub → you pull / re-run installer → provision picks it up
5. Emails you a **daily** update (noon AEST) and a **weekly digest** (Monday noon) with tools to try

You don't hunt for tools. The loop brings them to you.

## Optional: Alfred CLI

`run-alfred.bat` is for updates, Control Tower, and Dev Portal — not your primary workspace.
Use Cursor for actual work.
