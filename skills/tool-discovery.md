# Tool Discovery (Cursor learning)

Use when a **Cursor session** in the Alfred repo is tasked with finding new tools for the pack.
Playbook: **`docs/LEARNING-WORKFLOW.md`**

## Search angles (pick one per session)

- `MCP server` + finance / Excel / Power BI / SharePoint / PDF / scheduling
- `modelcontextprotocol` office productivity (npx / uvx install)
- CLI tools for CSV / parquet / markdown / calendar without admin install
- Agent skill patterns — update `skills/agent-playbook.md` instead of new `agent-*` files

## Evaluation checklist (must pass 3+)

1. **Installable** without admin on Windows (npx, uvx, pip, winget user)
2. **Distinct** — not in `cursor/mcp.json` or `discovered-tools.md`
3. **Actionable** — concrete "Try asking:" prompt
4. **Trust** — official or well-maintained; note if destructive
5. **No secret** in committed files — document keys in `.env.template` only

## What to ship

| Outcome | Action |
|---------|--------|
| Installable MCP | `cursor/mcp.json` + `mcp-tools.md` + skill |
| CLI only | manifest + `alfred-tools.json` + skill |
| Not ready | `discovered-tools.md` as `candidate` |
| Always | `memory/learning-log.md` entry |

**Update existing skills before creating new ones.** Check `requirements/catalog-index.json`.

## Web search discipline

- **1–3 searches** per DISCOVER session — enough to verify install path and docs
- No automatic daily search loop
- Log queries in `learning-log.md`

## Domains Andrew cares about

Power BI · Excel · labour planning · DLP · OneDrive/SharePoint · Azure dataflows ·
reports (Word/PDF/PPT) · git/PR workflows · token-efficient repo reading
