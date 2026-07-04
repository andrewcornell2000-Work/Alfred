# CLAUDE.md

Guidance for Claude Code and other coding agents working in this repository.

## Project Overview

Alfred is a Windows **toolchain pack** plus an optional CLI orchestrator. Day-to-day work happens in **Cursor** with globally provisioned MCPs, skills, and rules.

The Alfred CLI (`python backend/main.py`) routes natural-language tasks via `alfred_brain()`:

| Category | Meaning | Provider |
|----------|---------|----------|
| `GENERAL` | Conversation, explanation, planning | `claude` (chat) |
| `SEARCH` | Live/current data (news, versions, prices) | `claude` + Tavily |
| `CODE` | Repo code, tests, refactors | `codex` |
| `EXECUTE` | Files, scripts, Excel, browser, GitHub | `claude_code` |
| `POWERBI` | Models, DAX, Power Query | `claude_code` |

Claude Code and Codex are invoked through local CLIs (`claude auth login`, `codex login`).

## Running the App

```powershell
.venv\Scripts\activate
python backend\main.py
```

At the `Alfred >` prompt, type a task. Use `back`, `menu`, or `exit` to return to the main menu.

## Environment

Optional keys in `.env` (see `.env.template`):

```text
ANTHROPIC_API_KEY=...    # faster chat if set
TAVILY_API_KEY=...       # web search
GITHUB_TOKEN=...         # GitHub MCP
QUANT_BASE_URL=...       # local Quant plugin
```

## Architecture (`backend/main.py`)

1. **Route** — `alfred_brain()` returns category, provider, `needs_search`, optional plan/steps.
2. **Search** — `_tavily_search()` when category is `SEARCH` or brain/heuristics say live data is needed.
3. **Skills** — `load_relevant_skills()` injects matching top-level `skills/*.md` into execution prompts.
4. **Dispatch** — `run_codex()` or `run_claude()` with `_build_execution_prompt()` when auto-dispatch gates allow.
5. **Log** — Rich panels; autosave under `logs/` and `memory/`.

Quant plugin: `plugins/quant/` (Flask API). Menu option **9. Quant Dashboard**.

## Routing Rules

Canonical doc: `memory/routing-rules.md`. Keep aligned with:

- `ALFRED_BRAIN_PROMPT`
- `DANGEROUS_KEYWORDS`
- `CODEX_ROUTING_KEYWORDS` / `CLAUDE_CODE_ROUTING_KEYWORDS`
- `LEARNING_MODE_KEYWORDS`
- `detect_provider_override()`

Explicit overrides (`use claude ...`, `use codex ...`) bypass keyword scoring.

## Execution Scoping Principles

When building or modifying execution prompts:

- Minimize MCP usage; one primary path per task (`skills/mcp-routing.md`)
- Avoid broad repo scans — inspect minimum necessary scope first
- Stop after diagnosis unless the user asked for fixes
- For Power Query column errors, inspect query steps before source files
- Include hard stop conditions for destructive actions

## Tool Manifests

| File | Purpose |
|------|---------|
| `cursor/mcp.json` | MCP template (source of truth) |
| `requirements/mcp-tools.md` | Human MCP catalog |
| `requirements/alfred-tools.json` | CLI/package reference |
| `requirements/python-requirements.txt` | Core pip packages |
| `requirements/npm-tools.txt` | Global npm CLIs |

Provision: `Provision-Cursor.ps1` → Cursor, Claude Code, Codex user configs.

## Learning / Dev Portal

Menu option **5. Dev Portal** — discuss changes before dispatch. See `docs/LEARNING-WORKFLOW.md`.

Adding external tools: update manifests + `mcp-tools.md` + skill; never commit secrets.

## Repo Structure

Full map: **`docs/ALFRED-STRUCTURE.md`**

## Coding Guidelines

- `skills/karpathy-coding-guidelines.md`
- `AGENTS.md`
