# Claude Code Subagents & Hooks

Use this skill when you want Claude Code to **delegate work to specialist sub-workers** (subagents)
or **fire deterministic scripts automatically** at key points in its lifecycle (hooks).

These are two distinct power features most users never configure. Together they turn Claude Code
from a conversational tool into a programmable, automated engineering system.

*Companion skills: `agent-parallel-worktrees.md` (parallel branches), `agent-workflow-orchestration.md`
(multi-step chains), `agents-md-project-context.md` (project-wide context), `agent-handoff.md`
(cross-session continuity).*

---

## The four layers of Claude Code customisation

Understanding what each layer does prevents confusion about when to use which:

| Layer | File / location | Loads when | Purpose |
|-------|----------------|-----------|---------|
| **CLAUDE.md / AGENTS.md** | repo root or `~/.claude/CLAUDE.md` | Every session, always | Project rules, boundaries, build commands |
| **Skills** | `~/.claude/commands/*.md` or `.claude/commands/` | On `/skill-name` slash command | Reusable workflows you invoke explicitly |
| **Subagents** | `.claude/agents/*.md` | When Claude delegates to them | Specialist workers with isolated context windows |
| **Hooks** | `~/.claude/settings.json` `hooks` block | Automatically at lifecycle events | Deterministic shell commands at fixed trigger points |

**Rule of thumb:** CLAUDE.md tells Claude what to know always. Skills tell Claude how to do something when asked. Subagents let Claude offload heavy work to a specialist. Hooks run code regardless of what Claude decides.

---

## Part 1 — Subagents

### What a subagent is

A subagent is a **separate Claude Code instance with its own isolated context window**, spawned by
the main agent (the "orchestrator") to do a focused piece of work. The orchestrator doesn't balloon
its own context with exploratory file reads — it delegates to a subagent that handles the search
and reports back a clean summary.

**Key insight:** This is exactly how Cursor's built-in "Plan mode" works under the hood — it spins
up an Explore subagent to scan the repo, keeping the main planning thread clean.

### When to use a subagent vs. a skill

| Use a **skill** when… | Use a **subagent** when… |
|-----------------------|--------------------------|
| You want a repeatable workflow you invoke with `/command` | You want Claude to automatically delegate without you asking |
| The task is conversational (back-and-forth) | The sub-task is self-contained with a clear output |
| The task is small and fits in the current context | The sub-task would balloon the current context (big file scan) |
| You want to trigger it manually | You want automatic delegation during plan/execute cycles |

### Anatomy of a subagent file

Subagents live in `.claude/agents/` (project-level) or `~/.claude/agents/` (global / all projects).

```markdown
---
name: code-reviewer
description: Specialist for reviewing changed files for bugs, style issues, and security problems.
  Use when the user asks for a code review or when plan mode completes a set of edits.
tools: read_file, grep_search
---

You are a careful, opinionated code reviewer. When activated:

1. Identify all files that changed in this task (ask the orchestrator if not told).
2. For each file, check for:
   - Logic errors or off-by-one bugs
   - Hardcoded credentials or secrets
   - Functions longer than 50 lines (flag, don't rewrite)
   - Missing error handling on I/O operations
3. Return a markdown table: File | Issue | Severity (High/Medium/Low) | Suggested fix.
4. If no issues found, say "No issues found in [N] files reviewed."

Be terse. The orchestrator will relay your output to the user.
```

**Front-matter fields:**

| Field | Required | What it does |
|-------|----------|-------------|
| `name` | Yes | Identifier. Claude uses this to select the right subagent. |
| `description` | Yes | The routing hint — Claude reads this to decide when to delegate here. Write it like "Use when…" |
| `tools` | Optional | Comma-separated list of tools this subagent is allowed to use. Omit = inherits session defaults. |
| `model` | Optional | Override the model (e.g. `claude-haiku-4-5` for cheap exploratory tasks). |

### The description field is the selector — write it carefully

Claude decides which subagent to invoke based on the `description`. A vague description means
wrong routing. A good description answers: "What situation triggers this specialist?"

**Bad:** `description: Helps with code.`

**Good:** `description: Use when reviewing changed files after an edit session, or when the user says 'review my changes' or 'check my code'. Returns a structured table of issues.`

### Practical subagents to create today

**1. Repo explorer — keeps scan cost off the main context**
```markdown
---
name: explore
description: Use at the start of any plan or implementation task to map the relevant files
  and folders without loading them into the main context. Returns a concise file tree
  and summary of key entry points.
tools: read_file, list_directory, grep_search
model: claude-haiku-4-5
---

You are a fast repo navigator. Given a task description from the orchestrator:
1. List the top-level folders and their purpose (2 sentences max each).
2. Find the 3-5 files most relevant to the task using grep or directory listing.
3. For each file: name, one-line purpose, approximate line count.
4. Return a markdown summary. Do NOT open full file contents.
```

**2. Code reviewer — post-edit quality gate**
```markdown
---
name: code-reviewer
description: Use after completing edits to review changed files for bugs, hardcoded secrets,
  missing error handling, and style issues. Invoke when the user asks for review or when
  a plan phase ends.
tools: read_file, grep_search
---
[review instructions as shown above]
```

**3. Test writer — isolated context for test generation**
```markdown
---
name: test-writer
description: Use when asked to write tests for a function or module. Reads the source file
  and generates pytest or Jest tests with edge cases. Returns tests as a code block ready
  to save.
tools: read_file
---

You are a test engineer. Given a source file:
1. Identify all public functions/methods.
2. For each: write 3 test cases (happy path, edge case, error case).
3. Return the complete test file as a code block.
4. Note any function that is hard to test (no return value, heavy side effects) — suggest a fix.
```

**4. Document summariser — compress large files without context cost**
```markdown
---
name: summarise
description: Use when asked to understand a large file, PDF, or document without loading
  the full content into the main context. Returns a structured summary.
tools: read_file
model: claude-haiku-4-5
---

Summarise the provided file in this structure:
- **Purpose:** one sentence
- **Key sections:** bullet list of major sections/functions
- **Important values or constants:** any hardcoded config, URLs, or thresholds
- **Dependencies:** what this file imports or calls
- **Red flags:** anything unusual (TODO, FIXME, hardcoded secrets, deprecated APIs)
```

### Invoking subagents

You don't invoke subagents directly — **Claude orchestrates them**. Your job is to write the
subagent files. Claude will route to them when the `description` matches the situation.

You can also ask explicitly:
- "Use the explore subagent to map this repo before we start."
- "Delegate the test writing to the test-writer subagent — I want the main context kept clean."
- "Run the code-reviewer subagent on the files we just edited."

---

## Part 2 — Hooks

### What hooks are

Hooks are **shell commands that fire automatically at fixed points in Claude Code's lifecycle**.
They are deterministic — they always run at the trigger point, regardless of what Claude decides.
This is the layer you use when you need a guarantee, not a request.

**The difference:** You can ask Claude "run the linter after every edit." Claude might forget, or
decide to skip it. A hook *always* fires. No asking required.

### Hook trigger points (lifecycle events)

| Event | Fires when | Typical use |
|-------|-----------|-------------|
| `PreToolUse` | Before Claude calls any tool | Block dangerous tools, validate before file edits |
| `PostToolUse` | After Claude's tool call returns | Auto-lint after file edits, log tool usage |
| `PreCompact` | Before context is compressed | Save a checkpoint before the context shrinks |
| `PostSessionEnd` | When the session closes | Auto-update HANDOFF.md, run post-session tests |
| `UserPromptSubmit` | When you hit Enter on your prompt | Sanitise input, log prompts, inject context |
| `Stop` | When Claude finishes responding | Notify on task completion, trigger downstream |

### Hook configuration — `~/.claude/settings.json`

Hooks live in the `hooks` block of Claude Code's settings file:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "write_file",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix \"${file}\" --quiet"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Claude Code task complete' | powershell -Command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Claude Code finished', 'Alfred')\""
          }
        ]
      }
    ]
  }
}
```

**The `matcher` field:** Optional regex matching the tool name. Omit it to fire on all events
of that type. Use it to target specific tools (e.g. `"matcher": "write_file"` fires only when
Claude writes a file, not when it reads one).

### The 10 most useful hooks (practical configs)

**1. Auto-lint on every file edit** — never commit unformatted code
```json
"PostToolUse": [{
  "matcher": "write_file",
  "hooks": [{"type": "command", "command": "npx eslint --fix \"${file}\" --quiet 2>/dev/null || true"}]
}]
```

**2. Secret scanner — block before commit** — stops secrets reaching your repo
```json
"PreToolUse": [{
  "matcher": "bash",
  "hooks": [{"type": "command", "command": "git diff --staged | grep -iE '(api_key|secret|password|token)\\s*=' && echo 'BLOCKED: potential secret detected' && exit 1 || true"}]
}]
```

**3. Auto-run tests after file edits** — instant feedback loop
```json
"PostToolUse": [{
  "matcher": "write_file",
  "hooks": [{"type": "command", "command": "npm test -- --watchAll=false --passWithNoTests 2>&1 | tail -5"}]
}]
```

**4. Desktop notification when task completes** — don't stare at the terminal
```json
"Stop": [{
  "hooks": [{"type": "command", "command": "powershell -Command \"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('Done', 'Claude Code')\""}]
}]
```
*(Windows only — macOS: `osascript -e 'display notification "Done" with title "Claude Code"'`)*

**5. Auto-update HANDOFF.md at session end** — never forget to update it
```json
"PostSessionEnd": [{
  "hooks": [{"type": "command", "command": "echo '# Session ended: '$(date) >> HANDOFF.md"}]
}]
```

**6. Log all tool calls for audit** — see exactly what Claude touched
```json
"PostToolUse": [{
  "hooks": [{"type": "command", "command": "echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) ${tool} ${file:-}\" >> ~/.claude/tool-audit.log"}]
}]
```

**7. Block writes to sensitive directories** — hard stop before damage
```json
"PreToolUse": [{
  "matcher": "write_file",
  "hooks": [{"type": "command", "command": "echo \"${file}\" | grep -qE '/(finance|secrets|legacy)/' && echo 'BLOCKED: protected directory' && exit 1 || true"}]
}]
```

**8. Auto-format Python after edit** — keep Black happy
```json
"PostToolUse": [{
  "matcher": "write_file",
  "hooks": [{"type": "command", "command": "echo \"${file}\" | grep -q '\\.py$' && black \"${file}\" --quiet 2>/dev/null || true"}]
}]
```

**9. Checkpoint before context compaction** — don't lose decisions mid-session
```json
"PreCompact": [{
  "hooks": [{"type": "command", "command": "claude -p 'Write a 5-bullet summary of what we have decided so far and save it to CHECKPOINT.md' --output-format text > CHECKPOINT.md 2>/dev/null || true"}]
}]
```

**10. Slack / Teams notification on task end** — useful for long overnight runs
```json
"Stop": [{
  "hooks": [{"type": "command", "command": "curl -s -X POST \"${SLACK_WEBHOOK}\" -d '{\"text\":\"Claude Code task finished\"}' > /dev/null 2>&1 || true"}]
}]
```

### Hook safety rules

- **Always end commands with `|| true`** — a failing hook should not abort the Claude session.
- **Keep hooks fast** — hooks that take >5 seconds slow down every tool call. Move slow work to `PostSessionEnd`.
- **Use `PreToolUse` to block, `PostToolUse` to fix** — blocking before is safer than cleaning up after.
- **Test hooks manually first** — run the shell command in a terminal before adding it to settings.

---

## Decision guide — which layer do I need?

```
"I want Claude to always know X about my project"
  → CLAUDE.md / AGENTS.md

"I want to invoke a workflow by typing /command"
  → Skill in .claude/commands/

"I want Claude to automatically delegate exploratory/specialist work"
  → Subagent in .claude/agents/

"I want something to happen automatically regardless of what Claude decides"
  → Hook in settings.json
```

---

## Try asking

Paste these into Claude Code or Cursor to put this skill into practice:

**Set up subagents:**
- "Create a .claude/agents/ folder with a repo-explorer subagent that maps relevant files without loading them into the main context, and a code-reviewer subagent for post-edit quality checks."
- "I want a summarise subagent that reads large files and returns structured summaries — write the agents/summarise.md file for me."
- "Write me a test-writer subagent that uses claude-haiku to keep costs low — it should produce pytest tests for any Python function I point it at."

**Configure hooks:**
- "Add a PostToolUse hook to my Claude Code settings that auto-lints JavaScript files with ESLint after every write — show me the exact JSON to add to settings.json."
- "Add a Stop hook that shows a Windows desktop notification when Claude Code finishes a task, so I don't have to watch the terminal."
- "Add a PreToolUse hook that blocks any write_file call to a path containing /finance/ — I want a hard stop, not just a warning."
- "Show me a hook that logs every tool call with timestamp to a file — I want an audit trail of what Claude touched in each session."

**Use subagents explicitly:**
- "Before we start, use the explore subagent to map this repo — I don't want file reads filling up our main context."
- "We've finished the edits. Delegate a review to the code-reviewer subagent and bring back only the High severity issues."
- "I have a 4,000-line Python file. Use the summarise subagent to extract the key structure — don't read the whole thing into our context."

**Understand the system:**
- "Explain the difference between a Claude Code skill, a subagent, and a hook — and give me an example of when I'd use each one for a finance report task."
- "What's in my .claude/agents/ folder right now? List all subagents and describe when each one gets invoked."

---

## Setup

Subagents and hooks are built into Claude Code — no additional install needed.

**Subagent directories:**
- Project-level: `.claude/agents/` (in your repo — checked into git, shared with team)
- Global: `~/.claude/agents/` (your personal specialists, available in every project)

**Hooks config location:**
- `~/.claude/settings.json` (global — applies to all sessions)
- `.claude/settings.json` (project-level — overrides global for this repo)

**To see current settings:**
```bash
cat ~/.claude/settings.json
```

**To create your first subagent:**
```bash
mkdir -p .claude/agents
# Then create .claude/agents/explore.md with the content from the "Repo explorer" example above
```

**Available in Claude Code version:** 1.7+ (subagents), 1.9+ (full hooks suite).
**Available after next provision:** Skills sync to `~/.claude/skills/` on next `Provision-Cursor.ps1` run.
This skill is for Claude Code only — Cursor does not have subagents or lifecycle hooks (use rules/parallel agents instead).
