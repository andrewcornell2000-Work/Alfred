# Alfred — AI Task Routing Orchestrator

Alfred accepts natural language task descriptions, classifies them with GPT-4.1-mini, and generates optimised Claude Code prompts for execution.

---

## Fresh-machine setup

### 1. Prerequisites

Install these before running setup:

| Tool | Download |
|---|---|
| Python 3.10+ | https://www.python.org/downloads/ — tick **Add to PATH** |
| Git | https://git-scm.com/download/win |
| Node.js 18+ | https://nodejs.org/ |

### 2. Clone the repo

```powershell
git clone <repo-url> alfred
cd alfred
```

### 3. Run setup

```powershell
.\setup.ps1
```

This will:
- Confirm Python, Git, Node, npm, Claude Code CLI, and Codex CLI are available
- Create `.venv` and install `anthropic openai rich python-dotenv`
- Create `.env.template` if `.env` is missing

### 4. Add API keys

Copy the template and fill in your keys:

```powershell
Copy-Item .env.template .env
notepad .env
```

Keys needed:

| Key | Where to get it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |

### 5. Install and log in to CLIs

```powershell
npm install -g @anthropic-ai/claude-code
claude login

npm install -g @openai/codex
codex login
```

### 6. Run Alfred

Double-click **run-alfred.bat**, or from a terminal:

```powershell
.\run-alfred.bat
```

At the `Ask Alfred >` prompt, describe your task. Type `exit` to quit.

---

## Running in development

```powershell
.venv\Scripts\activate
python backend\main.py
```

---

## Project layout

```
backend/        Core logic (main.py)
skills/         Custom skill modules (future)
templates/      Prompt templates (future)
memory/         Conversation memory (future)
logs/           Operation logs (future)
setup.ps1       First-time setup script
run-alfred.bat  Portable launch script
CLAUDE.md       Claude Code instructions
```

---

## Troubleshooting

**`.venv` missing** — Run `.\setup.ps1` again.

**API key errors** — Check `.env` exists and contains valid keys (no extra spaces or quotes).

**`claude` / `codex` not found** — Install globally with npm and ensure `npm` global bin is on your PATH.
