# Repo Scout — GitHub triage (skills-first)

Evaluate a GitHub repo for Andrew's three goals: **web apps**, **mobile games**, **logistics/warehouse analyst** work.

**Run this skill in the current agent.** Do **not** launch `repo-*` subagents or Task fan-out. Do not install, clone, or provision during triage.

## Auto-route

When Andrew pastes a **GitHub repo URL** (or `owner/repo`) to look at / check / evaluate — follow this skill and return the 8-section Verdict Card. See `cursor/rules/repo-scout-routing.mdc`.

```text
https://github.com/owner/repo
look at this https://github.com/owner/repo
is this worth adding?
```

**Focus:** `all` | `web` | `games` | `logistics` (default `all` — still always run safety + overlap).

## Workflow (sequential, one agent)

1. **Intake**
2. **Safety** checklist
3. **Stack overlap** checklist
4. **Lens scores** (web / games / logistics — score all three; deepen the Focus lens)
5. **Synthesize** Verdict Card

---

## 1. Intake

1. Parse → `owner/repo` + HTTPS URL.
2. Fetch facts (`gh repo view` → GitHub MCP → WebFetch README):
   - Description, topics, license, archived?, default branch, pushed_at, stars
   - README ≤200 lines; SECURITY.md if exists
   - Manifest sniff: `package.json`, `pyproject.toml`, MCP/server hints
3. Record:

```text
REPO: owner/repo
URL: https://github.com/owner/repo
SUMMARY: <one sentence>
LANES: web | games | logistics | mcp | devtools | mixed
SIGNALS: <keywords>
LAST_ACTIVE: <date or "stale >12mo">
```

Do **not** clone unless Andrew explicitly asks.

---

## 2. Safety checklist

Inspect in order:

1. License, archived, fork, `pushed_at`, issues trend
2. Trust — org vs solo, SECURITY.md, signing
3. Install path — `npx` / `uvx` / `pip` / docker / `curl|bash` / `irm` / unsigned `.exe`
4. Scripts — `postinstall`, `preinstall`, CI on PR vs push
5. MCP/CLI permissions — filesystem scope, shell, network, env secrets
6. Secrets in repo — committed `.env`, example tokens

**BLOCK (cannot ADOPT):**

- `curl | bash` / `irm` without checksum or signed artifact
- Postinstall fetches unsigned binaries
- MCP wants full `C:\` or entire profile without reason
- Obfuscated single-file server with shell + network
- Archived + no maintainer + known critical issues

Official vendors (Microsoft, Supabase, Vercel, GitHub org) = lower scrutiny.

Capture: Risk LOW|MEDIUM|HIGH|BLOCK; safe to trial; install mechanism; admin?; API keys (names only); data leaves machine?

---

## 3. Stack overlap checklist

Read before judging (Alfred repo):

| File | Purpose |
|------|---------|
| `cursor/mcp.json` | MCP servers + `_bucket` |
| `requirements/alfred-tools.json` | CLIs |
| `memory/routing-rules.md` | Capabilities |
| `skills/_buckets.json` + `skills/*.md` | Skills |
| `agents/README.md` | Subagents (minimal roster) |
| `memory/discovered-tools.md` | Prior candidates |

Classify:

| Class | Definition |
|-------|------------|
| DUPLICATE | Same job, different package — incumbent wins |
| PARTIAL | Overlaps subset; one distinct feature remains |
| COMPLEMENT | Designed to pair (documented in Alfred) |
| NEW | No equivalent |

**Known complements (never DUPLICATE):** `excel`+`excel-mcp`; `context7`+`parallel-search`+`fetch`; `powerbi-modeling-mcp`+Fabric packs.

Penalize DUPLICATE of core: github, context7, filesystem, playwright, duckdb.

---

## 4. Lens scores (0–5 each)

### Web apps

Andrew stack: Next.js App Router, React, TS, Supabase, Vercel, `design-agent` for UI.

| Score | Meaning |
|------:|---------|
| 5 | Saves days on next app shipped |
| 3 | Useful for one project type |
| 1 | Thin web angle |
| 0 | Not web-related |

### Mobile / games

Engines: Unity, Godot, Unreal, Phaser, web-first. Indie/small-team scope.

| Score | Meaning |
|------:|---------|
| 5 | Clear win for next game |
| 3 | Useful for one game type |
| 1 | Generic gamedev |
| 0 | Not game-related |

### Logistics / analyst

Throughput, labour, inventory, commercial, Excel/PBI/SharePoint, SQL reconciliation.

Incumbent skills: excel/powerbi/data/labour/sharepoint, `dlp-doctor`.

| Score | Meaning |
|------:|---------|
| 5 | Weekly warehouse/commercial reporting improves |
| 3 | Occasional sub-domain use |
| 1 | Generic analytics, no logistics language |
| 0 | Wrong domain |

---

## 5. Verdict Card (required 8 sections)

```markdown
## Repo Scout — Verdict Card

| Field | Value |
|-------|-------|
| Repo | owner/repo |
| URL | … |
| Verdict | **ADOPT** \| **TRIAL** \| **SKIP** |
| Confidence | high \| medium \| low |

### 1. One-liner
…

### 2. Safety
Risk: LOW/MEDIUM/HIGH/BLOCK — …

### 3. Stack overlap
Class: DUPLICATE/PARTIAL/COMPLEMENT/NEW — …

### 4. Value scores
| Lens | 0–5 | One-line why |
|------|-----|--------------|
| Web apps | | |
| Mobile games | | |
| Logistics analyst | | |

### 5. Genuine help vs overlap
…

### 6. Try asking (if score ≥3 on any lens)
1. "…"

### 7. Risks / blockers
- …

### 8. Next step
- **ADOPT/TRIAL:** PoC (15–30 min) + Alfred files to touch
- **SKIP:** one-line reason
```

### Verdict logic

| Verdict | Criteria |
|---------|----------|
| **SKIP** | safety BLOCK **OR** DUPLICATE with no delta **OR** stale **OR** all lenses ≤1 |
| **TRIAL** | safe enough + score ≥3 on one lens + (PARTIAL or needs PoC) |
| **ADOPT** | no BLOCK + (NEW or COMPLEMENT) + score ≥4 on one lens + maintained |

**Hard rule:** any BLOCK → cannot ADOPT (TRIAL only if Andrew accepts risk).

### Anti-patterns

- Install / provision during triage
- ADOPT without overlap check
- Score 5 without Andrew-specific "Try asking"
- Launching `repo-*` or other specialist subagents for this workflow

### After ADOPT / TRIAL (owner approves)

1. `cursor/mcp.json` + `requirements/mcp-tools.md` if MCP
2. `alfred-tools.json` if CLI
3. `skills/` + `skills/_buckets.json`
4. `requirements/safety-gates.md` if destructive
5. `memory/discovered-tools.md`
6. `Provision-Cursor.ps1 -SkipCloseAgentApps`
