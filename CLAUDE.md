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

No `requirements.txt` or `pyproject.toml` exists — dependencies are managed directly in `.venv`. Key packages: `anthropic`, `openai`, `python-dotenv`, `rich`, `typer`.

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

## Planned Expansion

The following directories are empty placeholders for future features:
- `skills/` — custom skill modules
- `templates/` — prompt templates
- `memory/` — conversation memory/history
- `logs/` — operation logging
