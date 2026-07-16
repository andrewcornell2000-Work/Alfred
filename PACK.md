# Alfred Pack

**Alfred is not a chatbot you talk to every day.** Alfred is a **Windows installer and toolchain pack** that:

1. Installs CLIs (Claude Code, Codex, gh, pbi, …)
2. Provisions **MCP servers** globally into Cursor, Claude Code, and Codex
3. Syncs **skills** and **rules** into all three agents
4. Runs a **discovery loop** (GitHub Actions) that finds new MCPs and tools you wouldn't think to search for
5. Provides **maintenance commands** for update, provision, validate, and diagnostics

## What you do day-to-day

**Work in Cursor** (or Claude Code / Codex). Just ask normally — MCPs and skills are already wired.

You do **not** open Alfred to chat or use a menu.

## What Alfred does for you

| When | What |
|------|------|
| Fresh machine | Run **`Alfred-Install.exe`** once |
| Weekly / after updates | Re-run **`.exe`** or **`run-alfred.bat`** (git pull → setup → provision) |
| "What's installed?" | `python -m backend.cli status` or `python -m backend.cli diagnose` |
| "What can I try in Cursor?" | Read `requirements/discovered-tools.md` |
| Claude Desktop Connectors empty | Re-run `Provision-Cursor.ps1`, restart Claude app |

## Provision pipeline (single source of truth)

```
cursor/mcp.json          → MCP template (no secrets)
skills/*.md              → agent how-to skills
skills/_packs/**/SKILL.md→ vendored multi-file skill packs (copied verbatim)
cursor/rules/*.mdc       → Cursor rules (optional -ProjectPath)
Provision-Cursor.ps1     → ~/.cursor/mcp.json
                         → claude mcp add --scope user
                         → codex mcp add
                         → ~/.agents/skills (single copy)
                         → retires leftover servers (lean-ctx, ms-365, …)
```

## Discovery loop (the real value)

Every day, cloud Alfred:

1. Searches the web for new MCPs, CLIs, and techniques for finance/office/AI-dev work
2. Compares against what's already in `cursor/mcp.json` and `discovered-tools.md`
3. Ships a **complete** skill or catalog entry with **"Try asking:"** example prompts (for use in Cursor)
4. Commits to GitHub → you pull / re-run installer → provision picks it up
5. Emails a **daily** update (noon AEST) and a **weekly digest** (Monday noon) with tools to try

You don't hunt for tools. The loop brings them to you.

## Maintenance CLI (optional — not your primary workspace)

Developer/automation commands only:

```powershell
python -m backend.cli update      # same as run-alfred.bat
python -m backend.cli provision
python -m backend.cli validate
python -m backend.cli diagnose
python -m backend.cli status
```

Use **Cursor** for actual AI work.
