# Vercel

Use the Vercel MCP + official Vercel plugin for deployments, Next.js, and AI SDK work.

## Setup (Alfred provision)

1. Re-run provision (MCP + plugin install):

   ```powershell
   powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
   ```

2. Vercel plugin (installed automatically, or run manually):

   ```powershell
   npx plugins add vercel/vercel-plugin
   ```

   Docs: https://vercel.com/docs/agent-resources/vercel-plugin

## MCP (Cursor)

- Server: `vercel` — remote MCP at `https://mcp.vercel.com`
- OAuth in Cursor on first use
- Deployments, build/runtime logs, project status, docs search

## Plugin slash commands

```text
/vercel-plugin:nextjs
/vercel-plugin:ai-sdk
/vercel-plugin:deploy prod
/vercel-plugin:env
/vercel-plugin:status
/vercel-plugin:bootstrap
/vercel-plugin:marketplace
```

## When to use what

| Need | Use |
|------|-----|
| Deploy, logs, project status | Vercel MCP or `/vercel-plugin:deploy` |
| Next.js / AI SDK patterns | Plugin skills (`/vercel-plugin:nextjs`, `/vercel-plugin:ai-sdk`) |
| Env vars | `/vercel-plugin:env` or MCP |

Session context from the plugin activates automatically in empty dirs and detected Vercel/Next.js projects.
