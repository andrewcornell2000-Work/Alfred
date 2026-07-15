# Claude Code Subagents & Hooks

Use this skill when you want Claude Code to **delegate work to specialist sub-workers** (subagents)
or **fire deterministic scripts automatically** at key points in its lifecycle (hooks).

*Companion skills: `agent-parallel-worktrees.md`, `agent-workflow-orchestration.md`,
`agents-md-project-context.md`, `agent-handoff.md`.*

---

## The four layers of Claude Code customisation

| Layer | File / location | Loads when | Purpose |
|-------|----------------|-----------|---------|
| **CLAUDE.md / AGENTS.md** | repo root or `~/.claude/CLAUDE.md` | Every session | Project rules, boundaries, build commands |
| **Skills** | `~/.claude/commands/*.md` | On `/skill-name` | Reusable workflows you invoke explicitly |
| **Subagents** | `.claude/agents/*.md` | When Claude delegates | Specialist workers with isolated context windows |
| **Hooks** | `~/.claude/settings.json` `hooks` block | Automatically | Deterministic shell commands at lifecycle events |

---

## Part 1 — Subagents

### What a subagent is

A subagent is a **separate Claude Code instance with its own isolated context window**, spawned by
the orchestrator to do focused work. The orchestrator doesn't bloat its context with exploratory
reads — it delegates to a subagent that handles the search and reports back a clean summary.

### When to use subagent vs. skill

| Use a **skill** when… | Use a **subagent** when… |
|-----------------------|--------------------------|
| You invoke it with `/command` | Claude delegates automatically |
| The task is conversational | The sub-task is self-contained |
| Small, fits in current context | Would balloon context (big scan) |

### Anatomy of a subagent file

```markdown
---
name: code-reviewer
description: Specialist for reviewing changed files. Use when the user asks for a code
  review or when plan mode completes a set of edits.
tools: Read, Grep
---

You are a careful code reviewer. When activated:
1. For each changed file, check for logic errors, hardcoded secrets, missing error handling.
2. Return a markdown table: File | Issue | Severity | Fix.
3. If no issues: "No issues found in [N] files reviewed."
Be terse. The orchestrator relays your output.
```

**Front-matter fields:**

| Field | Required | What it does |
|-------|----------|-------------|
| `name` | Yes | Identifier Claude uses to select this subagent |
| `description` | Yes | Routing hint — write "Use when…" style |
| `tools` | Optional | Claude Code tools: `Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task` (NOT Cursor-style names — silently dropped) |
| `model` | Optional | e.g. `claude-haiku-4-5` for cheap exploratory tasks |

**Write the description like a routing selector:** "Use when the user says 'review my changes'
or when a plan phase ends." Vague descriptions → wrong routing.

### Four subagents to create today

**Repo explorer** — keeps scan cost off the main context:
```markdown
---
name: explore
description: Map relevant files at the start of any task. Returns file tree and entry
  points. Do NOT load full file contents into main context.
tools: Read, Glob, Grep
model: claude-haiku-4-5
---
1. List top-level folders (2 sentences each).
2. Find 3-5 files most relevant to the task.
3. Return: name, one-line purpose, approx line count.
```

**Test writer** — isolated context for test generation:
```markdown
---
name: test-writer
description: Write pytest/Jest tests for a function or module when asked. Returns
  a complete test file as a code block.
tools: Read
---
For each public function: write 3 test cases (happy path, edge case, error).
Flag any function that's hard to test and suggest why.
```

**Document summariser** — compress large files:
```markdown
---
name: summarise
description: Summarise a large file or document without loading full content into
  main context.
tools: Read
model: claude-haiku-4-5
---
Return: Purpose (1 sentence), Key sections (bullets), Important constants,
Dependencies, Red flags (TODO/FIXME/secrets).
```

**Finance data checker** — finance-specific quality gate:
```markdown
---
name: finance-checker
description: Use when working with Excel, CSV, or Power BI files to verify data
  integrity, spot formula errors, and flag unexpected nulls or negative values.
tools: Read, Bash
---
1. Check row counts before and after any merge/filter step.
2. Flag any column with >5% nulls.
3. Flag any numeric column with values outside [0, 1M] range (likely data error).
4. Report as a table: Column | Issue | Count.
```

### Invoking subagents

Claude routes automatically when the `description` matches. You can also ask explicitly:
- "Use the explore subagent to map this repo before we start."
- "Delegate test writing to the test-writer subagent — keep main context clean."
- "Run the code-reviewer subagent on the files we just edited."

---

## Part 2 — Hooks

### What hooks are

Hooks are **shell commands that fire automatically at fixed lifecycle points** — deterministic,
regardless of what Claude decides. You can ask Claude to run a linter; Claude might skip it.
A hook *always* fires.

### All 6 lifecycle events

| Event | Fires when | Can block? | Best for |
|-------|-----------|-----------|---------|
| `SessionStart` | Session opens | No | Load project state, log start |
| `UserPromptSubmit` | You hit Enter | Yes (exit 2) | Augment/sanitise prompts, inject context |
| `PreToolUse` | Before any tool call | Yes (exit 2) | Block dangerous tools, protect .env files |
| `PostToolUse` | After tool call returns | No | Auto-lint, log tool usage |
| `PreCompact` | Before context compression | No | Save checkpoint |
| `Stop` | Claude finishes responding | No | End-of-turn checks, notify, update HANDOFF.md |

### Exit codes — how hooks control Claude

| Exit | Meaning | Effect |
|------|---------|--------|
| `0` | Pass | Claude proceeds normally |
| `1` | Error (soft) | Claude sees stdout as error message, can adapt — but is NOT hard-blocked |
| `2` | Hard block | Claude's action is **cancelled**. Stdout is shown as the reason. |

**Exit 2 is your policy enforcer.** Only works in `PreToolUse` and `UserPromptSubmit`.

### JSON output for precise blocking (PreToolUse)

Instead of plain text, output this JSON from a `PreToolUse` hook for a cleaner block:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Writing to .env files is not allowed — use Alfred .env"
  }
}
```
`permissionDecision` values: `"allow"`, `"deny"`, `"ask"` (ask prompts the user).

### The `HOOK_INPUT` environment variable

When a hook fires, `HOOK_INPUT` (and stdin) contains the action JSON:
```json
{
  "session_id": "abc123",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/src/main.py",
    "content": "...file content..."
  }
}
```
Common fields: `tool_name`, `tool_input.file_path`, `tool_input.command` (Bash), `tool_input.content`.

**Windows note:** Use `pwsh -Command "($env:HOOK_INPUT | ConvertFrom-Json).tool_input.file_path"`
instead of `jq` if jq isn't on PATH. Claude Code ships `jq.exe` — check: `jq --version`.

### Hook configuration skeleton

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"${file}\" --quiet 2>/dev/null || true" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          { "type": "command", "command": "echo \"$HOOK_INPUT\" | jq -r '.tool_input.file_path' | grep -q '\\.env$' && exit 2 || exit 0" }
        ]
      }
    ]
  }
}
```

**Matcher targets Claude Code's internal tool names:** `Write`, `Edit`, `Read`, `Bash`, `Glob`,
`Grep` — capitalised. NOT `write_file` / `read_file` (those are Cursor names).

### 8 ready-to-paste hook configs

**1. Auto-format on every write (Prettier)**
```json
"PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type":"command","command":"npx prettier --write \"${file}\" --quiet 2>/dev/null || true"}]}]
```

**2. Block reads of .env files (hard deny)**
```json
"PreToolUse": [{"matcher": "Read", "hooks": [{"type":"command","command":"echo \"$HOOK_INPUT\" | jq -r '.tool_input.file_path // \"\"' | grep -q '\\.env$' && exit 2 || exit 0"}]}]
```

**3. Block `rm -rf` in Bash**
```json
"PreToolUse": [{"matcher": "Bash", "hooks": [{"type":"command","command":"echo \"$HOOK_INPUT\" | jq -r '.tool_input.command' | grep -q 'rm -rf' && echo 'BLOCKED: rm -rf' && exit 2 || exit 0"}]}]
```

**4. Desktop notification on task complete (Windows)**
```json
"Stop": [{"hooks": [{"type":"command","command":"pwsh -Command \"[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[System.Windows.Forms.MessageBox]::Show('Task complete','Claude Code')\""}]}]
```

**5. Desktop notification (macOS)**
```json
"Stop": [{"hooks": [{"type":"command","command":"osascript -e 'display notification \"Claude Code finished\" with title \"Alfred\"'"}]}]
```

**6. Audit log — every tool call with timestamp**
```json
"PostToolUse": [{"hooks": [{"type":"command","command":"echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) $(echo $HOOK_INPUT | jq -r .tool_name)\" >> ~/.claude/tool-audit.log 2>/dev/null || true"}]}]
```

**7. Inject project context into every prompt (UserPromptSubmit)**
```json
"UserPromptSubmit": [{"hooks": [{"type":"command","command":"echo '{\"additionalContext\": \"Project: Alfred Pack. Stack: PowerShell, Python. Always use Windows paths.\"}'"}]}]
```
*Output JSON with `additionalContext` key — Claude sees this prepended to the prompt.*

**8. Auto-format Python with Black**
```json
"PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type":"command","command":"echo \"$HOOK_INPUT\" | jq -r '.tool_input.file_path // \"\"' | grep -q '\\.py$' && black \"$(echo \"$HOOK_INPUT\" | jq -r .tool_input.file_path)\" --quiet || true"}]}]
```

### Hook safety rules

- End async hook commands with `|| true` — a failing `PostToolUse` hook should not abort Claude.
- Only use `exit 2` in `PreToolUse` / `UserPromptSubmit` (the blocking events).
- Keep hooks fast — >5s per hook slows every tool call. Move slow work to `Stop`.
- Test the command in a terminal with a mock `HOOK_INPUT` before wiring to settings.
- Project `.claude/settings.json` overrides global `~/.claude/settings.json`.

---

## Part 3 — End-of-turn quality gate

Use the `Stop` event to run a deterministic check after every Claude response. If checks fail,
Claude sees the failure and can self-correct on the next turn.

```json
"Stop": [{"hooks": [{"type": "command", "command": ".claude/hooks/end-of-turn-check.sh"}]}]
```

```bash
#!/bin/bash
# .claude/hooks/end-of-turn-check.sh
FAILS=()

# Syntax check any staged .py files
git diff --name-only --cached 2>/dev/null | grep '\.py$' | while read f; do
  python -m py_compile "$f" 2>/dev/null || FAILS+=("Syntax error: $f")
done

# Check HANDOFF.md updated this session (within 5 min)
if [ -f HANDOFF.md ]; then
  AGE=$(( $(date +%s) - $(date -r HANDOFF.md +%s 2>/dev/null || echo 0) ))
  [ "$AGE" -gt 300 ] && FAILS+=("HANDOFF.md not updated this session")
fi

if [ ${#FAILS[@]} -gt 0 ]; then
  echo "End-of-turn check FAILED:"; printf '  - %s\n' "${FAILS[@]}"; exit 1
fi
echo "End-of-turn checks passed."
```

---

## Decision guide

```
"Claude must always know X"           → CLAUDE.md / AGENTS.md
"Invoke a workflow with /command"     → Skill in .claude/commands/
"Auto-delegate exploratory work"      → Subagent in .claude/agents/
"Must happen regardless of Claude"    → Hook in settings.json
"BLOCK Claude from doing something"   → PreToolUse hook with exit 2
```

---

## Try asking

**Subagents:**
- "Create a .claude/agents/ folder with a repo-explorer subagent (uses claude-haiku, returns file tree) and a code-reviewer subagent for post-edit quality checks."
- "Write me a finance-checker subagent that verifies row counts, null rates, and outlier values whenever I'm working with Excel or CSV data."
- "We've finished the edits — delegate a review to the code-reviewer subagent, bring back only High severity issues."

**Hooks:**
- "Add a PreToolUse hook that blocks Claude from reading any file ending in .env — use exit code 2 and explain the HOOK_INPUT JSON shape."
- "Add a Stop hook that shows a Windows desktop notification when Claude Code finishes — show me the exact JSON for settings.json."
- "Add a UserPromptSubmit hook that injects my project name and tech stack into every prompt I send, so I stop repeating context."
- "Explain exit codes for PreToolUse hooks — what happens at exit 0, 1, and 2? When should I use each?"
- "Show me the structured JSON output format for denying a PreToolUse action with a clear reason message."
- "Write an end-of-turn Stop hook that checks for Python syntax errors in staged files and warns me if HANDOFF.md hasn't been updated."

**Understanding the system:**
- "What's the difference between a subagent and a hook? Give me an example of when I'd use each for a finance report task."
- "Show me the HOOK_INPUT JSON shape for a PreToolUse Write event — what fields can I match against?"
- "What are all the Claude Code lifecycle events? Which ones can block Claude's action and which can't?"

---

## Setup

Subagents and hooks are built into Claude Code — no additional install needed.

**Subagent directories:**
- Project-level: `.claude/agents/` (git-tracked, shared with team)
- Global: `~/.claude/agents/` (personal specialists, available everywhere)

**Hooks config:**
- Global: `~/.claude/settings.json`
- Project override: `.claude/settings.json`

**Available in Claude Code:** 1.7+ (subagents), 1.9+ (full hooks including `UserPromptSubmit` + JSON output).
**Available after next provision:** Syncs to `~/.claude/skills/` on next `Provision-Cursor.ps1` run.
This skill is Claude Code only — Cursor uses rules and parallel agents instead.
