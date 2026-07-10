# Alfred Install Audit — 2026-07-10

Audited by Claude Code (Fable 5). Method: knowledge-graph map of the repo (Graphify, AST-only, zero LLM tokens: 622 nodes / 1,099 edges / 30 communities in `graphify-out/`), line-level read of all installer scripts, **two real sandboxed install runs** against a fake `%USERPROFILE%` (transcripts in the session scratchpad: `run1.log`, `run2.log`), and inspection of the live machine's actual config end-state. No repo behavior was modified. One disclosure: the sandboxed runs re-registered the 10 MCP servers in the real `~/.codex/config.toml` (the Codex CLI resolves home via the Windows known-folder API and ignores env overrides) — net effect nil: same entries, each exactly once, pre-existing `node_repl` and `powerbi-modeling-mcp` untouched.

---

## 1. What Alfred actually is (verified, not README claims)

Alfred is **four things in one repo**, and only one of them is the installer:

| Component | Files | Share of code graph |
|---|---|---|
| **Toolchain installer** (the audit subject) | `Alfred-Install.ps1` (924 ln, bootstrap+CLIs+keys), `setup.ps1` (765 ln, prereqs+venv+portable tools), `Provision-Cursor.ps1` (802 ln, MCPs+skills+rules) | ~5 of 30 communities |
| Claude-API chat assistant ("Alfred CLI") | `backend/main.py` + helpers (`_call_anthropic`, `run_claude`, memory loading) | ~7 communities |
| Quant trading Flask plugin | `plugins/quant/*` | ~7 communities |
| Cloud growth loop + digest | `.github/workflows/alfred-growth-loop.yml`, `alfred_loop.py` | ~2 communities |

**Install chain:** `Alfred-Install.exe` → `Alfred-Install.ps1` (installs Git/Python/Node via winget→Scoop fallback, clones repo, prompts for API keys, writes repo-local `.claude/settings.json`) → `setup.ps1` (venv, `requirements/python-requirements.txt`, `requirements/npm-tools.txt`, portable gh/jq/pandoc/excel-mcp/az) → `Provision-Cursor.ps1` (the actual provisioner).

**Source of truth for what gets installed:**
- MCPs: `cursor/mcp.json` — 12 active server templates + 6 retired names. Placeholders (`${env:VAR}`, `${repoRoot}`, `${powerBiMcp}`…) resolved at provision time; servers with missing required secrets/commands are skipped with a printed reason.
- Skills: `skills/*.md` (31 synced, 2 skip-listed) + `skills/_packs/fabric/**` (12 folder skills).
- Rules: `cursor/rules/*.mdc` (5 files) + `cursor/AGENTS.shared.md`.
- CLIs: `requirements/npm-tools.txt` (claude, codex, lean-ctx-bin), `requirements/python-requirements.txt` (pandas, openpyxl, xlwings, excellm, pbi-cli-tool, csvkit, visidata, …).
- `requirements/alfred-tools.json` + `catalog-index.json` are **reference-only** manifests; `.github/scripts/validate_catalog.py` checks repo-internal consistency in CI. **Nothing validates machine state.**

Dependency health: npm tools and Python packages are unpinned (latest-at-install). Nothing looks abandoned; `excellm 1.2.0`, `pbi-cli-tool 3.11.1`, `pandas 3.0.3` present in the venv. Scripts are Windows-first (PowerShell 5.1+, winget→Scoop no-admin fallbacks, registry probing for Python) — cross-platform is explicitly out of scope, and **no bash-only/POSIX breakage exists** because there is no bash.

---

## 2. Coverage matrix (per category × target, with evidence)

Verdict on your core suspicion: **wrong for MCPs and skills, right for agents and plugins, mostly right for rules.**

| Category | Claude Code | Claude Desktop | Cowork | Cursor | Codex | Duplicated on re-run / across targets? |
|---|---|---|---|---|---|---|
| **MCP servers** | ✅ code + ✅ **picked up** — `claude mcp add --scope user` (`Provision-Cursor.ps1:511-530`); 11 servers live in `~/.claude.json`; all connected in the auditing session | ⚠️ code exists (`:534-572`), sandbox write works, but **live end-state = zero servers**: `claude_desktop_config.json` (rewritten by the app today 18:29) has no `mcpServers` key | n/a (Cowork uses Desktop connectors) | ✅ code + config present — 11 servers in `~/.cursor/mcp.json` (documented Cursor global MCP location) | ✅ code + config present — 10 `[mcp_servers.*]` blocks in `~/.codex/config.toml`, each once | **No.** Re-run is byte-identical (verified: md5-identical configs after run 2). Keyed upsert everywhere; retired names actively removed. |
| **Skills** | ✅ code + ✅ **picked up** — 44 dirs in `~/.claude/skills`; the `alfred-*` skills appear in this session's live skill list | ➖ no path (Desktop has no skills dir) | ✅ effectively — desktop-app agent sessions read `~/.claude/skills` (verified in this session) | ✅ code + location valid — 44 dirs in `~/.cursor/skills`, a documented user-level location (cursor.com/docs/skills) | ⚠️ lands in `~/.codex/skills` (legacy-compat path); Codex's current native home is `~/.agents/skills` | **Re-run: no** (deterministic overwrite + orphan cleanup `:647-655`). **Across targets: yes, by design** — the same 43 skills are written 3× and **Cursor reads all of `~/.cursor`, `~/.claude`, `~/.codex`, `~/.agents` skills dirs**, so Cursor sees every Alfred skill in triplicate. |
| **Rules** | ⚠️ only via `AGENTS.md` seeding, opt-in | ➖ no path | ➖ no path | ❌ **effectively never installed.** Global sync (`Sync-GlobalCursorRules:184-194`) targets `~/.cursor/rules`, which Cursor does **not** document reading (User Rules live in Settings GUI; project rules in `<repo>/.cursor/rules`). Worse, the sync only executes inside the lean-ctx branch (`:755-783`) and lean-ctx is not installed → live `~/.cursor/rules` contains only `graphify.mdc` (not Alfred's 5 rules). Project seeding (`:693-717`) works but requires `-ProjectPath`, which **no caller in the repo ever passes** | ➖ no path | n/a — nothing lands, so nothing duplicates |
| **Agents** | ❌ **no code path exists.** `~/.claude/agents` does not exist on this machine. Grep across all .ps1/.bat: zero writes to any agents dir | ❌ | ❌ | ❌ (`~/.cursor/agents` exists but empty; Cursor supports subagents in `.cursor/agents` — Alfred never writes it) | ❌ | n/a |
| **Plugins** | ❌ **no code path.** "Plugins" in Alfred = `plugins/quant`, an internal Flask trading app. Nothing touches Claude Code plugin/marketplace config or Cursor plugins | ❌ | ❌ (Cowork plugins on this machine came from the marketplace, not Alfred) | ❌ | ❌ | n/a |

Notes:
- The README promises "MCP servers → Cursor, Claude Code, Codex; Skills + rules → all three agents" — it never claims agents or assistant-plugins. So those two categories aren't broken code; they're **absent categories** wearing a misleading directory name (`plugins/`).
- Pickup was verified by end state + live behavior where possible (this Claude Code session lists Alfred's skills and has Alfred's MCPs connected). Cursor/Codex pickup is verified to the level of "files are in the documented locations"; I can't drive Cursor's agent from here.

---

## 3. Bug list (ranked by severity × how well it explains "not installing correctly")

1. **Rules never land anywhere Cursor reads, in the default flow.** Two stacked causes: (a) `Sync-GlobalCursorRules` writes to `~/.cursor/rules`, an undocumented location — Cursor's global rules are Settings-GUI text, project rules are `<repo>/.cursor/rules`; (b) the call is only reachable through the LeanCTX block (`Provision-Cursor.ps1:755-783`), and lean-ctx is missing, so it doesn't even run. Evidence: live `~/.cursor/rules` lacks all 5 Alfred rules. The only working path (`-ProjectPath` seeding → project `.cursor/rules` + `AGENTS.md`) is never invoked by `setup.ps1` (line 644 calls the provisioner with no args) or anything else. **Root cause: rules were designed as opt-in per-project but wired as if global sync existed.**
2. **No agents category, no assistant-plugins category** — not broken, *nonexistent* (see matrix). If Alfred is meant to be a one-stop shop for these, that's greenfield work, not a fix.
3. **Claude Desktop end-state failure with no detection.** The write code works (proven in sandbox run 1: "Wrote 10 managed server(s)" to the fake `%APPDATA%\Claude\`), but the live file has zero servers — the Desktop app rewrote its config (mtime today 18:29) and Alfred has no verification step to notice drift. Exit 0 was reported; end state is empty. **This is the poster child for "script exited 0 ≠ installed."**
4. **Silent dependency dropouts leave whole features off with exit 0.** Live machine: `lean-ctx` absent (it's in `npm-tools.txt`, so its install failed or predates the manifest) → LeanCTX MCP, hooks repair, *and* rule sync all silently skip. `bin/excel-mcp/mcp-excel.exe` absent (only `gh.exe` in `bin/`) → the `excel-mcp` server silently skips at provision (`run1.log`: "command not found on this machine"). The skip *reasons* are printed once and scroll away; nothing persists or re-checks.
5. **Skills are triple-written and Cursor reads all three roots** → every Alfred skill appears 3× to Cursor (`~/.cursor/skills`, `~/.claude/skills`, `~/.codex/skills` are all scanned per Cursor docs, plus `~/.agents/skills`). At best wasted context/listing noise, at worst confusing skill resolution. The modern cross-tool standard is **one** copy in `~/.agents/skills` (Alfred already uses it for the third-party taste-skill, and had to add `Remove-AlfredVendoredTasteSkills` to clean up exactly this class of duplicate — the pattern has bitten before).
6. **Codex skills land in a legacy path** (`~/.codex/skills`); Codex's native location is `~/.agents/skills` — fixing #5 fixes this for free.
7. **No `doctor`/verify command.** `validate_catalog.py` validates the repo's own JSON in CI; nothing anywhere lists what each assistant actually sees post-install. Every failure above survived because of this.
8. **Windows home-resolution inconsistency (latent).** `$HOME` in PowerShell does not follow `USERPROFILE` overrides, and the Codex CLI uses the known-folder API — scripts mixing `$HOME`, `$env:USERPROFILE`, `$env:APPDATA` (Provision does all three) behave inconsistently under redirected profiles/CI. Not the cause of your issue, but it made testing harder and will bite automation.
9. Minor: `Alfred-Install.ps1:831` overwrites (not merges) `.claude/settings.json` — repo-local scope only, so acceptable, but it would clobber any manual edits to that file. `.env.template` self-copy at `setup.ps1:633` is a no-op copying a file onto itself.

**What is *not* broken (verified):** MCP idempotency and dedup are genuinely correct — keyed merges for Cursor/Desktop JSON, remove-then-add for the `claude`/`codex` CLIs, `_retiredServers` cleanup, orphan-skill cleanup, secret-missing skip logic. Two consecutive sandbox runs produced byte-identical results. The failure pattern is **absence and silence**, not corruption.

---

## 4. Score vs. the "one-stop shop" promise

| Category | Verdict |
|---|---|
| MCPs | **Delivered** (Cursor, Claude Code, Codex), **silently rotted** for Claude Desktop. Server selection is current and sensible; skip-logic is good but ephemeral. |
| Skills | **Delivered** to all targets, with a redundancy design flaw (3 copies visible to Cursor) and no pickup verification. |
| Rules | **Not delivered** in practice. Dead global path + never-invoked project path. |
| Agents | **Vestigial/absent.** No inventory, no code path, no target dirs. |
| Plugins | **Absent as a category**; the word is used for an unrelated internal app. |

Net: Alfred is a good **MCP + skills provisioner** with strong idempotency, wearing a "one-stop shop" label it meets ~half of — and with zero ability to tell you which half worked on any given machine.

---

## 5. Redesign for 10× usefulness (concrete)

**a) One declarative manifest, keyed category × target.** Replace the four scattered sources (`cursor/mcp.json`, `skills/` glob, `cursor/rules/` glob, `npm-tools.txt`) with `alfred.manifest.json`:

```jsonc
{
  "items": [
    {
      "id": "excel-live", "kind": "mcp", "cost": "free-local",
      "profiles": ["data-analyst", "claude-heavy"],
      "spec": { "command": "${repoRoot}\\.venv\\Scripts\\python.exe", "args": ["-m", "excellm"] },
      "targets": { "cursor": true, "claude-code": true, "claude-desktop": true, "codex": true },
      "verify": { "type": "process-starts" }
    },
    {
      "id": "graphify", "kind": "cli+rule+skill", "cost": "free-local",
      "profiles": ["cursor-lite", "data-analyst", "claude-heavy"],
      "install": "uv tool install graphifyy",
      "targets": { "cursor": { "rule": "project" }, "claude-code": { "skill": "user" } }
    }
  ]
}
```
Because every item must declare a `targets` map, "we forgot skills for Cursor" becomes structurally impossible — an absent target is a visible `false`, not missing code. Adding/removing a tool is a data change; the installer is a small engine that reads the manifest.

**b) Idempotency & dedup by construction (keep + extend what exists).** The keyed-upsert pattern already used for MCPs becomes the engine's only write primitive: every item has a stable `id`; installs upsert by id; uninstalls remove by id. **Skills: write once to `~/.agents/skills/`** (the cross-tool standard read by Cursor, Claude Code, and Codex alike) and delete the `~/.cursor|.claude|.codex/skills` copies via the existing orphan-cleanup mechanism. That single change removes the 3× duplication and the Codex legacy path.

**c) `alfred doctor` — the missing half of the product.** A read-only command that renders the section-2 matrix live: for each manifest item × target, check (1) config entry present, (2) command/exe resolves, (3) where cheap, the server actually starts (`--help`/handshake), (4) skill dir present exactly once across the four skill roots. Persist the last report to `%LOCALAPPDATA%\alfred\doctor.json` so drift (like the Desktop wipe) is detected on next run: "excel-mcp was present on 2026-07-01, missing now." Run it automatically at the end of every install — this converts every "silent skip" bug into a visible line item.

**d) Profiles, defaulting to your actual usage.** `cursor-lite` (default): MCPs + skills + rules into Cursor only; nothing that requires Claude API tokens at runtime; `claude` CLI still installed for occasional use but no Claude-invoking hooks/loops. `data-analyst`: adds excellm, ExcelMcp, powerbi-modeling-mcp, duckdb, pbi-cli, fabric skill pack, graphify. `claude-heavy`: adds Codex/Desktop targets, Alfred chat backend, growth loop. Install = `alfred install --profile cursor-lite,data-analyst`.

**e) Cost tags.** Every manifest item carries `cost: free-local | api-tokens | api-optional`. Everything Alfred currently ships is free-local at runtime except: the Alfred chat backend (Anthropic API), the growth loop (API), fal-ai (paid key), context7/parallel-search (free tier, key optional). `--profile cursor-lite` excludes `api-tokens` items by default; `doctor` prints the tag so you always know what can bill you.

**f) Update/uninstall.** Track ownership in `%LOCALAPPDATA%\alfred\state.json` (item id → target → what was written where, when). `alfred remove <id>` / `alfred remove --all` then delete exactly those entries via the same keyed primitive — no orphans, works per-target. The `_retiredServers` list becomes just "items removed from the manifest," handled automatically by diffing state vs. manifest.

**g) Windows correctness (already decent) — codify it.** One `Resolve-Home` helper used everywhere instead of mixed `$HOME`/`$env:USERPROFILE`; keep the winget→Scoop no-admin ladder; add the `if __name__ == "__main__"` guard note for any Python entry points (the multiprocessing spawn error seen during graph build is the generic Windows trap).

---

## 6. Excel & Power BI readiness (this machine)

**Registry check:** Anthropic's MCP connector registry returned **zero** results for excel/spreadsheet/power-bi/fabric — no hosted connectors exist for this stack. Local MCP servers are the correct architecture, and Alfred's picks are current and well-chosen. Verified state:

| Capability | Status | Evidence |
|---|---|---|
| Live-Excel MCP (`excellm`) | ✅ installed + registered in Cursor/Claude/Codex | venv has excellm 1.2.0; server in all three configs |
| Closed-workbook Excel MCP (`ExcelMcp`) | ❌ **exe missing** — `bin/excel-mcp/` doesn't exist, server skipped at provision | `run1.log` skip line; `bin/` contains only gh.exe |
| Power BI Modeling MCP | ✅ registered; VS Code extension 0.4.0 present, exe path valid | `~/.claude.json` entry + extension dir verified |
| pbi-cli | ✅ venv 3.11.1 | version check |
| duckdb MCP (SQL over CSV/Parquet/Excel exports) | ✅ registered | configs |
| Python data stack | ✅ pandas 3.0.3, openpyxl 3.1.5, xlwings 0.36.6 (+ csvkit, visidata, python-docx, pypdf) | venv version checks |
| xlsx authoring skills | ✅ `alfred-excel-live-editing`, `alfred-excel-financial-models` in all skill dirs; Cowork additionally has the Anthropic `xlsx` plugin skill | dir listings + live session |
| Fabric/Power BI skill pack | ✅ 12 folder skills (semantic-model-*, powerbi-report-*, dataflows-*) synced | run log + `~/.claude/skills` |
| Excel itself | ✅ Office16 EXCEL.EXE present | path check |
| **Power BI Desktop** | ⚠️ **not found** in `Program Files` or WindowsApps probing — pbi-cli and the modeling MCP need a running Desktop instance. Verify/install (Store or `winget install Microsoft.PowerBI`) | path checks came back empty |
| ODBC/drivers | Not needed for current stack (duckdb reads files directly; modeling MCP talks to Desktop's local AS instance) | — |

**Actions:** re-run the ExcelMcp download step (or add it to the manifest with a `verify` so doctor flags it), confirm Power BI Desktop, install `lean-ctx-bin` or retire it deliberately. Graphify's `office` extra is **complementary, not overlapping**: it parses `.docx`/`.xlsx` *into the knowledge graph* for querying/cross-referencing (read-side); excellm/openpyxl/xlwings remain the authoring/editing side. Worth enabling for a finance-docs folder graph, not a replacement for anything above.

---

## 7. Graphify decision

**Recommendation: yes — adopt as a first-class manifest item.** Rationale: it directly serves the cost constraint (tree-sitter AST extraction is local and free; the only LLM use is optional doc/image extraction), and it replaces per-session brute-force re-reading of codebases in Cursor with graph queries. It proved itself in this audit: the Alfred graph (622 nodes, 1,099 edges) was built in seconds for zero LLM tokens and immediately isolated the 5 installer communities from the ~25 unrelated ones.

Current machine state: already installed globally (uv tool `graphifyy`; hook-guards in `~/.claude/settings.json`; `graphify` skill in `~/.claude/skills`; `~/.cursor/rules/graphify.mdc`).

- **Scope: project-level, not user-global, for Cursor.** `graphify cursor install --project` writes `<repo>/.cursor/rules/graphify.mdc` — a *documented* pickup location; the existing global `~/.cursor/rules/graphify.mdc` sits in the same undocumented directory as Alfred's rules and may not load at all. Per-repo also means the rule only fires where a graph exists (`graphify-out/`), and it travels with the repo. Fold it into the same per-project seeding step as Alfred's rules (`alfred seed <repo>`).
- **Manifest entry:** `kind: cli+rule+skill`, `cost: free-local`, profiles: all. Install: `uv tool install graphifyy`; per-project: rule seed + optional initial `graphify <repo>` build; `doctor` check: `graphify --version` + rule file present in seeded repos.
- **`office` extra:** include in the `data-analyst` profile, pointed at the finance folder, with the note above about read vs. author.

---

## 8. Prioritized action plan

**Quick fixes (hours, do first):**
1. Move `Sync-GlobalCursorRules` out of the lean-ctx branch — but retarget it: stop writing `~/.cursor/rules` (dead); instead print/store guidance and rely on per-project seeding.
2. Wire `-ProjectPath` into the default flow: `setup.ps1` should seed rules + `AGENTS.md` + `graphify.mdc` into a configurable list of active repos (start with `C:\Users\Andre\boostly`), or add an `alfred seed <repo>` entry point.
3. Skills: write once to `~/.agents/skills`, remove the three per-tool copies (reuse the orphan-cleanup code to delete existing `alfred-*` dirs from `.cursor/.claude/.codex` skill roots).
4. Fix the two silent dropouts on this machine: install `lean-ctx-bin` (or retire LeanCTX from the manifest deliberately) and re-run the ExcelMcp download; verify Power BI Desktop presence.
5. Add a minimal `alfred doctor` (even 100 lines of PowerShell rendering the section-2 matrix) and run it at the end of every install. This single item would have caught bugs 1, 3, and 4.

---

## Implementation log — 2026-07-10 (v3.1.0)

The audit above was performed against a working tree that was 29 commits behind `origin/main`; v3.0.x had already removed lean-ctx entirely and un-gated the rules sync. The remaining confirmed bugs were fixed on top of current main:

| Audit item | Status | Change |
|---|---|---|
| Rules never land where Cursor reads (bug #1) | **Fixed** | `Sync-GlobalCursorRules` (dead `~/.cursor/rules` target) deleted; per-project seeding now runs for `-ProjectPath`, `-SeedProjects`, and `ALFRED_PROJECT_PATHS` in `.env` (semicolon-separated) on every provision. `Invoke-ProjectSeed` copies `cursor/rules/*.mdc`, `AGENTS.md` (if absent), `.cursorrules`, and the graphify rule into each repo. |
| Skills triple-copied, Cursor lists ×3 (bug #5/#6) | **Fixed** | Skills sync **once** to `~/.agents/skills` (cross-tool standard read by Cursor, Claude Code, Codex). `Remove-LegacySkillCopies` deletes the old per-tool copies. Exception: `impeccable` stays per-harness (its docs hard-code harness paths). |
| No verification / silent drift (bugs #3/#4/#7) | **Fixed** | New `Alfred-Doctor.ps1`: per-target MCP matrix (expected-vs-registered, retired leftovers, duplicates), single-copy skills check, per-project rules check, CLI + Excel/PBI stack checks; saves `%LOCALAPPDATA%\alfred\doctor.json` and reports drift vs the previous run. Runs automatically at the end of every provision (`-SkipDoctor` to opt out). |
| Graphify first-class (Phase 7) | **Done** | Provision installs graphify via `uv tool install graphifyy` when missing (free/local), and seeds the project-scoped Cursor rule (`graphify install --platform cursor` in each seeded repo). |
| ExcelMcp exe missing (Phase 6) | **Open** | Binary download blocked by session policy (external exe). Re-run `setup.ps1` (its step at line ~446) or download manually per its instructions; doctor flags it until present. |
| Power BI Desktop absent (Phase 6) | **Open** | Doctor warns; install via Store or `winget install Microsoft.PowerBI` if this machine should run PBI locally. |
| Agents / plugins categories | **Deferred** | Still absent by design; manifest redesign below is the vehicle for adding them honestly. |

Verified on this machine post-implementation (doctor: **HEALTHY**, 2 warnings = the two Open items): Cursor 14/14, Claude Code 13/13 (+1 OAuth-deferred by design), Claude Desktop 14/14 restored, Codex 14/14; 50 skills single-copy; boostly seeded 13 rules + AGENTS.md + graphify.

**Larger redesign (days, in order):**
6. `alfred.manifest.json` keyed category × target × profile × cost; refactor `Provision-Cursor.ps1` into a manifest-driven engine (its keyed-upsert primitives survive as-is).
7. State tracking + `alfred remove` (clean uninstall per item per target).
8. Profiles with `cursor-lite` as default; cost tags enforced by profile filters.
9. Decide agents & plugins honestly: either implement them (agents → `~/.claude/agents` + per-repo `.cursor/agents`; plugins → Claude Code marketplace add) or delete the words from the README and rename `plugins/quant` to `apps/quant`.
10. Claude Desktop: either monitor via doctor (re-provision when the app wipes config) or drop the target and let Desktop users rely on Cowork connectors.
