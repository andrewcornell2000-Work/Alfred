# Live Web Search

Use this skill when Alfred needs real-time information: latest versions, current documentation,
recent news, prices, or anything that requires up-to-date data beyond training knowledge.

## Tool: brave-search MCP

The `brave_web_search` tool is available via the `brave-search` MCP server.

```
brave_web_search(query="your search query", count=5)
```

Returns: title, url, description for each result. Follow up with `brave_local_search` for location-based queries.

## When to use

- "What's the latest version of X?"
- "Current docs for [library/API]"
- "Search online for [topic]"
- "Look up [company/price/news]"
- "Find the official docs for [tool]"
- Any question where training data may be stale

## Approach

1. Form a precise, concise search query (avoid filler words)
2. Run `brave_web_search` with `count=5`
3. Return the most relevant result with the source URL
4. If the top results look unreliable, refine the query and search again

## Example queries

```
brave_web_search(query="Python 3.13 release notes", count=3)
brave_web_search(query="FastAPI latest stable version", count=3)
brave_web_search(query="site:docs.anthropic.com Claude API tool use", count=5)
```

## Safety rules

- Always cite the source URL
- Do not present search results as your own knowledge
- If results conflict, show both and let the user decide
