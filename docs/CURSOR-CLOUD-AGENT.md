# Alfred Learning — Cursor Cloud Agent

Alfred learns new AI capabilities through **Cursor Cloud Agents** — not GitHub Actions.

Security first: agents **propose** updates via the review pipeline. Users **install** via `Alfred.exe` or the update notification.

---

## Quick start

1. Open the **Alfred** repo in Cursor
2. Start a **Cloud Agent** (Background Agent) with this prompt:

```text
Run Alfred secure learning session. Read .cursor/cloud-learning.md fully and follow it exactly.
One mission only. Max 3 web searches. Open a PR when done — do not push to main directly.
```

3. Review the PR → merge to `main`
4. On your PC: toast notification or **Alfred.exe → Install update**

---

## Setting up a recurring Cloud Agent

In Cursor, use **Automations** or scheduled Cloud Agents (when available):

| Setting | Value |
|---------|-------|
| **Repository** | `andrewcornell2000-Work/Alfred` |
| **Branch** | Create PR against `main` |
| **Schedule** | Twice weekly (e.g. Mon + Thu) — or run manually |
| **Prompt** | See `.cursor/cloud-learning.md` or paste the quick start above |

If scheduling is not available, run manually twice weekly or after major AI vendor announcements.

---

## Secure pipeline (enforced)

```
Read .cursor/cloud-learning.md + review-queue.json + catalog-index.json
  → 1 mission (DISCOVER / IMPROVE / SHIP approved / CATALOG refresh)
  → max 3 web searches (trusted sources only)
  → update review-queue.json OR improve existing skill
  → python .github/scripts/validate_catalog.py
  → python .github/scripts/validate_review_queue.py (if queue changed)
  → python .github/scripts/review_candidate.py (for new candidates)
  → memory/learning-log.md
  → PR (never direct push to main)
```

User machine after merge:

```
Check-AlfredUpdates.ps1 → toast → Alfred-Update.ps1 -Force → Provision-Cursor.ps1
```

---

## What the Cloud Agent may change

| Allowed | Blocked |
|---------|---------|
| `requirements/review-queue.json` (candidates) | New MCP in `cursor/mcp.json` without `approved` queue entry |
| Improve existing `skills/*.md` | `skills/taste-*`, finance domain skills |
| `requirements/discovered-tools.md` (candidates) | Duplicate `agent-*` skills |
| `memory/learning-log.md` | API keys, credentials |
| SHIP: `cursor/mcp.json` only for **approved** slugs | Blind package install |

---

## Stop conditions

- Max **3** web searches per session
- Max **2** new review candidates per session
- One deliverable per session
- Stop if duplicate, rejected, or nothing worth shipping (log in `learning-log.md`)

---

## Validation before PR

```bash
python .github/scripts/validate_catalog.py
python .github/scripts/validate_review_queue.py
python .github/scripts/review_candidate.py path/to/candidate.json  # if adding candidate
```

---

## Deprecated: GitHub Actions loop

The GitHub Actions learning workflows (`alfred-secure-learning.yml`, `alfred-growth-loop.yml`) and `alfred_loop.py` are **removed**.

Archived script: `.github/archive/alfred_loop.py` (reference only).

---

## Related docs

- Agent rules: `.cursor/cloud-learning.md`
- Review queue: `requirements/review-queue.json`
- Install updates: `docs/INSTALL.md`
- Structure: `docs/ALFRED-STRUCTURE.md`
