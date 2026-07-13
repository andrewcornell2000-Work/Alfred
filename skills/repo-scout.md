# Repo Scout — GitHub A-Team (Mr Smith canonical prompt)

Evaluate a GitHub repo for Andrew's three goals: **web apps**, **mobile games**, **logistics/warehouse analyst** work.

## Auto-route (default — no special words needed)

If Andrew pastes a **GitHub repo URL** and wants it looked at, agents **must** run Repo Scout + A-Team (see `cursor/rules/repo-scout-routing.mdc`). Examples that auto-trigger:

```text
https://github.com/owner/repo
look at this https://github.com/owner/repo
is this worth adding?
check this repo for overlap with Alfred
```

Return the 8-section Verdict Card. Do not install during triage.

## Explicit prompt (optional — same workflow)

```text
Repo Scout — evaluate this repo for Andrew.

URL: https://github.com/OWNER/REPO
Focus: all

Return the 8-section Verdict Card. Run A-Team in parallel. Do not install anything.
```

**Focus options:** `all` | `web` | `games` | `logistics`

## A-Team roster

| Agent | Role |
|-------|------|
| **repo-scout** | Lead — you invoke this one |
| **repo-safety-guard** | Install / MCP safety |
| **repo-stack-overlap** | Duplicate vs Alfred stack |
| **repo-eval-logistics** | Analyst / warehouse fit |
| **repo-eval-web** | Web app shipping fit |
| **repo-eval-games** | Mobile / game fit |
| **research-analyst** | Ambiguous / mixed repos |

Evaluators triage; **builders** (`nextjs-developer`, `game-developer`) run only after ADOPT.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| **ADOPT** | Safe, new/useful, maintained — integrate or daily use |
| **TRIAL** | 15–30 min PoC first |
| **SKIP** | Unsafe, duplicate, stale, or wrong domain |

## Acceptance test (Mr Smith)

A good run includes:

1. All **8 Verdict Card sections** populated
2. **Safety BLOCK** → never ADOPT
3. **Overlap class** stated (DUPLICATE/PARTIAL/COMPLEMENT/NEW)
4. Three **0–5 lens scores** with one-line whys
5. At least one **"Try asking"** if any score ≥3
6. **No install** during triage

## After ADOPT / TRIAL

Owner approves explicitly, then:

1. `cursor/mcp.json` + `requirements/mcp-tools.md` (MCP)
2. `alfred-tools.json` (CLI)
3. `skills/` + `skills/_buckets.json`
4. `requirements/safety-gates.md` if destructive
5. `memory/discovered-tools.md` + `memory/learning-log.md`
6. `Provision-Cursor.ps1 -SkipCloseAgentApps` to sync

## Shorthand

```text
Repo Scout — evaluate https://github.com/owner/repo
```
