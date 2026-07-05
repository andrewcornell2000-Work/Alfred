# Alfred Structure

Short map of how Alfred is organized. Read this before adding rules, skills, or MCPs.

## Day-to-day

**Work in Cursor.** MCPs, skills, and rules are provisioned globally by `Provision-Cursor.ps1`.

Alfred CLI (`run-alfred.bat`) is for Control Tower, updates, and Dev Portal — not primary coding.

---

## Instruction layers (precedence)

| Layer | Location | Scope | Notes |
|-------|----------|-------|-------|
| Cursor rules | `cursor/rules/*.mdc` | Provisioned to Cursor | `00-agent-tooling.mdc` always on; `lean-ctx.mdc` optional |
| Repo root rules | `.cursorrules` | This repo in Cursor | Points to native tools + structure doc |
| Agent guidelines | `AGENTS.md`, `CLAUDE.md` | All coding agents | Keep in sync; no duplicate long prose |
| lean-ctx reference | `LEAN-CTX.md`, `skills/lean-ctx.md` | Optional compression | Native tools remain default |
| MCP routing | `skills/mcp-routing.md` | Task-specific MCP choice | Single source for decision table |
| Memory | `memory/*.md` | Alfred CLI context injection | Hot files: `recent-context.md`, `current-focus.md` |

**Do not duplicate** MCP routing tables or lean-ctx mandates in new files — link to the sources above.

---

## Skills

| Location | Loaded by Alfred CLI? | Purpose |
|----------|----------------------|---------|
| `skills/*.md` | Yes (keyword match, ≥2 hits) | Domain + agent how-to skills |
| `skills/_packs/**/SKILL.md` | No (provisioned only) | Fabric / multi-file packs |
| `skills/_vendor/**` | No (provisioned only) | Third-party bundles (e.g. impeccable) |
| `skills/_archive/**` | No | Deprecated skills (reference only) |

### Adding or updating a skill

1. Search `skills/` and `requirements/catalog-index.json` — **update existing** before creating new.
2. One skill per domain; include **"Try asking:"** examples.
3. Never create `skills/lean-ctx.md` or duplicate `mcp-routing` as skills (covered by rules).
4. Never write `skills/taste-*.md` (use upstream install).
5. Run `python .github/scripts/validate_catalog.py` after catalog changes.

### Consolidated agent guidance

Use **`skills/agent-playbook.md`** for reasoning, token discipline, and loop recovery. Detailed archived skills live in `skills/_archive/agent/` if needed.

---

## MCPs and tools

| File | Role |
|------|------|
| `cursor/mcp.json` | **Source of truth** MCP template |
| `requirements/mcp-tools.md` | Human-readable catalog |
| `requirements/alfred-tools.json` | CLI/package manifest |
| `Provision-Cursor.ps1` | Writes user-scope configs; skips servers missing keys/commands |

**16 domain MCPs** in template (+ lean-ctx merged at provision). Tavily is **not** an MCP — Alfred CLI calls it directly.

Retired (do not re-add): `sequential-thinking`, `memory`, `time`, `codegraph`, `sqlite`.

---

## Web search policy

| Context | When to search | Tool |
|---------|----------------|------|
| Alfred CLI chat | Category `SEARCH`, brain `needs_search`, or explicit recency keywords | Tavily API |
| Alfred CLI chat | Timeless explain/plan/code questions | **No search** |
| Cursor agent | Live news, versions, current docs | `parallel-search` MCP **or** user asks |
| Cursor agent | Library API docs | `context7` only |
| Cursor agent | Known URL | `fetch` once |
| Learning workflow | New tool/MCP research for catalog | 1–3 targeted searches, then write skill |

**Do not** search automatically on every question mark or "what is" phrasing.

Details: `skills/web-search.md`, `docs/LEARNING-WORKFLOW.md`.

---

## Learning workflow

| Method | When |
|--------|------|
| **Cursor session** | You ask Cursor to research and ship a tool/skill (primary) |
| **Dev Portal** | Menu 5 — discuss Alfred behavior changes before dispatch |
| **Instincts** | Session lessons via `scripts/instinct-cli.py` |
| **GitHub loop** | **Deprecated** — manual `workflow_dispatch` only for emergencies |

Full playbook: **`docs/LEARNING-WORKFLOW.md`**

---

## Prompts and routing code

All in `backend/main.py`:

- `ALFRED_BRAIN_PROMPT`, `GENERAL_RESPONSE_PROMPT`, `ALFRED_EXECUTOR_PROMPT`
- `alfred_brain()`, `_should_search()`, `load_relevant_skills()`
- Keyword lists: `DANGEROUS_KEYWORDS`, `LEARNING_MODE_KEYWORDS`, routing keywords

Docs: `memory/routing-rules.md`, `CLAUDE.md`.

---

## Avoiding slowness

- One primary tool path per task (`skills/mcp-routing.md`)
- Native Read/Grep before MCP for repo files
- lean-ctx optional — never force on every call
- Don't load overlapping skills (check catalog before adding)
- Don't run broad repo scans without a scoped target
- Alfred brain routing uses Claude CLI today (~8–12s); API key speeds chat path

---

## Maintenance checklist

After changing routing, MCPs, or skills:

1. Update `memory/routing-rules.md` and `CLAUDE.md` if behavior changed
2. Update `requirements/catalog-index.json` for new slugs
3. Run `python .github/scripts/validate_catalog.py`
4. Re-run `Provision-Cursor.ps1` on your machine
