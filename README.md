# Alfred - AI Task Routing Orchestrator

Alfred accepts natural language task descriptions, classifies them with GPT-4.1-mini, and generates optimized Claude Code prompts for execution.

---

## Fresh-Machine Setup

1. **Get the repo from GitHub**

   Easiest Windows path: download **`Install-From-GitHub.bat`** from this repo and double-click it. It installs Git if needed, clones or updates Alfred in `%USERPROFILE%\Alfred`, then starts the normal installer.

   If you download the full repo ZIP instead, extract it, open the extracted folder, and double-click `Install-Alfred.bat`.

   If Git is already installed, cloning is better because Alfred can check for updates:

   ```powershell
   git clone https://github.com/andrewcornell2000-Work/Alfred.git alfred
   cd alfred
   ```

2. **Double-click `Install-Alfred.bat`**

   The installer will:
   - Check Python, Git, Node.js 18+, and npm
   - Install Git, Python, and Node.js with `winget` when available
   - Install Claude Code CLI and Codex CLI from `requirements/npm-tools.txt`
   - Create `.venv` and install Python packages
   - Use `.env.template` to guide local API key setup
   - Print login instructions for Claude and Codex
   - Launch Alfred only when the required toolchain and `.env` are ready

   Re-run `Install-Alfred.bat` any time. All steps are idempotent.

---

## First Run Checklist

Before Alfred starts you need:

| Requirement | Where to get it |
|---|---|
| Python 3.10+ | https://www.python.org/downloads/ - tick **Add to PATH** |
| Git | https://git-scm.com/download/win |
| Node.js 18+ | https://nodejs.org/ |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |

The installer guides you through each one. After Python and Node are installed, re-run `Install-Alfred.bat`; it picks up where it left off.

### Add API Keys

If the installer reports `.env is missing`:

```powershell
Copy-Item .env.template .env
notepad .env
```

Fill in your keys, save, then double-click `Install-Alfred.bat` again.

### Log In To CLIs

Run once per machine after the CLIs are installed:

```powershell
claude login   # opens browser; authenticate with your Anthropic account
codex login    # opens browser; authenticate with your OpenAI account
```

---

## Day-To-Day Use

Double-click **`run-alfred.bat`**, or from a terminal:

```powershell
.\run-alfred.bat
```

At the `Ask Alfred >` prompt, describe your task. Type `exit` to quit.

Use menu option **8. Dev Portal** when you want to teach Alfred a new skill, routing rule, tool requirement, or self-improvement. Dev Portal discusses the proposed change first, asks for confirmation, then routes the confirmed work through Codex.

---

## Running In Development

```powershell
.venv\Scripts\activate
python backend\main.py
```

---

## Project Layout

```text
backend/                        Core logic (main.py)
skills/                         Custom skill modules
  karpathy-coding-guidelines.md  Karpathy coding principles for all code tasks
templates/                      Prompt templates (future)
memory/                         Conversation memory and routing rules
logs/                           Operation logs
Install-Alfred.bat              One-click installer and launcher (start here)
Install-From-GitHub.bat         Bootstrap installer for a fresh machine
run-alfred.bat                  Portable day-to-day launcher
setup.ps1                       Setup script (called by Install-Alfred.bat)
CLAUDE.md                       Claude Code instructions
AGENTS.md                       Coding agent guidelines (Codex, Claude Code)
```

---

## Troubleshooting

**`.venv` missing** - Run `Install-Alfred.bat` or `.\setup.ps1` again.

**API key errors** - Check `.env` exists and contains valid keys, with no extra spaces or quotes around values.

**`claude` / `codex` not found after install** - Open a new terminal so PATH changes from npm install take effect, then run `claude login` and `codex login`.

**npm global install fails with permission errors** - Run `Install-Alfred.bat` as Administrator: right-click, then **Run as administrator**.

**Local `Node/` folders** - These are machine-local caches and are ignored by git. Fresh installs should use `setup.ps1` to install or detect Node.js instead of committing a Node runtime into the repo.
