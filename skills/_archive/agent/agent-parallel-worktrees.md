# Parallel Agents with Git Worktrees

Use this skill when you have **multiple independent tasks** that could run at the same time but
currently run one after the other. Git worktrees let you check out several branches of the same
repo into separate directories simultaneously, so Cursor's background agents (or Claude Code
sessions) can each own their own branch without ever touching each other's files.

*Companion skills: `agent-reasoning.md` (plan before you split), `agent-context-engineering.md`
(handoff summaries). This skill covers the mechanics of parallelism.*

---

## Why this matters

By default, every agent shares the same working directory. If you ask two Cursor agents to edit
different files, they race on the same checkout — one can undo what the other just wrote, and
merges become a mess. Worktrees fix this by giving **each agent its own on-disk copy of the repo,
on its own branch, from the same underlying `.git`** — like separate desk drawers that share the
same filing cabinet.

Cursor's parallel-agent feature already does this for you automatically when you enable it. But
knowing the mechanism lets you:
- Set it up manually when running Claude Code or Codex in separate terminal tabs
- Understand why an agent "can't see" a file another agent just wrote
- Clean up stale worktrees after the run

---

## 1. Quick decision: should I run tasks in parallel?

Run in parallel when ALL of these are true:

| Check | Test |
|-------|------|
| **Independent** | Task A's output is not an input to Task B |
| **Different files** | The tasks don't write to the same file |
| **Bounded** | Each task has a clear finish condition (not open-ended exploration) |
| **Reviewable** | You have time to review N diffs, not just one |

**Don't** parallelise root-cause debugging, schema migrations (order matters), or anything where
one task must check the result of the other before proceeding.

Good candidates:

- Write unit tests for Module A while refactoring Module B
- Draft the README while another agent fixes linting errors
- Generate a migration script while another agent updates the API types
- Run two different "try this approach" spikes and pick the better diff

---

## 2. Git worktree basics (3 commands)

```bash
# 1. Create a worktree — new branch, new directory alongside your repo
git worktree add ../myrepo-feat-login feat/login

# 2. List all active worktrees
git worktree list

# 3. Remove a worktree when done (prune cleans orphaned metadata)
git worktree remove ../myrepo-feat-login
git worktree prune
```

Key facts:
- All worktrees share the same `.git` folder — commits in one are immediately visible to `git log`
  in all others
- A branch can only be checked out in **one** worktree at a time (prevents data races at the git
  level)
- Files on disk are completely separate — no accidental overwrites across tasks

---

## 3. Manual parallel-agent workflow (Claude Code / Codex)

Use this when running agents in separate terminal tabs, not inside Cursor's UI.

### Step 1 — Plan the split (do this in chat first)

Before creating worktrees, have the agent write a split plan:

> "I have [task description]. Identify the independent sub-tasks that could run in parallel.
> List them as: Task A (branch name, files it touches), Task B (branch name, files it touches).
> Flag any shared files."

### Step 2 — Create the worktrees

```bash
# From your main repo directory
git worktree add ../myrepo-task-a feat/task-a
git worktree add ../myrepo-task-b feat/task-b
```

### Step 3 — Launch agents (separate terminals)

Terminal 1:
```bash
cd ../myrepo-task-a
# Open Cursor here, or: claude-code "Your Task A instructions"
```

Terminal 2:
```bash
cd ../myrepo-task-b
# Open Cursor here, or: claude-code "Your Task B instructions"
```

### Step 4 — Review and merge

When both agents finish:
```bash
# Back in main repo
cd myrepo
git diff main..feat/task-a    # review diff A
git diff main..feat/task-b    # review diff B

# Merge in order if needed, or create a combined PR
git merge feat/task-a
git merge feat/task-b

# Clean up
git worktree remove ../myrepo-task-a
git worktree remove ../myrepo-task-b
git branch -d feat/task-a feat/task-b
```

---

## 4. Cursor's built-in parallel agents (UI workflow)

Cursor handles worktrees automatically when you use **Background Agents**:

1. Open Cursor with your repo loaded
2. Start a new background agent with `Ctrl+Shift+E` (or via the agent panel)
3. Each background agent gets its own isolated branch and worktree automatically
4. You can chat with each agent independently — they don't share context windows
5. Review the diff from each agent in the PR-style review panel before accepting

**Key behaviour:** Cursor agents communicate through files (not shared memory). If Agent A
produces a file that Agent B needs, you must merge A first, then create Agent B's task.

---

## 5. Handoff files — how agents share information without a shared context

When agents need to pass information, use **files in the repo** as the medium:

```markdown
# agents/task-a-output.md
## What Task A completed
- Refactored auth module (src/auth/*.ts)
- New interface: AuthProvider (see src/auth/types.ts)
- Breaking change: `signIn()` now returns `Promise<AuthResult>` not `boolean`

## What Task B needs to know
- Import AuthProvider from src/auth/types.ts, not auth/index.ts
- The `signIn` return type changed — update any callers in src/api/
```

Instruct each agent at the start of its session to read the handoff file before beginning work.

---

## 6. Port and service isolation (for full-stack work)

If agents need to run a dev server or database, they must use different ports to avoid conflicts:

```bash
# Agent A's dev environment
PORT=3001 npm run dev

# Agent B's dev environment
PORT=3002 npm run dev
```

For databases: use separate test database names, or use Neon/PlanetScale branch-per-worktree if
your stack supports it.

---

## 7. Checklist before you split

- [ ] Written a split plan — task names, branch names, files each task touches
- [ ] Confirmed no shared file writes between tasks
- [ ] Created worktrees before launching any agent
- [ ] Each agent's starting instruction includes the branch name and scope
- [ ] Handoff file written if Task B depends on Task A's output
- [ ] Ports / test DBs isolated if running services
- [ ] Reviewed both diffs before merging (never auto-squash without reading the diff)

---

## 8. Clean-up discipline

Stale worktrees slow down `git status` and can confuse IDE indexing:

```bash
# List all worktrees — anything not "main" that's been merged can go
git worktree list

# Remove by path
git worktree remove /path/to/worktree

# If the directory was deleted manually first:
git worktree prune

# Check for branches that are merged and can be deleted
git branch --merged main
git branch -d feat/task-a feat/task-b
```

Make it a habit: after every parallel session, run `git worktree list` and prune anything merged.

---

## Try asking

In Cursor or Claude Code:

1. **Split a task:** "I need to (A) refactor the auth module and (B) write integration tests for the billing API. These are independent — write me the git worktree setup commands to run these in parallel, then give me the starting instruction for each agent."

2. **Create worktrees from a plan:** "Create two worktrees for this repo — `feat/auth-refactor` and `feat/billing-tests`. Give me the commands and tell me which directory to open Cursor in for each task."

3. **Handoff file:** "Task A just finished. Write a handoff file (`agents/task-a-output.md`) summarising what changed, what the new interfaces are, and what Task B needs to know before it starts."

4. **Review and merge:** "Both agents are done. Show me `git diff main..feat/auth-refactor` and `git diff main..feat/billing-tests`, then tell me the safe merge order given any file overlaps."

5. **Clean up:** "List all worktrees in this repo and give me the commands to remove any that are on branches already merged to main."

6. **Decision check:** "I want to tackle these 3 tasks in parallel: [list]. Tell me which can actually run in parallel (no shared files, no dependency), which must be sequential, and why."

---

## Common mistakes

| Mistake | What goes wrong | Fix |
|---------|----------------|-----|
| Two agents on the same branch | Git prevents checkout; agent errors out | Each task gets its own branch |
| Agents write to the same config file | Last write wins; one agent's work is silently lost | Check the file list in the split plan |
| Merging without reviewing diffs | Agents make different, incompatible assumptions | Always diff before merge |
| Not writing handoff files | Agent B re-derives what Agent A already decided | Write `agents/task-X-output.md` |
| Forgetting to clean up | Dozens of stale worktrees slow the repo | `git worktree prune` after every session |
| Running dev servers on same port | Port conflict; second server fails to start | Explicit `PORT=` env vars per worktree |

---

## Available after next provision

This skill syncs to `~/.cursor/skills`, `~/.claude/skills`, and `~/.codex/skills` when you next
run `Provision-Cursor.ps1`. No new MCPs required — this is pure workflow technique using git
(already installed) and Cursor's built-in background agents.
