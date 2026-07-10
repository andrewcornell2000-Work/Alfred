# Alfred Pack 2.0

**Alfred is a Windows installer and toolchain pack** — not a chat app you use every day.

Run `Alfred-Install.exe` once and it wires your PC for AI work:

- **MCP servers** → Cursor, Claude Code, Codex (Power BI, Excel, GitHub, …)
- **Skills + rules** → all three agents globally
- **CLIs** → Claude, Codex, gh, pbi, jq, …
- **Discovery loop** → nightly search for new tools you wouldn't think to look for

**Day-to-day:** work in **Cursor**. Just ask. The pack is already provisioned.

**Maintenance:** re-run the installer or `run-alfred.bat` to update and re-provision — see [PACK.md](PACK.md).

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
   - Create a desktop shortcut that runs **update + provision** (not a chat window)

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

Skills from `skills/` sync **once** to `~/.agents/skills` — the cross-tool Agent
Skills standard that Cursor, Claude Code, and Codex all read. (Per-tool copies in
`~/.cursor|.claude|.codex/skills` were retired: Cursor scans every root, so three
copies meant every skill listed in triplicate. The provisioner cleans them up.)

Rules are **per-project** — Cursor has no global rules directory. List your repos
in `.env` as `ALFRED_PROJECT_PATHS=C:\path\repo1;C:\path\repo2` and every provision
seeds `<repo>/.cursor/rules/*.mdc`, `AGENTS.md`, and the graphify rule into each.

Re-provision after pulling updates:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
```

Verify what each tool actually sees (runs automatically after provisioning):

```powershell
powershell -ExecutionPolicy Bypass -File Alfred-Doctor.ps1
```

Doctor checks MCP registration per target (Cursor / Claude Code / Claude Desktop /
Codex), single-copy skills, per-project rules, CLIs, and the Excel / Power BI
stack, then diffs against the previous report (`%LOCALAPPDATA%\alfred\doctor.json`)
so config drift is called out — "the script exited 0" is never trusted as success.

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
| Optional API keys | Web research, GitHub MCP, optional API paths | `.env` |

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
SUPABASE_PROJECT_REF=ieahwigeexmwvggmmjzp   # enables Supabase MCP in Cursor
SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.ieahwigeexmwvggmmjzp.supabase.co:5432/postgres
```

Save, then run `Alfred-Install.exe` or `run-alfred.bat` again.

### Supabase + Vercel (web apps)

Alfred provisions both via `Provision-Cursor.ps1`:

| Integration | What Alfred installs | First-use auth |
|---|---|---|
| **Supabase MCP** | Remote MCP + `npx skills add supabase/agent-skills` | OAuth in Cursor/Claude/Codex + `SUPABASE_PROJECT_REF` in `.env` |
| **Vercel MCP + plugin** | Remote MCP + `npx plugins add vercel/vercel-plugin` | OAuth in Cursor/Claude/Codex |

Skills: `skills/supabase.md` · `skills/vercel.md`

Vercel plugin docs: https://vercel.com/docs/agent-resources/vercel-plugin

Slash commands after plugin install: `/vercel-plugin:deploy`, `/vercel-plugin:nextjs`, `/vercel-plugin:ai-sdk`, etc.

### CLI Login

Run once per machine after the CLIs are installed:

```powershell
claude auth login
codex login
```

---

## Day-To-Day Use

**Use Cursor** (or Claude Code / Codex) for real work. MCPs and skills are global.

Alfred itself is **not** your workspace — it installs, provisions, updates, and validates.

### Keep the pack current

```powershell
# Re-run installer, or:
.\run-alfred.bat          # git update check → setup → provision
```

### Developer maintenance commands (non-interactive)

These are for diagnostics and automation — **not** a user-facing chat CLI:

```powershell
python -m backend.cli status      # short installed/provisioned summary
python -m backend.cli diagnose    # detailed health report
python -m backend.cli validate    # catalog, template, rules sync, tests
python -m backend.cli provision   # re-run Provision-Cursor.ps1
python -m backend.cli update      # same flow as run-alfred.bat
```

New tools land in `requirements/discovered-tools.md` with **"Try asking:"** prompts for use **inside Cursor**. Re-provision after pulling updates.

## Office Mastery

Alfred provisions Office-capable MCPs and skills. Use them from Cursor / Claude Code:

| Domain | Tool path |
|---|---|
| Excel live workbooks | `excel` MCP / `excellm` |
| Excel offline files | `openpyxl` and `pandas` |
| Power BI models | `powerbi-modeling-mcp` |
| Power BI visuals | `pbi-cli` |
| Word documents | `python-docx` |
| PowerPoint decks | `python-pptx` |
| PDFs | `pypdf` |

Check readiness: `python -m backend.cli diagnose`

---

## Discovery loop (why Alfred exists)

You can't find every useful MCP yourself. Alfred's GitHub Actions loop runs daily:

1. Searches for new MCPs, CLIs, and techniques (finance, office, Power BI, token efficiency)
2. Ships catalog entries + skills with **"Try asking:"** examples
3. Commits to this repo → you pull / re-run installer → `Provision-Cursor.ps1` wires everything globally

See `requirements/discovered-tools.md` for the living catalog.

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

Alfred learns **instincts** — confidence-scored `when X → do Y` lessons surfaced via Claude Code hooks (not via an Alfred chat UI):

```powershell
python scripts/instinct-cli.py status     # see what Alfred has learned
```

Details: `skills/continuous-learning.md` and `memory/instincts/README.md`.

---

## Running In Development

```powershell
.venv\Scripts\activate
python -m backend.cli validate    # safe checks
python -m backend.cli status      # quick health summary
```

Legacy entry point `python backend\main.py` forwards to the maintenance CLI (no chat).

## Project Layout

```text
backend/cli.py                   Non-interactive maintenance runner (update/provision/validate/…)
backend/diagnostics/             MCP status, setup scan, plain-text reports
backend/provision/registry.py    Capability registry
backend/skills_loader.py           Skill inventory for diagnostics (status/diagnose)
requirements/                    Python, npm, MCP, and tool manifests
requirements/safety-gates.md       Destructive-tool safety keywords for skill authors
skills/                          Markdown skill modules (provisioned globally)
memory/                          Learning log, routing notes, instincts
scripts/instinct-cli.py          Instinct engine (status/record/decay/prune)
Alfred-Install.ps1               Source compiled into Alfred-Install.exe for releases
Install-Alfred.bat               Repo-local installer fallback
run-alfred.bat                   Update + provision launcher (desktop shortcut target)
check-updates.ps1                Prompts before pulling GitHub updates
Provision-Cursor.ps1             MCP + skills + rules provisioning
setup.ps1                        Idempotent environment setup
CLAUDE.md                        Claude Code instructions for this repo
AGENTS.md                        Coding agent guidelines
```

---

## Current Known Gaps

- Project Mode is planned but not yet implemented. There is no `projects/` directory lifecycle yet.

---

## Troubleshooting

**`.venv` missing** - Re-run `Alfred-Install.exe`. If you are working from a cloned repo, run `Install-Alfred.bat` or `.\setup.ps1` again.

**API key errors** - API keys are optional. Check `.env` only if you added one; values should have no quotes or extra spaces.

**`claude` / `codex` not found after install** - Open a new terminal so PATH changes from npm install take effect, then run `claude auth login` and `codex login`.

**`npm.ps1 cannot be loaded because running scripts is disabled`** - Download the latest `Alfred-Install.exe` from GitHub Releases and run it again. The installer now calls `npm.cmd`/`npx.cmd` directly, so PowerShell execution policy should not block npm installs.

**npm global install fails with permission errors** - Re-run `Alfred-Install.exe` as Administrator, or install the CLI manually with `npm install -g`.

**Local `Node/` folders** - These are machine-local caches and are ignored by git. Fresh installs should use `setup.ps1` to install or detect Node.js instead of committing a Node runtime into the repo.
