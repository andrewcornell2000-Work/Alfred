# Continuous Learning (Instincts)

**When to use:** any time Alfred solves a non-trivial problem, discovers a
workaround, or hits the same mistake twice. Capture the lesson as an *instinct*
so future sessions start already knowing it.

## What it is

An instinct is a confidence-scored `when X → do Y` rule stored in
`memory/instincts/`. Active/strong instincts are **auto-injected at session
start** by the `SessionStart` hook (`scripts/hooks/session-start-instincts.py`),
so they actually shape behaviour instead of rotting in a doc.

Engine: `scripts/instinct-cli.py` (stdlib Python, no deps). Ported lean from
ECC's continuous-learning-v2 — see `memory/instincts/README.md` for the
confidence model.

## Try asking

- "Alfred, what instincts have you learned?" → runs `/instinct-status`
- "Remember this: when a Vercel build fails on a missing env var, check the
  Vercel project settings before touching code." → records a global instinct
- "We just figured that out — save it as an instinct." → `/instinct-learn`

## How to record a lesson

Reinforce-if-exists, otherwise create:

```bash
python scripts/instinct-cli.py record \
  --domain "vercel" \
  --trigger "build fails with 'Environment Variable not found'" \
  --guidance "It's config, not code — add the var in Vercel project settings, redeploy." \
  --scope project        # or: global (applies everywhere)
```

- Use **project** scope for repo-specific conventions (Boostly, finance pack).
- Use **global** scope for lessons that transfer across all work.
- Re-recording the same `domain`+`trigger` reinforces it (confidence ↑) instead
  of duplicating.

## Maintenance (run from the autonomous loop)

```bash
python scripts/instinct-cli.py decay   # age out instincts untouched >14 days
python scripts/instinct-cli.py prune   # delete dead 'pending' instincts (30-day TTL)
```

## Guardrail hooks shipped alongside

Wired in `.claude/settings.json`:

- **config-protection** (`Edit|Write|MultiEdit`) — blocks edits that weaken
  linter/formatter configs (eslint/prettier/biome/ruff/stylelint/markdownlint).
  Steers Alfred to fix the code, not the config.
- **pre-commit-quality** (`Bash`) — scans staged files before `git commit`;
  blocks on secrets/debugger, warns on `console.log`.
- **observe-session** (`Stop`, opt-in `ALFRED_INSTINCT_OBSERVE=1`) — logs cheap
  observation markers for later mining.
