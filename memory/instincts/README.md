# Alfred Instincts (continuous learning)

An **instinct** is a confidence-scored, reusable lesson — *"when X, do Y"* — that
Alfred learns from real sessions and **surfaces automatically at the start of
future sessions** (via the `SessionStart` hook). It's the upgrade over a static
`brain.md`: lessons gain/lose weight over time and only the confident ones get
injected into context.

Engine: [`scripts/instinct-cli.py`](../../scripts/instinct-cli.py) (stdlib-only,
ported lean from ECC's continuous-learning-v2).

## Files

| File | Tracked? | What |
|------|----------|------|
| `global.json` | ✅ committed | Curated + learned instincts that apply everywhere |
| `projects/<hash>.json` | 🚫 git-ignored | Per-repo instincts (keyed by git-remote/cwd hash) |
| `observations.jsonl` | 🚫 git-ignored | Runtime observation log (opt-in Stop hook) |

Per-project and observation data stay local on purpose — they're machine/repo
specific. Promote anything broadly useful into `global.json`.

## Confidence model

- New instinct starts at **0.30** (`pending`) and rises asymptotically toward
  1.0 with each reinforcement.
- `pending <0.50` → `active 0.50–0.80` → `strong ≥0.80`. Only **active+** surface
  at session start.
- `decay` lowers confidence for instincts untouched ≥14 days; `prune` deletes
  `pending` instincts past a 30-day TTL.

## Commands

```bash
python scripts/instinct-cli.py status                      # view (project + global)
python scripts/instinct-cli.py record --domain D \
    --trigger "when ..." --guidance "do ..."               # add or reinforce
python scripts/instinct-cli.py reinforce <id>              # bump confidence
python scripts/instinct-cli.py decay                       # age out stale ones
python scripts/instinct-cli.py prune                       # drop dead pending ones
```

Slash commands: `/instinct-status` and `/instinct-learn` (see `.claude/commands/`).
