# Agent rules (shared)

Seeded by Alfred. Read by both Cursor and Claude Code. Project-specific instructions below this line take precedence.

- Inspect existing patterns before writing new code; reuse before abstracting.
- Make the smallest change that fully solves the task. No speculative scope.
- After changes: typecheck, run relevant tests, lint if present, then summarize changed files and risks.
- Fix root causes, not symptoms. Add a regression test when fixing a bug.
- Surface assumptions and tradeoffs instead of guessing silently.
- Don't claim something works until it has been run and verified.

<!-- Project-specific rules go below. -->
