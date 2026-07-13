# Alfred subagents

Canonical subagent definitions for Cursor, Claude Code, and Codex.

## Bucket guide

| Bucket | Who it's for |
|--------|----------------|
| **core** | Universal day-to-day — everyone benefits (Mr Smith, Jean Paul, janitor, code review, debugging, TypeScript, tests) |
| **cloud** | Web apps + **game development** + hosted backends (Next.js, React, Supabase/Vercel agents, game-developer) |
| **data** | Commercial / analytical work (SQL, data-analyst, quant, business analyst) |
| **web** | Research (parallel-search companion agents) |
| **office365** | Excel + M365 (if enabled) |
| **powerbi** | Power BI + DLP Doctor |

`core` is always installed. Other buckets follow `ALFRED_BUCKETS` in `.env`.

## Alfred-native (custom)

| Agent | Bucket | Role |
|-------|--------|------|
| mr-smith | core | Prompt architect / handoffs |
| design-agent | core | Jean Paul — UI design |
| janitor | core | Folder clutter cleanup |
| dlp-doctor | powerbi | DLP / Labour Planning Power BI diagnostics |

## VoltAgent imports

Sourced from [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (MIT). Re-import:

```powershell
.\tools\Import-VoltAgentAgents.ps1 -Force
.\Provision-Cursor.ps1 -SyncOnly -Buckets all
```

| Agent | Bucket | Use |
|-------|--------|-----|
| game-developer | cloud | Game dev (engines, gameplay, performance) |
| nextjs-developer | cloud | Next.js App Router / full-stack |
| typescript-pro | core | TypeScript strict patterns |
| react-specialist | cloud | React 18+ UI |
| postgres-pro | cloud | Supabase / Postgres |
| api-designer | cloud | REST/GraphQL API design |
| payment-integration | cloud | Stripe / payments |
| fintech-engineer | cloud | Billing, fees, money logic |
| devops-engineer | cloud | CI/CD, Vercel deploys |
| seo-specialist | cloud | Landing / marketing SEO |
| test-automator | core | Playwright / test automation |
| performance-engineer | cloud | Core Web Vitals, perf |
| code-reviewer | core | PR / quality review |
| security-auditor | core | OAuth, secrets, prod security |
| error-detective | core | Prod error traces |
| debugger | core | Deep debugging |
| powershell-7-expert | core | Windows / Alfred scripts |
| data-analyst | data | Insights, dashboards |
| sql-pro | data | SQL across DuckDB/Postgres |
| business-analyst | data | Requirements, specs |
| quant-analyst | data | Quant / modelling |
| research-analyst | web | Broad research |
| ab-test-analysis | data | Experiment analysis |

## Install paths (after provision)

- `~/.cursor/agents/*.md` — Cursor
- `~/.claude/agents/*.md` — Claude Code
- `~/.codex/agents/*.toml` — Codex CLI

Project-only agents (e.g. Boostl `competitive-analyst`, `session-hub`) live in each repo's `.cursor/agents/`.
