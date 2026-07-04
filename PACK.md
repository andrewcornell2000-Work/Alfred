# Alfred Pack

**Alfred is not a chatbot you talk to every day.** Alfred is a **toolchain pack** for Windows that:

1. Installs CLIs (Claude Code, Codex, gh, pbi, LeanCTX, …)
2. Provisions **MCP servers** globally into Cursor, Claude Code, and Codex
3. Syncs **skills** and **rules** into all three agents
4. **Learning workflow** — Cursor sessions per `docs/LEARNING-WORKFLOW.md` (replaces daily GitHub loop)

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
skills/_packs/**/SKILL.md→ vendored multi-file skill packs (copied verbatim)
skills/_vendor/impeccable→ impeccable design skill (per-harness path rewrite + Cursor hook)
cursor/rules/*.mdc       → Cursor rules (optional -ProjectPath)
Provision-Cursor.ps1     → ~/.cursor/mcp.json
                         → claude mcp add --scope user
                         → codex mcp add
                         → ~/.cursor/skills + ~/.claude/skills + ~/.codex/skills
                         → lean-ctx onboard (merge, not replace)
```

## Discovery & learning (Cursor)

Use Cursor in the Alfred repo with **`docs/LEARNING-WORKFLOW.md`**:

1. Research one new MCP, CLI, or technique for finance/office work (1–3 web searches when needed)
2. Compare against `cursor/mcp.json` and `discovered-tools.md`
3. Ship a complete skill or catalog entry with **"Try asking:"** prompts
4. Commit → pull / re-run installer → provision picks it up

The scheduled GitHub Actions loop is **disabled**. Manual workflow dispatch remains for emergencies.

Weekly digest email (Mondays) still summarizes recent learning-log entries.

## Optional: Alfred CLI

`run-alfred.bat` is for updates, Control Tower, and Dev Portal — not your primary workspace.
Use Cursor for actual work.
