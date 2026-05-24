# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Alfred is a CLI-based AI task routing and prompt optimization orchestrator. It accepts natural language task descriptions, classifies them via OpenAI GPT-4.1-mini, and generates optimized Claude Code prompts when appropriate.

## Running the App

```powershell
# Activate the virtual environment (Windows)
.venv\Scripts\activate

# Run Alfred
python backend/main.py
```

At the prompt `Ask Alfred >`, type a task description. Enter `exit` to quit.

## Environment Setup

Requires a `.env` file in the project root with:
```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Python packages are declared in `requirements/python-requirements.txt` and installed into `.venv` by `setup.ps1` via `pip install -r`. Key packages: `anthropic`, `openai`, `python-dotenv`, `rich`, `typer`.

## Architecture

All logic lives in `backend/main.py`. The flow is:

1. **Classify** — `classify_task()` sends the user input to GPT-4.1-mini with `CLASSIFIER_PROMPT`, which returns one of three labels: `GENERAL`, `POWERBI`, or `CLAUDE_EXECUTION`.
2. **Scope** — If classified as `POWERBI` or `CLAUDE_EXECUTION`, `generate_claude_scope()` sends the input to GPT-4.1-mini with `CLAUDE_SCOPE_PROMPT` to produce an optimized Claude Code prompt.
3. **Display** — Results are rendered in the terminal via `rich.console.Console`.

Two API clients are initialized at module load: `openai_client` (OpenAI) and `anthropic_client` (Anthropic). The Anthropic client is imported but not yet used for inference — scope generation currently uses OpenAI.

## Prompt Engineering Conventions

`CLAUDE_SCOPE_PROMPT` encodes specific rules for generated Claude Code prompts:
- Minimize MCP tool usage; prefer direct file reads over broad scans
- Inspect minimum necessary scope before acting
- For Power Query column errors, inspect query steps before source files
- Include hard stop conditions
- Never scan all source files indiscriminately

When modifying or extending this prompt, preserve these scoping principles.

## Tool Manifests

Tool dependencies are tracked in `requirements/`:

| File | Purpose |
|---|---|
| `python-requirements.txt` | pip packages; used by `setup.ps1` via `pip install -r` |
| `npm-tools.txt` | npm global CLI tools; format `package:command:description` |
| `alfred-tools.json` | Master manifest summarising all tool types with metadata |
| `mcp-tools.md` | MCP server documentation and candidate tool registry |

`setup.ps1` reads these files at runtime — adding a line to `npm-tools.txt` is enough to make setup auto-install a new tool on the next run.

## Learning Mode: Adding External Tools

When Alfred encounters or learns about a new external tool in a session:

1. Add the tool to the appropriate manifest file (`npm-tools.txt` or `python-requirements.txt`).
2. Update `alfred-tools.json` with the full tool entry.
3. Update `requirements/mcp-tools.md` if it is an MCP server.
4. Update `README.md` if the tool changes the user-facing setup steps (new login, new key).
5. Commit all manifest changes before the session ends.

**Rules that must not be broken:**
- Never add API keys, tokens, or credentials to any manifest or committed file.
- Never auto-pull from GitHub or auto-install tools without explicit user approval (`check-updates.ps1` always prompts).
- New tools with file-write or destructive capabilities must be added to `BLOCKED_KEYWORDS` in `backend/main.py` before they are allowed to dispatch.

## Update Flow

`run-alfred.bat` calls `check-updates.ps1` on each startup:
1. Runs `git fetch origin main` silently (no-op if offline).
2. Compares local HEAD with `origin/main`.
3. If behind, shows the commit list and asks **Y/N** — never pulls without approval.
4. On pull: re-runs `setup.ps1` to apply any new packages or tool entries.

## Planned Expansion

- `skills/` — custom skill modules
- `templates/` — prompt templates
- `memory/` — conversation memory/history
- `logs/` — operation logging

## Coding Guidelines

For all coding, refactoring, debugging, architecture, UI/app design, and Alfred self-improvement tasks, apply the guidelines in:

- [`skills/karpathy-coding-guidelines.md`](skills/karpathy-coding-guidelines.md) — full Karpathy coding principles (source: [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md))
- [`AGENTS.md`](AGENTS.md) — concise version for Codex and other coding agents
