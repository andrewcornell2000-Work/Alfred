# Alfred — AI Task Routing Orchestrator

Alfred accepts natural language task descriptions, classifies them with GPT-4.1-mini, and generates optimised Claude Code prompts for execution.

---

## Fresh-machine setup

1. **Clone the repo**
   ```powershell
   git clone <repo-url> alfred
   cd alfred
   ```

2. **Double-click `Install-Alfred.bat`**

   That's it. The installer will:
   - Check Python, Git, Node.js, and npm (and tell you what to install if missing)
   - Install Claude Code CLI and Codex CLI via npm (if npm is available)
   - Create a `.venv` and install Python packages
   - Write `.env.template` if `.env` is missing
   - Print login instructions for Claude and Codex
   - Launch Alfred when everything is ready

   Re-run `Install-Alfred.bat` any time — all steps are idempotent.

---

## First run checklist

Before Alfred starts you need:

| Requirement | Where to get it |
|---|---|
| Python 3.10+ | https://www.python.org/downloads/ — tick **Add to PATH** |
| Git | https://git-scm.com/download/win |
| Node.js 18+ | https://nodejs.org/ |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |

The installer guides you through each one. After Python and Node are installed, re-run `Install-Alfred.bat` — it picks up where it left off.

### Add API keys

If the installer reports `.env is missing`:

```powershell
Copy-Item .env.template .env
notepad .env
```

Fill in your keys, save, then double-click `Install-Alfred.bat` again.

### Log in to CLIs

Run once per machine after the CLIs are installed:

```powershell
claude login   # opens browser — authenticate with your Anthropic account
codex login    # opens browser — authenticate with your OpenAI account
```

---

## Day-to-day use

Double-click **`run-alfred.bat`**, or from a terminal:

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
backend/                        Core logic (main.py)
skills/                         Custom skill modules
  karpathy-coding-guidelines.md  Karpathy coding principles for all code tasks
templates/                      Prompt templates (future)
memory/                         Conversation memory and routing rules
logs/                           Operation logs
Install-Alfred.bat              One-click installer and launcher (start here)
run-alfred.bat                  Portable day-to-day launcher
setup.ps1                       Setup script (called by Install-Alfred.bat)
CLAUDE.md                       Claude Code instructions
AGENTS.md                       Coding agent guidelines (Codex, Claude Code)
```

---

## Troubleshooting

**`.venv` missing** — Run `Install-Alfred.bat` (or `.\setup.ps1`) again.

**API key errors** — Check `.env` exists and contains valid keys (no extra spaces or quotes around values).

**`claude` / `codex` not found after install** — Open a new terminal so PATH changes from the npm install take effect, then run `claude login` / `codex login`.

**npm global install fails with permission errors** — Run `Install-Alfred.bat` as Administrator (right-click → Run as administrator).
