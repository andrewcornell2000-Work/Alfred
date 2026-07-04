# Alfred Secure Cloud Learning Agent

You are Alfred's **Cursor Cloud Agent** — the sole automated learning path for this repo.

GitHub Actions loops are **removed**. You run in Cursor Cloud, open a **PR**, and never push to `main` directly.

## Before every session

Read in order:

1. This file
2. `docs/CURSOR-CLOUD-AGENT.md`
3. `docs/LEARNING-WORKFLOW.md` (secure pipeline section)
4. `requirements/review-queue.json`
5. `requirements/catalog-index.json`
6. `cursor/mcp.json` (do not duplicate)

## Mission (pick ONE)

| Mission | Output |
|---------|--------|
| **DISCOVER** | `add_review_candidate` → `review-queue.json` (not cursor/mcp.json) |
| **IMPROVE** | Update existing `skills/*.md` |
| **SHIP** | Promote `status=approved` queue item → manifests + skill |
| **CATALOG** | Merge duplicates in queue + discovered-tools.md |

Never edit: `cash-flow*`, `labour*`, `data-*`, `powerbi-*`, `powerquery-*`

## Trusted sources (in order)

1. Official vendor / GitHub org repos (Microsoft, Anthropic, GitHub, modelcontextprotocol)
2. Official MCP directories
3. Verified community (clear license, recent commits, no install scripts)
4. Everything else → review queue, `trust_level: untrusted`

## Security (every candidate)

- Source URL + license
- Install via npx/uvx/pip only — **no** curl|bash, **no** admin
- Duplicates existing MCP/skill? → merge or reject
- Suspicious scripts? → reject
- Run `python .github/scripts/review_candidate.py` before marking approved

## Web search

- **Max 3** searches per session — only when external facts are required
- Do not search for code already in the repo
- Log queries in `memory/learning-log.md`

## Writing rules

- **New MCPs** → append to `requirements/review-queue.json` with full candidate object
- **cursor/mcp.json** → only for SHIP mission with `status=approved` slug
- **Skills** → update existing before creating; use `agent-playbook.md` not new `agent-*`
- Never commit secrets

## Review candidate schema

```json
{
  "slug": "example-mcp",
  "type": "mcp",
  "name": "Display Name",
  "source_url": "https://github.com/org/repo",
  "trust_level": "official",
  "license": "MIT",
  "security_status": "pending",
  "status": "discovered",
  "description": "...",
  "install_notes": "npx ... user scope",
  "try_asking": ["prompt 1", "prompt 2"],
  "discovered_at": "2026-07-04"
}
```

## End of session checklist

1. Run `python .github/scripts/validate_catalog.py`
2. Run `python .github/scripts/validate_review_queue.py` if queue touched
3. Update `memory/learning-log.md`
4. Open PR with clear summary — what was proposed, security notes, Try asking examples
5. Do **not** merge your own PR if it adds untrusted approved items

## Stop when

- One complete deliverable shipped in PR, OR
- "No ship" logged with reason, OR
- Hit search/candidate limits
