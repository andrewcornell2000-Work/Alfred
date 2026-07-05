# AGENTS.md — Project Context Files for Cursor, Claude Code & Codex

Use this skill when you want any AI agent (Cursor, Claude Code, Codex CLI) to automatically
know your project's build commands, coding conventions, forbidden zones, and architectural
constraints — **without repeating them every session**.

*Companion skills: `agent-context-engineering.md` (window management), `agent-reasoning.md`
(decompose tasks), `lean-ctx.md` (context budget). This skill covers the **project-persistent**
layer: what goes in the repo, not the conversation.*

---

## What is AGENTS.md?

`AGENTS.md` is a plain Markdown file placed at the **root of a repository**. When Cursor,
Claude Code (v1.7+), or Codex CLI starts a session, they automatically read it and inject its
contents into their system prompt. You write it once; every agent session in that project gets
it without any extra prompting.

**Key insight:** It covers what agents *cannot infer from the codebase alone* — exact build flags,
test procedures, which folders to never touch, and team conventions that live nowhere in the code.

### How each tool reads it

| Tool | How it loads AGENTS.md |
|------|------------------------|
| **Claude Code** | Auto-loaded at session start (v1.7+); also loads `CLAUDE.md` if present |
| **Cursor** | Loaded as a Cursor Rule when named `AGENTS.md` in repo root (same as `.cursorrules`) |
| **Codex CLI** | Auto-loaded by default on `codex` invocation if present in repo root |
| **GitHub Copilot Workspace** | Reads `AGENTS.md` as project context (2026) |

---

## The three-tier boundary system

The most important thing in any `AGENTS.md` is a **clear three-tier boundary declaration**:

```markdown
## Boundaries

### ALWAYS do
- Run `npm test` before committing
- Follow TypeScript strict mode — no `any`
- Keep PR descriptions under 200 words

### NEVER do
- Touch /legacy — frozen production code
- Modify .env files or commit secrets
- Rename exported function signatures without updating all callers

### ASK before doing
- Deleting or moving files
- Changing database schema
- Refactoring shared utilities used in more than 2 modules
```

Agents parse imperative verbs. **NEVER** and **do not** are the strongest signals.
**ASK before** is the second tier — triggers a confirmation step rather than silent action.

---

## Recommended sections (in order)

### 1. Build commands
Exact commands with all flags. Agents guess wrong when flags matter.

```markdown
## Build & Run

```bash
# Install
npm install

# Dev server (hot reload)
npm run dev -- --port 3001

# Production build
npm run build -- --mode production

# Lint (must pass before PR)
npm run lint -- --max-warnings 0
```
```

### 2. Test commands
Include how to run a single test (agents use this constantly):

```markdown
## Tests

```bash
# Full suite
npm test

# Single file
npm test -- --testPathPattern="src/utils/format.test.ts"

# Watch mode
npm test -- --watch
```

Tests must pass before committing. If a test is failing and you did not write it, stop and ask.
```

### 3. Project structure (brief)
Only what's non-obvious:

```markdown
## Project Structure

- `/src/features/` — one folder per domain (auth, billing, reports). Add new features here.
- `/src/shared/` — utilities used by 2+ features. Do NOT add feature-specific code here.
- `/legacy/` — DO NOT TOUCH. Frozen 2023 code kept for reference only.
- `/scripts/` — one-off data migration scripts. Never imported by app code.
```

### 4. Code style — deviations from defaults only
Don't repeat what ESLint/Prettier already enforces. Write only team-specific conventions:

```markdown
## Code Style

- Use named exports only — no default exports (Cursor auto-imports break with defaults)
- Date formatting: always use `formatDate(d, 'DD MMM YYYY')` from `src/shared/dates.ts` — never raw `toLocaleDateString()`
- Error messages: sentence case, no trailing period, include the offending value
- DAX measures: prefix with `_` if they're intermediate (not surfaced in reports)
```

### 5. PR / commit conventions

```markdown
## Commits & PRs

- Commit format: `type(scope): short description` — types: feat | fix | refactor | docs | chore
- PR title must match commit format
- Always add a reviewer — never self-merge
- Link Jira ticket in PR description if one exists: `Resolves PROJ-1234`
```

### 6. Environment & credentials

```markdown
## Environment

- Copy `.env.example` to `.env.local` for dev — never commit `.env.local`
- Required env vars are documented in `.env.example` with comments
- Production secrets live in Azure Key Vault — ask the team for access
```

---

## What NOT to put in AGENTS.md

Every line costs context tokens on every session. These inflate cost without adding value:

| ❌ Don't include | ✅ Why not |
|------------------|-----------|
| General coding advice ("write clean code") | Already in the model's training |
| Things enforced by linter/formatter | Redundant — the tool catches it anyway |
| Full architectural diagrams | Use a separate `ARCHITECTURE.md` and reference it |
| Secrets or credentials | Never in any tracked file |
| Long explanations of *why* conventions exist | Keep it imperative; docs go elsewhere |

**Target length:** under 150 lines. Above that, important rules get buried.

---

## AGENTS.md vs CLAUDE.md vs .cursorrules

| File | Scope | Best for |
|------|-------|----------|
| `AGENTS.md` | All agents (Cursor, Claude Code, Codex, Copilot) | Cross-tool teams, new standard |
| `CLAUDE.md` | Claude Code only | Claude-specific workflows, memory imports |
| `.cursorrules` | Cursor only | Editor-specific completions, Cursor autopilot rules |
| `.cursor/rules/*.md` | Cursor only (per-rule) | Fine-grained rule files with activation patterns |

**Recommended approach for Andrew's stack:** maintain `AGENTS.md` for shared conventions, and a
small `CLAUDE.md` for Claude-specific memory imports and project onboarding instructions.
They coexist cleanly — Claude Code reads both.

---

## Sub-directory AGENTS.md files

You can place `AGENTS.md` inside subdirectories. Agents merge parent + child:

```
/AGENTS.md            ← global conventions
/backend/AGENTS.md    ← Python/FastAPI specifics, test DB path, alembic commands
/frontend/AGENTS.md   ← React/Vite specifics, component patterns, Storybook commands
```

This is useful when different parts of the repo have different languages or build systems.

---

## Alfred Pack projects — starter template

For any repo Andrew works in, here's a minimal `AGENTS.md` to drop in:

```markdown
# AGENTS.md — [Project Name]

## Build & Run

```bash
# Install
[install command]

# Dev
[dev command]

# Test (full suite)
[test command]

# Test (single file)
[test command with filter flag]
```

## Boundaries

### NEVER do
- Modify files in `/[frozen-folder]/`
- Commit `.env` files or API keys
- Rename public function signatures without updating all callers

### ASK before doing
- Deleting or moving files
- Changing any shared schema or data model

## Project Layout
- `/[main source]/` — [description]
- `/[shared utils]/` — [description]; used by 2+ modules
- `/[legacy or frozen]/` — DO NOT TOUCH

## Code Conventions
- [Language + version]
- [Key formatter/linter: e.g. "Prettier 3, 2-space indent, single quotes"]
- [One team-specific rule that isn't in the linter]

## Tests
Tests must pass before committing. If a test you didn't write is failing, stop and ask.

## Commit Format
`type(scope): short description` — types: feat | fix | refactor | docs | chore
```

---

## AgentLint — lint your AGENTS.md automatically

**AgentLint** (`npx agentlint-ai`) is a free CLI that audits your `AGENTS.md`, `CLAUDE.md`,
`.cursor/rules`, and CI workflows against 33 evidence-backed checks. Useful for catching:

- Rules that are too vague for agents to act on
- Missing test commands
- Credentials accidentally included
- Conflicts between `AGENTS.md` and `.cursorrules`

```bash
npx agentlint-ai
```

---

## Practical workflow

### Starting a new project
1. Copy the starter template above into repo root as `AGENTS.md`
2. Fill in build/test commands with exact flags (test them first)
3. Run `npx agentlint-ai` to check for common mistakes
4. Commit — all agents now pick it up automatically

### Maintaining an existing AGENTS.md
- When a convention changes, update `AGENTS.md` in the same PR
- Quarterly: prune rules that are now enforced by linter (they're redundant)
- If you add a new frozen/legacy folder, add it to the NEVER list immediately

### Debugging "agent ignored my convention"
1. Check if the rule is in `AGENTS.md` (not just your memory)
2. Check if the rule is imperative ("do X") vs vague ("prefer X")
3. If using Cursor, verify `AGENTS.md` appears in the Rules panel (Settings → Rules)
4. Run `npx agentlint-ai` — it often spots the issue

---

## Try asking

```
Drop a starter AGENTS.md in this repo root — include the build command, test command,
and set /legacy as a NEVER-touch zone
```

```
Read our AGENTS.md and summarise what conventions an agent needs to follow before
making any changes to this codebase
```

```
Audit our AGENTS.md against the three-tier boundary checklist — are all destructive
operations covered with NEVER or ASK before doing?
```

```
We just added a new /archive folder that should never be touched — update AGENTS.md
to add it to the NEVER list
```

```
Create a /backend/AGENTS.md for the Python FastAPI layer — include the alembic
migration command, pytest run command, and the rule about never importing from /frontend
```
