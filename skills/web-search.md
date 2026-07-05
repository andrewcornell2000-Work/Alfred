# Live Web Search

Use when **live or external data** is required — not for code already in the repo or timeless explanations.

## Alfred CLI (Tavily direct API)

Alfred calls Tavily from `backend/main.py` (`_tavily_search()`). Key: `TAVILY_API_KEY` in `.env`.

### When Alfred searches automatically

- Brain category is **`SEARCH`**, or
- Brain sets **`needs_search: true`**, or
- User text matches **explicit recency keywords** (`latest`, `today`, `search for`, `current version`, …)

### When Alfred does NOT search

- Timeless "explain / how does X work" questions (unless brain flags live data)
- Meta commands (`back`, `menu`, `exit`)
- Code, refactor, and file tasks (unless brain explicitly needs external docs)
- Every question ending in `?` — **not** a trigger by itself

Prefer fast chat over search when unsure.

## Cursor agents (MCP)

| Need | Tool | Not |
|------|------|-----|
| Library/SDK API docs | `context7` | Tavily, fetch |
| Live news / versions / prices | `parallel-search` or Alfred Tavily | fetch for search |
| Single known URL | `fetch` once | playwright |
| Deep crawl / JS-heavy site | `firecrawl` (if key set) | repeated fetch loops |

**One web path per question** — see `skills/mcp-routing.md`.

## Learning / discovery sessions

Web search only when researching a **new external tool** to add to the catalog.

- DISCOVER missions: **1–3 targeted queries**, not a daily quota
- IMPROVE existing skills: search only to verify a URL or version
- Normal coding: **no search**

Playbook: `docs/LEARNING-WORKFLOW.md`

## Approach

1. Form a precise query (no filler words)
2. Run one search path; refine once if results are poor
3. Cite source URLs
4. Do not present results as training knowledge

## Safety

- Never commit the Tavily key
- If results conflict, show both sides
- Stop searching once you have enough to write the deliverable
