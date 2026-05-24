# Alfred - AI Task Routing Orchestrator

Alfred is a Windows-first CLI operator for routing natural-language work to the cheapest capable AI provider. It classifies a request, chooses OpenAI Mini, Claude Code, Codex, or the Quant plugin, then either answers directly, generates a scoped execution prompt, or dispatches to the selected tool.

---

## Fresh-Machine Setup

1. **Get the repo from GitHub**

   Easiest Windows path: download **`Install-From-GitHub.bat`** from this repo and double-click it. It installs Git if needed, clones or updates Alfred in `%USERPROFILE%\Alfred`, then starts the normal installer.

   If you download the full repo ZIP instead, extract it, open the extracted folder, and double-click `Install-Alfred.bat`.

   If Git is already installed, cloning is better because Alfred can check for updates:

   ```powershell
   git clone https://github.com/andrewcornell2000-Work/Alfred.git Alfred
   cd Alfred
   ```

2. **Double-click `Install-Alfred.bat`**

   The installer will:
   - Check Python, Git, Node.js 18+, and npm
   - Install Git, Python, and Node.js with `winget` when available
   - Install Claude Code CLI and Codex CLI from `requirements/npm-tools.txt`
   - Create `.venv` and install Python packages from `requirements/python-requirements.txt`
   - Print login instructions for Claude and Codex
   - Prompt for `OPENAI_API_KEY` if it is missing
   - Launch Alfred only when the required local toolchain is ready

   Re-run `Install-Alfred.bat` any time. All setup steps are intended to be idempotent.

---

## First Run Checklist

Before Alfred is fully useful, you need:

| Requirement | Purpose | Where to get it |
|---|---|---|
| Python 3.10+ | Run Alfred and its Python dependencies | https://www.python.org/downloads/ - tick **Add to PATH** |
| Git | Clone/update Alfred | https://git-scm.com/download/win |
| Node.js 18+ and npm | Install Claude Code and Codex CLIs | https://nodejs.org/ |
| Claude Code login | File/code execution provider | `claude login` |
| Codex login | Code implementation provider | `codex login` |
| `OPENAI_API_KEY` | Classification and general chat | https://platform.openai.com/api-keys |

Claude and Codex use browser-based CLI login. Alfred does not require an `ANTHROPIC_API_KEY` for the current CLI-based Claude Code flow.

### API Key

If Alfred reports that `OPENAI_API_KEY` is missing, either follow the prompt or create `.env` manually:

```powershell
Copy-Item .env.template .env
notepad .env
```

Add:

```text
OPENAI_API_KEY=sk-...
```

Save, then run `Install-Alfred.bat` or `run-alfred.bat` again.

### CLI Login

Run once per machine after the CLIs are installed:

```powershell
claude login
codex login
```

---

## Quant Plugin Setup

Alfred includes a Quant Intelligence plugin under `plugins/quant`.

By default, `backend/main.py` uses `QUANT_BASE_URL` when set, otherwise it falls back to the configured cloud Quant URL. To force the local Flask server, add this to `.env`:

```text
QUANT_BASE_URL=http://127.0.0.1:5000
```

The Quant plugin has its own Python dependencies in `plugins/quant/requirements.txt`:

```powershell
.venv\Scripts\activate
pip install -r plugins\quant\requirements.txt
```

Run the dashboard directly:

```powershell
python plugins\quant\app.py
```

Or use Alfred menu option **9. Quant Dashboard**.

---

## Day-To-Day Use

Double-click **`run-alfred.bat`**, or from a terminal:

```powershell
.\run-alfred.bat
```

At the `Alfred >` prompt, describe your task. Type `back`, `menu`, or `exit` to return to the main menu.

Useful menu options:

| Option | Purpose |
|---|---|
| 1 | Ask Alfred |
| 2 | View Memory |
| 3 | View Skills |
| 4 | View Recent Logs |
| 5 | Show Dispatch Rules |
| 6 | Run Claude Directly |
| 8 | Dev Portal / Learning Creator Mode |
| 9 | Quant Dashboard |

Use Dev Portal when you want to teach Alfred a new skill, routing rule, tool requirement, or self-improvement. Dev Portal discusses the proposed change first, asks for confirmation, then routes confirmed implementation work through Codex.

---

## Routing Summary

Alfred classifies each request as one of:

| Category | Typical route |
|---|---|
| `GENERAL` | OpenAI Mini answers directly |
| `POWERBI` | Claude Code scope + dispatch |
| `CLAUDE_EXECUTION` | Codex or Claude Code based on keyword scoring |
| `QUANT` | Quant plugin API |

Explicit provider override phrases are supported in the local working tree:

```text
use claude ...
use codex ...
with claude ...
with codex ...
via claude ...
via codex ...
ask claude ...
ask codex ...
```

Auto-dispatch is blocked for dangerous keywords such as `delete`, `remove`, `overwrite`, `credentials`, and `password`.

---

## Running In Development

```powershell
.venv\Scripts\activate
python backend\main.py
```

Run Quant tests:

```powershell
cd plugins\quant
python -m unittest discover -s tests
```

---

## Project Layout

```text
backend/                         Core Alfred CLI and routing logic
plugins/quant/                   Quant Intelligence Flask plugin
requirements/                    Python, npm, MCP, and tool manifests
skills/                          Markdown skill modules
memory/                          Conversation memory, routing notes, learning log
logs/                            Interaction logs
Install-Alfred.bat               One-click installer and launcher
Install-From-GitHub.bat          Fresh-machine bootstrap installer
run-alfred.bat                   Day-to-day launcher with update check
check-updates.ps1                Prompts before pulling GitHub updates
setup.ps1                        Idempotent setup script
CLAUDE.md                        Claude Code instructions
AGENTS.md                        Coding agent guidelines
```

---

## Current Known Gaps

- Project Mode is planned but not yet implemented. There is no `projects/` directory lifecycle yet.
- Quant plugin dependencies are tracked separately in `plugins/quant/requirements.txt`.
- The Quant stock universe is currently configured in `plugins/quant/config.py`.

---

## Troubleshooting

**`.venv` missing** - Run `Install-Alfred.bat` or `.\setup.ps1` again.

**`OPENAI_API_KEY` errors** - Check `.env` exists and contains `OPENAI_API_KEY=sk-...` with no quotes or extra spaces.

**`claude` / `codex` not found after install** - Open a new terminal so PATH changes from npm install take effect, then run `claude login` and `codex login`.

**Quant import errors** - Activate `.venv`, then run `pip install -r plugins\quant\requirements.txt`.

**npm global install fails with permission errors** - Run `Install-Alfred.bat` as Administrator, or install the CLI manually with `npm install -g`.

**Local `Node/` folders** - These are machine-local caches and are ignored by git. Fresh installs should use `setup.ps1` to install or detect Node.js instead of committing a Node runtime into the repo.
