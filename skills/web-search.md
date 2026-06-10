# Live Web Search

Use this skill when Alfred needs real-time information: latest versions, current documentation,
recent news, prices, or anything that requires up-to-date data beyond training knowledge.

## Tool: Tavily (direct API — not an MCP)

Alfred calls Tavily directly from Python (`backend/main.py`). No MCP server is needed.
The API key lives in Alfred's `.env` as `TAVILY_API_KEY`.

Routing: requests with live/current-data keywords (latest, news, price, today, current version)
are classified as **SEARCH** and run through Tavily before Claude synthesises the answer.

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
3. Verify in Alfred Control Tower — Tavily should show **ready**

## Safety rules

- Always cite the source URL
- Do not present search results as your own knowledge
- If results conflict, show both and let the user decide
- Never commit the Tavily key to git
