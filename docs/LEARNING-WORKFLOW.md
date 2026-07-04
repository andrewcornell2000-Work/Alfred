# Learning Workflow (Cursor + Cloud Agents)

Alfred learns new capabilities through **controlled sessions** — not automatic blind installs.

## Secure review pipeline

```
Discovered item
  → source validation (official > verified community > untrusted)
  → security review (license, scripts, permissions, secrets)
  → duplication check (catalog-index + mcp.json + review-queue)
  → test install (optional)
  → manual or trusted auto-approval
  → staged update (repo commit)
  → global install (Provision-Cursor.ps1 on user machine)
  → verification (Validate-Install.ps1)
  → update log (memory/learning-log.md)
```

**Cloud agents may:** search trusted sources, summarize tools, propose candidates, flag security concerns.

**Cloud agents may NOT:** bypass review, auto-approve untrusted packages, create duplicate skills, or run endless web searches.

Review queue: `requirements/review-queue.json`  
Validator: `python .github/scripts/review_candidate.py <candidate.json>`

### Stop conditions

- Max **3** web searches per session · Max **5** candidates per run
- Stop if already `installed`, `rejected`, or `duplicate`
- Stop if security review unresolved

---

## When to learn (do search + write)

Trigger learning when the user explicitly asks to:

- Add a new MCP, CLI, or skill to the pack
- Research a tool for finance/office/Power BI workflows
- Update Alfred routing, rules, or manifests
- Promote a `candidate` entry in `requirements/discovered-tools.md`

Use **Dev Portal** (Alfred menu 5) or a Cursor chat in this repo with a clear mission.

## When NOT to learn (no web search, no new files)

- Normal coding, debugging, or refactoring in a project
- Questions answerable from repo files or training knowledge
- "Explain how X works" unless X is a new external tool to install
- Every session startup — no automatic discovery runs
- Duplicating an existing skill with a slightly different name

---

## Cursor session playbook

### 1. Orient (read only, no search yet)

```text
Read: docs/ALFRED-STRUCTURE.md
Read: requirements/catalog-index.json
Read: cursor/mcp.json (check for duplicates)
Read: requirements/discovered-tools.md
Read: memory/active-projects.md (if continuing prior work)
```

### 2. Choose one mission

Pick **one** deliverable:

| Mission | Output |
|---------|--------|
| DISCOVER MCP | New server in `cursor/mcp.json` + `mcp-tools.md` + skill, **or** candidate in `discovered-tools.md` |
| DISCOVER CLI | Manifest entry + `alfred-tools.json` + skill, **or** candidate |
| SHIP candidate | Promote existing candidate to installed + skill |
| IMPROVE skill | Update existing `skills/*.md` (preferred over new file) |
| CATALOG refresh | Fix stale entries, merge duplicates — no new tools |

**Never edit** finance/domain skills unless explicitly asked: `cash-flow*`, `labour*`, `data-*`, `excel-financial*`, `powerbi-*`, `powerquery-*`.

### 3. Research (controlled web search)

Search only when the mission needs current external facts:

- **DISCOVER missions:** 1–3 targeted searches (not a minimum quota)
- **IMPROVE / CATALOG:** search only if verifying a version or URL
- **Code tasks:** no search

In Cursor use `parallel-search` or `fetch` MCP. In Alfred CLI, Tavily runs automatically only for `SEARCH` category or explicit recency keywords.

Log what you searched in `memory/learning-log.md`.

### 4. Build (update before create)

Before `write_file`:

1. Check `catalog-index.json` — update existing slug if overlap
2. Check `skills/` for a file on the same topic — **merge**, don't fork
3. Every deliverable needs **"Try asking:"** prompts Andrew can paste into Cursor

Write locations:

| Asset | Path |
|-------|------|
| Skill | `skills/<name>.md` |
| MCP | `cursor/mcp.json` + `requirements/mcp-tools.md` |
| CLI | `requirements/npm-tools.txt` or `python-requirements.txt` + `alfred-tools.json` |
| Candidate | `requirements/discovered-tools.md` |

Never commit API keys. Use `${env:VAR}` + `_requires` in MCP template.

### 5. Record

- `memory/learning-log.md` — what changed and why
- `memory/discoveries.md` — only for genuine breakthroughs
- `memory/active-projects.md` — next mission (one line)
- Optional instinct: `python scripts/instinct-cli.py record ...`

### 6. Validate and commit

```powershell
python .github/scripts/validate_catalog.py
git add [specific files]
git commit -m "Learn: <what you shipped and why>"
git push
```

Re-run `Provision-Cursor.ps1` locally to pick up MCP/skill changes.

---

## Skill format

```markdown
# Skill Title

One paragraph: when to use this skill.

## When to use
- Bullet triggers

## Approach
1. Numbered steps

## Try asking:
- "Concrete prompt Andrew can paste"
- "Another example"
```

Keep skills under ~150 lines unless the domain requires more. Link to `skills/mcp-routing.md` instead of copying MCP tables.

---

## Deprecated: GitHub Actions loop

GitHub Actions learning workflows are **removed**. Use **Cursor Cloud Agents** per `docs/CURSOR-CLOUD-AGENT.md`.

Historical prompt: `docs/archive/ALFRED_LOOP_PROMPT.md` · Archived script: `.github/archive/alfred_loop.py`

---

## Anti-patterns

| Bad | Good |
|-----|------|
| New `agent-*` skill for every technique | Update `skills/agent-playbook.md` |
| 5+ web searches per session | 1–3 targeted queries, then write |
| Duplicate MCP in `cursor/mcp.json` | Check template first |
| Auto loop commits without review | Cursor session + human review + provision |
| Copy MCP routing into every skill | Link to `skills/mcp-routing.md` |
