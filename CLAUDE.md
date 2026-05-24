# CLAUDE.md

This file provides guidance to Claude Code and other coding agents working in this repository.

## Project Overview

Alfred is a CLI-based AI task routing and prompt optimization orchestrator. It accepts natural-language task descriptions, classifies them with OpenAI, and routes work to one of four paths:

- `GENERAL` -> OpenAI Mini response in the terminal
- `POWERBI` -> scoped Claude Code execution plan and dispatch
- `CLAUDE_EXECUTION` -> Codex or Claude Code, chosen by deterministic keyword scoring
- `QUANT` -> Quant Intelligence plugin API

Claude Code and Codex are invoked through their local CLIs. Alfred currently uses CLI login for those providers, not provider API keys.

## Running the App

```powershell
# Activate the virtual environment (Windows)
.venv\Scripts\activate

# Run Alfred
python backend\main.py
```

At the `Alfred >` prompt, type a task description. Enter `back`, `menu`, or `exit` to return to the main menu.

## Environment Setup

The core app expects:

```text
OPENAI_API_KEY=...
```

Optional Quant configuration:

```text
QUANT_BASE_URL=http://127.0.0.1:5000
```

Use `claude login` and `codex login` for Claude Code and Codex authentication.

Python packages for Alfred core are declared in `requirements/python-requirements.txt` and installed into `.venv` by `setup.ps1`. Quant plugin packages are declared separately in `plugins/quant/requirements.txt`.

## Architecture

Most orchestration logic lives in `backend/main.py`.

1. **Classify** - `classify_task()` sends input to OpenAI with `CLASSIFIER_PROMPT`, returning `GENERAL`, `POWERBI`, `CLAUDE_EXECUTION`, or `QUANT`.
2. **Choose provider** - `choose_provider()` routes by category plus keyword scoring:
   - `GENERAL` -> `openai_mini`
   - `POWERBI` -> `claude_code`
   - `CLAUDE_EXECUTION` -> `codex`, `claude_code`, or `openai_mini`
   - `QUANT` -> Quant API path
3. **Scope** - `generate_claude_scope()` asks Claude CLI to produce a constrained execution plan for `POWERBI` and `CLAUDE_EXECUTION` tasks.
4. **Dispatch** - `run_claude()` or `run_codex()` executes the scoped prompt when auto-dispatch gates allow it.
5. **Render/log** - Rich terminal panels display results; logs and autosave entries are written under `logs/` and `memory/`.

The Quant plugin lives in `plugins/quant` and exposes Flask routes for analysis, opportunities, macro, alerts, paper trading, institutional flow, and learning stats.

## Routing Rules

Routing documentation lives in `memory/routing-rules.md`. Keep it aligned with these constants/functions in `backend/main.py`:

- `CLASSIFIER_PROMPT`
- `DANGEROUS_KEYWORDS`
- `CODEX_ROUTING_KEYWORDS`
- `CLAUDE_CODE_ROUTING_KEYWORDS`
- `LEARNING_MODE_KEYWORDS`
- `choose_provider()`
- `should_send_to_claude()`
- `detect_provider_override()`

Explicit provider override phrases such as `use claude ...` and `use codex ...` should bypass normal keyword scoring when present.

## Prompt Engineering Conventions

`CLAUDE_SCOPE_PROMPT` encodes rules for generated Claude Code prompts:

- Minimize MCP usage
- Avoid broad scans
- Inspect minimum necessary scope before acting
- Stop after diagnosis unless the user asked for fixes
- For Power Query column errors, inspect query steps before source files
- Include hard stop conditions
- Never tell Claude to scan all source files indiscriminately

When modifying or extending this prompt, preserve these scoping principles.

## Tool Manifests

Tool and dependency metadata is tracked in `requirements/`:

| File | Purpose |
|---|---|
| `python-requirements.txt` | Core Alfred pip packages used by `setup.ps1` |
| `npm-tools.txt` | npm global CLI tools; format `package:command:description` |
| `alfred-tools.json` | Reference manifest for tool/plugin metadata |
| `mcp-tools.md` | MCP server documentation and candidate registry |

`setup.ps1` reads `requirements/python-requirements.txt` and `requirements/npm-tools.txt`. It does not currently install `plugins/quant/requirements.txt`; install that separately when running the local Quant plugin.

## Learning Mode: Adding External Tools

When Alfred learns about a new external tool:

1. Add the tool to the appropriate install manifest when persistent installation is required.
2. Update `alfred-tools.json` with the full tool entry.
3. Update `requirements/mcp-tools.md` if it is an MCP server.
4. Update `README.md` if the tool changes setup, login, API key, or local dependency steps.
5. Commit manifest and documentation changes before the session ends.

Rules:

- Never add API keys, tokens, or credentials to committed files.
- Never auto-pull from GitHub or auto-install tools without explicit user approval.
- New tools with file-write or destructive capabilities must be represented in the safety gates before dispatch is allowed.

## Update Flow

`run-alfred.bat` calls `check-updates.ps1` on each startup:

1. Runs `git fetch origin main`.
2. Compares local HEAD with `origin/main`.
3. If behind, shows the commit list and asks before pulling.
4. If updates are pulled, `run-alfred.bat` re-runs `setup.ps1`.

`backend/main.py` also has a startup update check when run directly, and it follows the same approval-before-pull rule.

## Current Known Gaps

- Project Mode is planned but not implemented yet.
- Learning / Creator Mode exists as Dev Portal, but deterministic file-writing workflows for skills/rules/tools are still evolving.
- Quant plugin dependencies are separate from the core setup manifest.

## Coding Guidelines

For coding, refactoring, debugging, architecture, UI/app design, and Alfred self-improvement tasks, apply:

- `skills/karpathy-coding-guidelines.md`
- `AGENTS.md`
