# Live Web Search

Use this skill when Alfred needs real-time information: latest versions, current documentation,
recent news, prices, or anything that requires up-to-date data beyond training knowledge.

## Tool: Tavily (optional `.env` key — not an MCP)

Tavily is optional web research. Configure `TAVILY_API_KEY` in Alfred's `.env` if you use live search from skills that reference it.

Use **inside Cursor / Claude Code** — Alfred itself does not run a chat search UI.

## When to use

- "What's the latest version of X?"
- "Current docs for [library/API]"
- "Search online for [topic]"
- "Look up [company/price/news]"
- "Find the official docs for [tool]"
- Any question where training data may be stale

## Approach

1. Form a precise, concise search query (avoid filler words)
2. Alfred runs Tavily with `max_results=5` (or 3 for quick lookups)
3. Return the most relevant result with the source URL
4. If the top results look unreliable, refine the query and search again

## Setup (fresh machine)

1. Get a free key at https://app.tavily.com
2. Add to Alfred `.env`: `TAVILY_API_KEY=tvly-...`
3. Verify: `python -m backend.cli diagnose` — Tavily should show **ready** when configured

## Safety rules

- Always cite the source URL
- Do not present search results as your own knowledge
- If results conflict, show both and let the user decide
- Never commit the Tavily key to git
