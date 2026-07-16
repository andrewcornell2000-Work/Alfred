# Alfred Pack 2.0

**Alfred is a Windows installer and toolchain pack** — not a chat app you use every day.

Install it once — **git clone on work/managed machines**, `Alfred-Install.exe` on personal ones (see [Install](#install)) — and it wires your PC for AI work:

- **MCP servers** → Cursor, Claude Code, Codex (Power BI, Excel, GitHub, …)
- **Skills + rules** → all three agents globally
- **CLIs** → Claude, Codex, gh, pbi, jq, …
- **Discovery loop** → nightly search for new tools you wouldn't think to look for

**Day-to-day:** work in **Cursor**. Just ask. The pack is already provisioned.

**Maintenance:** re-run the installer or `run-alfred.bat` to update and re-provision — see [PACK.md](PACK.md).

---

## Install

Pick the path that fits the machine.

### Work / managed machine — git clone (recommended)

Use this on any corporate or locked-down PC. There is **no compiled binary**, so there's nothing for security tooling (EDR / SmartScreen) to flag as an unknown, unsigned executable — `git` is an already-trusted tool, and you (or IT) can read every line before it runs.

```powershell
git clone https://github.com/andrewcornell2000-Work/Alfred.git "$env:USERPROFILE\Alfred"
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Alfred\Alfred-Install.ps1"
```

In the wizard, choose **Work machine** — it provisions the analyst working set (Power BI, Excel, DuckDB analytics, doc/graphify tools, and design) and leaves out the heavy browser-automation and cloud-dev buckets. Git must already be present (it is on most managed machines). If Python/Node aren't, the script installs them per-user where policy allows, or prints the exact manual step.

### Personal machine — installer .exe

The one-double-click bootstrapper for a bare machine — it installs Git, Python, and Node for you:

```text
https://github.com/andrewcornell2000-Work/Alfred/releases/latest/download/Alfred-Install.exe
```

Save it, double-click, and choose **More info → Run anyway** if SmartScreen prompts. Pick **Personal machine** in the wizard for the full toolset. The exe is unsigned, so it may be flagged on locked-down machines — which is exactly why work machines should use the git-clone path above.

### Then, on either machine

The installer checks/installs Git, Python, Node 18+, and the Claude/Codex CLIs, creates `.venv`, runs `Provision-Cursor.ps1` to register MCP servers + skills into **Cursor, Claude Code, and Codex**, and drops a desktop shortcut that runs **update + provision** (not a chat window). Then log in once:

```powershell
claude auth login
codex login
```

**Updating (both machines):** just run the desktop shortcut (or `run-alfred.bat`) — it does `git pull` + re-provision. No exe needed to update. All steps are idempotent.

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
seeds `<repo>/.cursor/rules/*.mdc`, `AGENTS.md`, the graphify rule, and **mirrors
`<repo>/.cursor/agents/*.md` → `<repo>/.claude/agents/`** (Cursor + Claude Code
subagent parity) into each.

Third-party design skills (when missing): `ui-design-brain`, `frontend-design`,
`accessibility`, `Leonxlnx/taste-skill`. Boostl projects also ship
`.cursor/skills/between-steps-ux/` in-repo — see `skills/boostly-jean-paul-design.md`.

Re-provision after pulling updates:

```powershell
# Omit -SkipCloseAgentApps to close Cursor/Claude/ChatGPT first (cleanest hook write)
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -SkipCloseAgentApps
```

Verify what each tool actually sees (runs automatically after provisioning):

```powershell
powershell -ExecutionPolicy Bypass -File Alfred-Doctor.ps1
```

Doctor checks MCP registration per target (Cursor / Claude Code / Claude Desktop /
Codex), single-copy skills, per-project rules, CLIs, and the Excel / Power BI
stack, then diffs against the previous report (`%LOCALAPPDATA%\alfred\doctor.json`)
so config drift is called out — "the script exited 0" is never trusted as success.
Doctor also fails on **plaintext tokens** in any client config (rotate + move to
`.env`) and on **duplicate** server entries.

### Pick what you install: MCP buckets (why your RAM stays sane)

Every registered MCP server is a live process in **each** client you run (Cursor,
Claude Desktop chat, Cowork/Claude Code, Codex), and on Windows each `npx`/`uvx`
server drags a `cmd → node → cmd → conhost → node` wrapper chain. Registering the
full set on every machine is what makes Task Manager fill with Node/cmd/conhost —
and you rarely need all of it (a laptop that never touches Power BI shouldn't run
the Power BI server).

So every server in `cursor/mcp.json` carries a `_bucket` category, and you choose
which buckets install **per machine**:

| Bucket | Servers | For |
|---|---|---|
| `core` *(always on)* | filesystem, github, context7 | general dev |
| `office365` | outlook-calendar, excel, excel-mcp | Excel + Outlook calendar (`ms-365` Graph MCP quarantined — device-code forbidden) |
| `powerbi` | powerbi-modeling-mcp | Power BI model editing |
| `web` | playwright, parallel-search, firecrawl, fetch | browsing, research, scraping |
| `data` | duckdb, markitdown, longhand | local data + history |
| `mediagen` | fal-ai, magic | image/video/audio + UI generation |
| `cloud` | supabase, vercel | web-app backends |

Choose them when you install — the provisioner shows an interactive picker — or
non-interactively:

```powershell
powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1 -Buckets "core,office365,powerbi"
# or "all"; the choice is saved to ALFRED_BUCKETS in .env so re-provisions are consistent
```

**Skills follow the same buckets.** `skills/_buckets.json` maps each Alfred skill
(and the vendored `_packs/fabric` set) to a bucket, so selecting `powerbi` also
installs the Power BI / Power Query skills and the Fabric pack, and de-selecting a
bucket prunes its skills from `~/.agents/skills` on the next provision. Unlisted
skills fall back to `core` (always installed).

Notes:
- `excel` (ExceLLM, live workbooks) and `excel-mcp` (ExcelMcp, closed-file COM) look
  redundant but are complementary — both live in `office365`.
- Real duplication (e.g. `powerbi-modeling-mcp` also arriving via a Claude Code
  plugin) is flagged by Doctor; pick one source.
- Running Cursor **and** Claude Desktop at once still doubles whatever you selected —
  that's inherent to running two clients; close the one you're not using when RAM matters.

### Reset / clean slate

`Alfred-Reset.ps1` removes every Alfred-managed MCP registration from all four
clients (prompts first; backs up each config to `<file>.reset.bak`):

```powershell
powershell -ExecutionPolicy Bypass -File Alfred-Reset.ps1                       # reset only
powershell -ExecutionPolicy Bypass -File Alfred-Reset.ps1 -KillProcesses        # + free RAM now
powershell -ExecutionPolicy Bypass -File Alfred-Reset.ps1 -AndReinstall -Yes    # reset-and-reinstall
```

Use `-AndReinstall` when a machine is in a broken/duplicated state: it tears
everything down, then re-provisions cleanly from the canonical template.

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

**Fabric / Azure auth** - Fabric skills need browser/SSO `az login` only — never `az login --use-device-code`. Policy: `skills/_packs/common/AUTH-HARD-RULES.md`. After update/install, re-run `Provision-Cursor.ps1` so the quarantined `ms-365` MCP is removed from Cursor configs.

**Azure / AKS device-code blocked** - Same rule: browser/SSO `az login` only — never `az login --use-device-code`. AKS kubeconfig remediation is **optional** (kube/AKS only — skip if you only use Fabric): `powershell -ExecutionPolicy Bypass -File scripts\Fix-AzureKubeAuth.ps1` (runs `kubelogin convert-kubeconfig -l azurecli`). CI/CD should use a service principal or managed/workload identity, not a user account.
