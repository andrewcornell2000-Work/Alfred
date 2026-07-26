# Agent Handoff — Passing Work Between Sessions and Tools

Use this skill when you are switching AI tools mid-task, ending a session and resuming it
tomorrow, or handing a partially-complete task to Codex (cloud) or Claude Code (terminal)
after starting in Cursor (IDE).

Use `prompt-handoff.md` instead when the deliverable is a copy-paste executor prompt rather
than a record of current repository state. Use `agent-planning.md` to design work that will
continue in the current session.

Do not create a handoff file automatically. If the user asks for a portable file, write it to
the requested path (default `HANDOFF.md` at the repo root). If they only ask for handoff text,
return the block in chat and do not add repository clutter.

---

## The core problem

Every AI session starts blank. When you stop work in Cursor at 5 pm and open Claude Code
tomorrow, it knows nothing about what you decided, what files you touched, or what you
deliberately left unfinished. You either:

- Re-explain everything from scratch (slow, lossy), or
- Paste a **HANDOFF.md** that the new session reads in 10 seconds.

The HANDOFF.md is not a project README (too broad) or a transcript (too noisy). It is a
**living session-end document** — rewritten when requested, always reflecting *right now*,
never accumulating stale history.

---

## The Three Handoff Types

### Type 1: Same-tool, next-day resume
You stop a Cursor session at the end of the day. Tomorrow you open a new Cursor session
on the same task.

**When to use:** Any session you plan to continue. Takes 30 seconds to generate.

### Type 2: Same-task, different tool
You've been designing/planning in Cursor (interactive, exploratory) and now want to hand
execution to Codex CLI or Claude Code (which run autonomously, take larger context windows,
and are better for long execution chains).

**When to use:** You've confirmed the design in Cursor and now want Codex to actually build it.
Or you've hit Cursor's context limit and want to continue in Claude Code.

### Type 3: Parallel worker dispatch
You (or an orchestrator session) are splitting a task and dispatching to N worker sessions
or worktrees. Each worker needs its own scoped handoff.

**When to use:** See `agent-parallel-worktrees.md` and `agent-workflow-orchestration.md`
Pattern B. Each worker gets a slimmed handoff covering only its own slice.

---

## The HANDOFF.md Template

When the user requests a file, place `HANDOFF.md` at the **repo root** (or their requested
task path). Never append — always overwrite after confirming that replacing an existing
handoff is intended.

```markdown
# HANDOFF — [Task Name]
_Session ended: [date + time]_
_Last worked in: [Cursor | Claude Code | Codex]_
_Status: IN PROGRESS | BLOCKED | READY FOR NEXT PHASE_

## What we're building
[One sentence. The goal. Not the approach — the goal.]

## Repository state
- Repo / branch: [owner/repo] / [branch]
- Base commit: [short SHA]
- Working tree: [clean | modified files listed]
- Remote state: [unpushed commits, open PR, or none]

## What's done ✓
- [Concrete thing completed] — files affected: [list]
- [Another concrete thing]
(Only things that are CONFIRMED done — tested, checked, saved.)

## Decisions locked 🔒
- [Decision]: [Why] — do not revisit unless explicitly asked
- [Decision]: [Why]
(These are confirmed. A new session should not reopen them.)

## What to do next (ordered)
1. [First thing to do] — expected outcome: [what done looks like]
2. [Second thing] — depends on: [any dependency]
3. [Third thing] — only if step 2 succeeds

## Do NOT do
- [Specific thing the new session might try that would break something]
- [File or folder to stay away from this session]

## Key files (touch these, not others)
- `[path]` — [what it is and why it's relevant]
- `[path]` — [same]

## Open questions (needs human input before proceeding)
- [Question]: [context for why it's blocked]

## Verification and environment
- Commands run: [command → result]
- Next verification command: [exact command]
- Required environment variable names: [names only — never values]
- Machine assumptions: [OS, local services, authenticated CLIs]

## Starting prompt for next session
> [Paste-ready. What you'll type in the new session's first message to orient the agent immediately.]
```

---

## Prompts to generate a HANDOFF.md

Paste these **at the end of your session** before closing the tool.

### Quick handoff (< 2 min)

```
We're done for today. Before I close this session, write a HANDOFF.md at the repo root.
Use this structure:
- What we're building (one sentence)
- What's done (confirmed, tested things only — with file names)
- Decisions locked (things we explicitly confirmed — do not reopen these)
- What to do next (ordered numbered list)
- Do NOT do (specific pitfalls for the next session)
- Key files (only what the next session needs to touch)
- Open questions (anything blocked on my input)
- Starting prompt (what I should paste first in the next session)

Overwrite any existing HANDOFF.md. Be concise. No history — only present state.
```

### Full handoff (cross-tool, before handing to Codex)

```
I'm handing this task to Codex to run autonomously. Write HANDOFF.md at the repo root.
It must be self-contained — Codex will start with ONLY this file and no other context.
Include:
1. Exact goal (one sentence, measurable)
2. Repository state (repo, branch, base commit, dirty files, unpushed commits or PR)
3. Everything confirmed done (file names + what changed)
4. Every decision made and WHY (Codex must not guess rationale)
5. Ordered steps with expected outputs for each
6. Hard constraints (files not to touch, patterns not to use, things that will break prod)
7. Exact verification commands and their latest results
8. Environment variable NAMES only, authentication prerequisites, and machine assumptions
9. A paste-ready starting prompt for Codex

Be specific. Codex has no memory of our conversation.
Never include tokens, passwords, connection strings, private data, or environment values.
```

### Parallel worker handoff (one per worker)

```
I'm splitting this task across two parallel agents. Write a scoped HANDOFF for Worker A only.
Worker A's scope: [describe scope].
Worker B will handle: [describe B's scope — context so A doesn't duplicate it].
Include: goal, done, decisions, next steps, constraints, test command, starting prompt.
Do NOT include anything outside Worker A's scope.
Save as tasks/handoff-worker-a.md.
```

---

## Prompts to CONSUME a HANDOFF.md (starting a new session)

### Standard resume

```
Read HANDOFF.md at the repo root. Do not start work yet.
Summarise in 3 bullets: what's done, what you'll do first, and any blocker you spotted.
Then ask if you should proceed.
```

### Codex autonomous start

```
Read HANDOFF.md at the repo root. This is your complete context.
Execute the "What to do next" steps in order.
After each step: confirm what you did and the test/verify result before moving to the next.
If you hit an open question, stop and report — do not guess.
```

### Conflict check (after coming back to a repo that may have changed)

```
Read HANDOFF.md. Then check: have any of the "Key files" been modified since the HANDOFF
was written (use git log --since="[date]")? If yes, list what changed and whether it
affects the "What to do next" steps before we proceed.
```

---

## Cursor → Claude Code → Codex: which tool for which phase

Choose the next tool based on the task, not a fixed hierarchy. The handoff must remain
tool-neutral except for explicit prerequisites. Cursor, Claude Code, and Codex should all be
able to recover repository state, constraints, and the next verified step from the same file.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Writing a HANDOFF that includes conversation history | Only include current state — no "first we tried X, then we realised Y" |
| Forgetting to rewrite HANDOFF before switching tools | Make "generate HANDOFF.md" the last prompt of every session |
| Open questions in HANDOFF that block the whole next session | Resolve them yourself before handing off, or break the task into a step the agent CAN do first |
| "Key files" list too broad ("all of src/") | Name specific files; too-broad scope causes agents to re-read everything |
| Handoff for Codex includes Cursor-specific notes | Codex is headless — no IDE context, no open tabs. Strip IDE-specific notes |
| Appending to an existing HANDOFF | Always overwrite. Stale entries cause confusion. The file = present state only |

---

## Try asking

```
We're done for today. Write HANDOFF.md so I can resume this tomorrow in a fresh session.
Make it self-contained — assume no memory of today's conversation.
```

```
Read HANDOFF.md. Summarise what's done, what's next, and any blocker before you start.
```

```
I'm handing this task to Codex to run without me watching. Write a HANDOFF.md Codex can
follow autonomously — include the test command it should run after each step.
```

```
I'm splitting this into two parallel worktrees. Write two separate handoffs:
one for the data-pipeline work and one for the report-formatting work.
Each worker should be completely independent — no shared files.
```

```
Check HANDOFF.md — have any of the key files changed since yesterday's session? If so,
what do I need to update in the handoff before we continue?
```

---

## Quick reference

```
End of session  →  "Write HANDOFF.md — overwrite, present state only"
Start of session →  "Read HANDOFF.md, summarise, ask before starting"
Cross-tool       →  "Write self-contained HANDOFF for Codex — it has no context"
Parallel agents  →  One scoped handoff per worker, no overlap
Conflict check   →  "Has HANDOFF.md key files changed since [date]?"
```
