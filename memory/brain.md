# Alfred's Brain
*Living knowledge base. Updated every loop iteration. Never overwritten — only grown.*

**Born:** 2026-06-05  
**Home:** `%USERPROFILE%\Alfred`  
**GitHub:** https://github.com/andrewcornell2000-Work/Alfred

---

## What Alfred Is (2026-07)

A **Windows installer and toolchain pack** — not an interactive chat CLI.

Alfred:

- Installs Python, Node, CLIs, and `.venv` dependencies
- Provisions **MCP servers**, **skills**, and **rules** into Cursor, Claude Code, and Codex
- Runs a **discovery / learning loop** (GitHub Actions) that ships new tools and skills
- Exposes **maintenance commands** (`backend.cli`) for update, provision, validate, and diagnostics

Users work in **Cursor / Claude Code / Codex** — not in Alfred.

## Current Architecture

| Component | Role |
|-----------|------|
| `Alfred-Install.exe` | One-click installer (from `Alfred-Install.ps1`) |
| `setup.ps1` | Idempotent venv, npm, PATH setup |
| `Provision-Cursor.ps1` | MCP + skills + rules provisioning |
| `run-alfred.bat` | Update check → setup → provision |
| `backend/cli.py` | Non-interactive maintenance runner |
| `backend/diagnostics/` | Health reports, MCP status |
| `backend/provision/registry.py` | Capability registry |
| `skills/` | Markdown skills (provisioned globally) |
| `memory/` | Learning log, instincts, routing notes |

## Legacy (removed)

Interactive chat, menus, slash commands, task dispatch, and routing modules (`routing/brain.py`, `routing/keywords.py`) were removed.

## Discovery Loop

Cloud Alfred searches for new MCPs/CLIs, updates `discovered-tools.md` and skills, commits to GitHub.
Users pull or re-run installer → provision picks up changes.

## Frontier

- Project Mode (planned)
- Richer instinct / continuous-learning integration
- Stronger validate CI on every growth-loop commit

## Accounts Alfred Has Created

See `memory/accounts.md`
