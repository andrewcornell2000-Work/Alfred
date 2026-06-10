# Tool Discovery (for the growth loop)

When Alfred's cloud loop searches for new tools, prioritize **day-to-day finance & office work**
over generic dev tooling.

## Search angles (rotate)

- `MCP server` + finance / Excel / Power BI / SharePoint / PDF / scheduling
- `modelcontextprotocol` new servers 2026
- `npx mcp` OR `uvx mcp` office productivity
- CLI tools for CSV / parquet / markdown / email / calendar without admin install
- Token-efficient alternatives to browser automation

## Evaluation checklist (must pass 3+)

1. **Installable** without admin on Windows (npx, uvx, pip, winget user, portable zip)
2. **Distinct** — not duplicate of something in `cursor/mcp.json` or `discovered-tools.md`
3. **Actionable** — you can write a concrete "Try asking:" prompt
4. **Trust** — official or well-maintained community; note if destructive
5. **No secret** — or document key source in `_requires` / `.env.template` only

## What to ship each run

- **If installable MCP:** add to `cursor/mcp.json` + `requirements/mcp-tools.md` + skill
- **If CLI only:** add to npm/python requirements + `alfred-tools.json` + skill
- **If not ready:** add to `discovered-tools.md` as `candidate` with why it's promising
- **Always:** append `memory/discoveries.md` and update `memory/learning-log.md`
- **Email Andrew:** include 2–3 "Try asking:" examples in plain English

## Domains Andrew cares about

Power BI · Excel · labour planning · DLP · OneDrive/SharePoint · Azure dataflows ·
reports (Word/PDF/PPT) · git/PR workflows · token-efficient code reading
