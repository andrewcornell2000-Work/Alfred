# Alfred Secure Cloud Learning Loop

Automated cloud agent that researches trusted sources and **proposes** capability updates through the review pipeline — never blind installs.

## Schedule

GitHub Actions: **Monday and Thursday 02:00 UTC** (~noon AEST)  
Manual: Actions → "Alfred Secure Learning Loop" → Run workflow

## Pipeline (enforced)

```
Research (max 3 web searches)
  → add_review_candidate OR improve existing skill
  → review_candidate.py validation
  → memory/learning-log.md
  → commit (review queue + docs only for new MCPs)
  → user approves on machine → Alfred-Update.ps1 → Provision-Cursor.ps1
```

## What the cloud agent may write

| Allowed | Blocked |
|---------|---------|
| `requirements/review-queue.json` (candidates) | Direct new MCP keys without approved queue entry |
| `requirements/discovered-tools.md` (candidates) | `skills/taste-*`, finance domain skills |
| Improve existing `skills/*.md` | Duplicate agent-* skills |
| `memory/learning-log.md` | API keys, credentials |

## Cursor Cloud Agent

For Cursor background agents, use prompt: **`.github/prompts/cloud-learning.md`**

Same rules as GitHub Actions loop.

## Stop conditions

- Max **3** web searches per run
- Max **8** agent iterations
- Max **2** new review candidates per run
- Stop if no approved work remains

## Local install after cloud learning

When the loop commits to `main`:

1. Notification appears (if Alfred UI / scheduled task registered)
2. Click **Install Update** → `scripts/Alfred-Update.ps1 -Force`
3. Or run `ui/Alfred-App.ps1` → **Install Update**

See `docs/INSTALL.md` for rollback.
