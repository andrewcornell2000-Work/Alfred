# CLAUDE.md

This file provides guidance to Claude Code and other coding agents working in this repository.

## Project Overview

Alfred is a **Windows installer + provision + update + validation pack**. It is **not** an interactive chat or menu CLI.

Normal user flow:

1. Install via **`Alfred-Install.exe`** (or `Install-Alfred.bat` from a clone).
2. Alfred runs **`setup.ps1`** and **`Provision-Cursor.ps1`** — MCPs, skills, and rules land in Cursor, Claude Code, and Codex.
3. User works in those tools day-to-day.
4. Re-run **`run-alfred.bat`** or **`python -m backend.cli update`** to pull updates and re-provision.

## Maintenance CLI (developer / automation only)

Non-interactive command runner — **not** a chat interface:

```powershell
.venv\Scripts\activate
python -m backend.cli status      # short summary
python -m backend.cli diagnose    # detailed health report
python -m backend.cli validate    # catalog + template + rules + tests
python -m backend.cli provision   # Provision-Cursor.ps1
python -m backend.cli update      # check-updates → setup (if needed) → provision
```

`python backend\main.py` is a deprecated shim that forwards to `backend.cli`.

## Environment Setup

```text
# Optional in .env — only keys you use:
TAVILY_API_KEY=...
GITHUB_TOKEN=...
OPENAI_API_KEY=...
```

Use `claude auth login` and `codex login` for Claude Code and Codex authentication.

Python packages: `requirements/python-requirements.txt` → `.venv` via `setup.ps1`.

## Architecture

| Module | Purpose |
|--------|---------|
| `backend/cli.py` | Maintenance command runner |
| `backend/diagnostics/` | MCP status, setup scan, plain-text reports |
| `backend/provision/registry.py` | Capability registry (`TOOL_REGISTRY`) |
| `backend/updater/git.py` | Git fetch / behind-count helpers |
| `backend/config/env.py` | `.env` and secret helpers |
| `backend/context.py` | Project root, console, `.env` loading |
| `Provision-Cursor.ps1` | Single source of truth for MCP + skill provisioning |
| `Alfred-Install.ps1` | Full installer (compiled to `Alfred-Install.exe`) |
| `check-updates.ps1` | User-approved git pull |
| `setup.ps1` | Idempotent venv, npm, PATH setup |

Shared PowerShell: `Alfred-Common.ps1`, `Alfred-CoreSetup.ps1`.

### Legacy routing modules (removed)

Interactive task routing (`routing/brain.py`, `routing/keywords.py`) was removed.
Capability metadata lives in `backend/provision/registry.py`.
Safety keywords for skill authors: `requirements/safety-gates.md`.

## Capability registry

Human-readable capability list: `memory/routing-rules.md`.

Code: `backend/provision/registry.py` — `TOOL_REGISTRY`, `register_tool()`, `iter_control_tower_capabilities()`.

Diagnostics display: `python -m backend.cli diagnose`.

## Tool Manifests

| File | Purpose |
|---|---|
| `python-requirements.txt` | Core Alfred pip packages |
| `npm-tools.txt` | npm global CLI tools |
| `alfred-tools.json` | MCP/tool metadata for diagnostics |
| `mcp-tools.md` | MCP server documentation |
| `safety-gates.md` | Destructive-tool safety keywords for skill authors |
| `discovered-tools.md` | Optional tools catalog |

## Adding External Tools

When Alfred learns about a new external tool:

1. Add to install manifest if persistent installation is required.
2. Update `alfred-tools.json`.
3. Update `requirements/mcp-tools.md` if it is an MCP server.
4. Add MCP entry to `cursor/mcp.json` if provisioned.
5. Update `README.md` if setup/login steps change.
6. Run `Provision-Cursor.ps1` and `python -m backend.cli validate`.

Rules:

- Never add API keys to committed files.
- Never auto-pull or auto-install without explicit user approval.
- Destructive tools: document in `requirements/safety-gates.md` and skill safety notes.

## Update Flow

`run-alfred.bat` / `backend.cli update`:

1. `check-updates.ps1` — fetch, prompt, pull if approved (exit 10 = pulled).
2. `setup.ps1` — if updates were pulled.
3. `Provision-Cursor.ps1` — re-provision MCPs and skills.

## Coding Guidelines

- `skills/karpathy-coding-guidelines.md`
- `AGENTS.md`
