# Alfred Pack 2.0

**Alfred is a Windows toolchain pack** — not a chatbot you use every day.

Run `Alfred-Install.exe` once and it wires your PC for AI work:

- **MCP servers** → Cursor, Claude Code, Codex (Power BI, Excel, GitHub, LeanCTX, …)
- **Skills + rules** → all three agents globally
- **CLIs** → Claude, Codex, gh, pbi, jq, LeanCTX, …
- **Discovery** → Cursor learning sessions (`docs/LEARNING-WORKFLOW.md`) ship catalog entries + skills

**Day-to-day:** work in **Cursor**. Just ask. The pack is already provisioned.

**Alfred CLI** (`run-alfred.bat`) is for updates, health checks, and viewing discovered tools — see [PACK.md](PACK.md).

---

## Fresh-Machine Setup

1. **Download the installer**

   Download **`Alfred-Install.exe`** from the latest GitHub Release:

   ```text
   https://github.com/andrewcornell2000-Work/Alfred/releases/latest/download/Alfred-Install.exe
   ```

   Save it anywhere, then double-click it.

   When Windows asks whether to run it, choose **More info** -> **Run anyway** if needed.

2. **Confirm the install folder**

   Press `Y` when prompted. The installer installs Git if needed, clones or updates Alfred in `%USERPROFILE%\Alfred`, and continues setup from there.

   Developer/manual fallback: download the full repo ZIP, extract it, open the extracted folder, and double-click `Install-Alfred.bat`.

   If Git is already installed, cloning is better because Alfred can check for updates:

   ```powershell
   git clone https://github.com/andrewcornell2000-Work/Alfred.git Alfred
   cd Alfred
   ```

3. **Let the installer finish**

   The installer will:
   - Check Python, Git, Node.js 18+, and npm
   - Install Git, Python, and Node.js with `winget` when available, or tell you the exact manual step if Windows blocks an install
   - Install Claude Code CLI and Codex CLI from `requirements/npm-tools.txt`
   - Create `.venv` and install Python packages from `requirements/python-requirements.txt`
   - Print login instructions for Claude and Codex
   - Run `Provision-Cursor.ps1` — registers all MCP servers and skills into **Cursor, Claude Code, and Codex**
   - Run `lean-ctx onboard` — merges LeanCTX context compression (no API keys required)
   - Launch Alfred only when the required local toolchain is ready

4. **Log in once**

   After install, open a new terminal and run:

   ```powershell
   claude auth login
   codex login
   ```

   Re-run `Alfred-Install.exe` any time to update or repair Alfred. All setup steps are intended to be idempotent.

### Cross-tool MCP + skills (Cursor, Claude Code, Codex)

`cursor/mcp.json` is the portable MCP template. `Provision-Cursor.ps1` resolves paths and secrets from `.env`, then writes:

| Tool | Where MCPs land |
|------|-----------------|
| Cursor | `~/.cursor/mcp.json` |
| Claude Code | `claude mcp add --scope user` |
| Codex | `codex mcp add` |

Skills from `skills/` sync to `~/.cursor/skills`, `~/.claude/skills`, and `~/.codex/skills`.

Re-provision after pulling updates:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
```

### LeanCTX (Alfred 2.0 — no new accounts)

LeanCTX compresses file reads and shell output, persists session memory, and exposes `ctx_*` MCP tools.
It merges into your existing MCP configs — Alfred domain tools are untouched.

| | Alfred MCPs | LeanCTX |
|---|-------------|---------|
| Power BI / Excel / GitHub | ✓ | — |
| Code read/search compression | — | ✓ |
| Session memory / knowledge graph | basic `memory` MCP | rich `ctx_*` memory |
| Web search | Tavily direct API | — |

Verify: `lean-ctx doctor` · Savings: `lean-ctx gain` · Skill: `skills/lean-ctx.md`

---

## First Run Checklist

Before Alfred is fully useful, you need:

| Requirement | Purpose | Where to get it |
|---|---|---|
| Python 3.10+ | Run Alfred and its Python dependencies | https://www.python.org/downloads/ - tick **Add to PATH** |
| Git | Clone/update Alfred | https://git-scm.com/download/win |
| Node.js 18+ and npm | Install Claude Code and Codex CLIs | https://nodejs.org/ |
| Claude Code login | File/app/MCP execution provider | `claude auth login` |
| Codex login | Code implementation provider | `codex login` |
| Optional API keys | Faster chat, web research, GitHub MCP | `.env` |

Claude and Codex use browser-based CLI login. Alfred can run from those logins; API keys are optional enhancements.

### Optional API Keys

If you want faster direct API responses or extra integrations, create `.env` manually:

```powershell
Copy-Item .env.template .env
notepad .env
```

Add only the keys you want:

```text
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
GITHUB_TOKEN=ghp_...
FAL_KEY=...            # optional — enables the fal-ai MCP (image/video/audio generation)
```

Save, then run `Alfred-Install.exe` or `run-alfred.bat` again.

### CLI Login

Run once per machine after the CLIs are installed:

```powershell
claude auth login
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

**Use Cursor** (or Claude Code / Codex) for real work. MCPs, LeanCTX, and skills are global.

### Keep the pack current

```powershell
# Re-run installer, or:
.\run-alfred.bat          # checks git pull → setup → provision
```

### Alfred CLI menu (optional)

| Option | Purpose |
|---|---|
| 2 | **Control Tower** — what's installed and ready on this machine |
| 3 | View Skills |
| 4 | **Discovered Tools** — things the loop found that you can try in Cursor |
| 7 | Publish update to GitHub |
| 1 | Ask Alfred (legacy chat — Cursor is better for daily work) |

New tools land in `requirements/discovered-tools.md` with **"Try asking:"** prompts. Re-provision after pulling updates.

## Office Mastery

Alfred is being shaped into an Office operator, not just a chat router:

| Domain | Tool path |
|---|---|
| Excel live workbooks | `excel` MCP / `excellm` |
| Excel offline files | `openpyxl` and `pandas` |
| Power BI models | `powerbi-modeling-mcp` |
| Power BI visuals | `pbi-cli` |
| Word documents | `python-docx` |
| PowerPoint decks | `python-pptx` |
| PDFs | `pypdf` |

Use `Control Tower` to see which capabilities are ready on the current machine.

---

## Discovery & learning (Cursor)

You can't find every useful MCP yourself. Use **Cursor in this repo** with `docs/LEARNING-WORKFLOW.md`:

1. Pick one mission (new MCP, CLI, or skill improvement)
2. Run 1–3 targeted web searches only when needed
3. Ship catalog entry + skill with **"Try asking:"** examples
4. Pull / re-run installer → `Provision-Cursor.ps1` wires everything globally

See `requirements/discovered-tools.md` for the living catalog.

The old GitHub Actions daily loop is **disabled** (manual dispatch only). Weekly digest email still runs Mondays.

Structure reference: **`docs/ALFRED-STRUCTURE.md`**

### MCPs added in v2.2.0

Cherry-picked from a read-only review of the ECC harness (`affaan-m/ECC`) — only the ones that beat what Alfred already had:

| MCP | What it adds | Key |
|-----|--------------|-----|
| `fal-ai` | AI image/video/audio generation — ad creative, thumbnails, b-roll | `FAL_KEY` in `.env` |
| `magic` | Magic UI components — animated React/Tailwind blocks | none |
| `parallel-search` | Citation-backed web search + fetch in one call (via `mcp-remote`) | none (key-free) |
| `longhand` | Lossless Claude Code session history → local SQLite+ChromaDB | `pip install longhand && longhand setup` |

Each is auto-skipped by `Provision-Cursor.ps1` if its key/command is missing, so they never break a provision.

---

## Continuous Learning (instincts)

Alfred now learns **instincts** — confidence-scored `when X → do Y` lessons that
**surface automatically at the start of every session** (via a `SessionStart`
hook), instead of sitting inert in a memory file.

```powershell
python scripts/instinct-cli.py status     # see what Alfred has learned
```

Slash commands `/instinct-status` and `/instinct-learn` drive it; the autonomous
loop records a lesson each iteration and ages out stale ones. Two guardrail hooks
ship alongside (wired in `.claude/settings.json`): **config-protection** (blocks
weakening linter configs) and **pre-commit-quality** (secret/debugger scan before
`git commit`). Details: `skills/continuous-learning.md` and
`memory/instincts/README.md`.

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
memory/instincts/                Confidence-scored learned instincts (continuous learning)
scripts/instinct-cli.py          Instinct engine (status/record/decay/prune)
scripts/hooks/                   Claude Code hooks (instinct surfacing + guardrails)
logs/                            Interaction logs
Alfred-Install.ps1               Source script compiled into Alfred-Install.exe for releases
Install-Alfred.bat               Repo-local installer and launcher fallback
Install-From-GitHub.bat          Legacy bootstrap fallback when the .exe is unavailable
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

**`.venv` missing** - Re-run `Alfred-Install.exe`. If you are working from a cloned repo, run `Install-Alfred.bat` or `.\setup.ps1` again.

**API key errors** - API keys are optional. Check `.env` only if you added one; values should have no quotes or extra spaces.

**`claude` / `codex` not found after install** - Open a new terminal so PATH changes from npm install take effect, then run `claude auth login` and `codex login`.

**`npm.ps1 cannot be loaded because running scripts is disabled`** - Download the latest `Alfred-Install.exe` from GitHub Releases and run it again. The installer now calls `npm.cmd`/`npx.cmd` directly, so PowerShell execution policy should not block npm installs.

**Quant import errors** - Activate `.venv`, then run `pip install -r plugins\quant\requirements.txt`.

**npm global install fails with permission errors** - Re-run `Alfred-Install.exe` as Administrator, or install the CLI manually with `npm install -g`.

**Local `Node/` folders** - These are machine-local caches and are ignored by git. Fresh installs should use `setup.ps1` to install or detect Node.js instead of committing a Node runtime into the repo.
