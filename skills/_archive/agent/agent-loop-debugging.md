# Agent Loop Debugging & Recovery

Use this skill when a Cursor or Claude Code agent goes wrong mid-task:
gets stuck, spins in circles, silently produces wrong output, or drifts away from the goal.

*Companion skills: `agent-reasoning.md` (plan before acting), `agent-context-engineering.md`
(manage what's in the window), `agent-token-efficiency.md` (tool choice discipline).*

---

## The six failure modes — and how to recognise them

| Mode | What you see | Root cause |
|------|-------------|------------|
| **Tool misuse** | Agent calls the wrong MCP, wrong args, or retries with identical broken params | Tool descriptions are ambiguous; agent guessed |
| **Context loss** | Agent forgets an earlier decision, re-asks what was already confirmed, repeats a step | Conversation scrolled past context window; no external write |
| **Goal drift** | Agent solves a related-but-different problem; output is "technically correct" but not what you asked | Original goal wasn't re-anchored after a detour |
| **Retry loop** | Agent calls the same tool 5+ times with tiny variations and never progresses | No backoff strategy; tool error not being read correctly |
| **Cascading failure** | One wrong step (wrong column name, wrong file) corrupts every downstream step silently | No checkpoint/verify after each phase |
| **Sycophantic confirmation** | Agent says "Done!" — but didn't do it, or only partially did it | Confirmation bias; agent completed the turn without completing the task |

---

## Diagnosis: 5 questions to ask first

Before restarting, scroll back and answer these:

1. **Where did it last succeed?** Find the last correct tool result in the conversation.
2. **Did it read the right file / table / sheet?** Check the exact path or name in the tool call — typos are silent.
3. **Did a tool return an error the agent ignored?** Search the transcript for `error`, `exception`, `not found`.
4. **Did the goal change mid-session?** If you added a new instruction after the agent started, it may be chasing two conflicting goals.
5. **Is the output actually empty or truncated?** Many "I've done it" responses have 0-byte files or cut-off content.

---

## Recovery playbook by failure mode

### Tool misuse — wrong tool, wrong args

**Symptoms:** Repeated `tool_use` blocks with slightly varied args; error text in tool result that the agent ignores.

**Fix:**
```
Stop. The tool call is failing because [paste the error]. 
Do not retry the same call. Instead: [describe the right approach explicitly].
If you're unsure which tool to use, ask me before calling anything.
```

**Prevent:** Check `cursor/mcp.json` `_note` fields — each MCP has an explicit use-case guard.
Ambiguous tool descriptions are the #1 cause. If an MCP is misfiring, improve its `_note` field.

---

### Context loss — forgot earlier decisions

**Symptoms:** Agent re-asks something you already answered; re-reads a file it summarised two steps ago; reverts a change.

**Fix — anchor the goal every 10-15 turns:**
```
Before continuing: summarise the current state in 3 bullets
(what's confirmed, what's done, what's left). Then proceed.
```

**Fix — write decisions externally mid-session:**
- Use `filesystem` MCP to append to a `SCRATCH.md` in the repo root
- Store key facts in LeanCTX: `ctx_knowledge set <key> <value>`
- Say "checkpoint: we confirmed X — remember this" explicitly in chat

**Prevent:** For sessions > 30 turns, proactively write a checkpoint every 10 turns.

---

### Goal drift — solving the wrong problem

**Symptoms:** Agent produces something polished but not what you asked; explains at length why its variation is better.

**Fix — re-anchor the original goal:**
```
Pause. The original goal was: [paste your first message].
What you've done [describe it] does not satisfy that goal because [reason].
Return to the original goal. Do not improvise.
```

**Fix — use a goal header in long sessions:**
```
GOAL (do not change): <one sentence>
CURRENT STEP: <step number>
CONSTRAINTS: <anything non-negotiable>
```
Put this at the top of every fresh agent invocation for complex multi-day tasks.

---

### Retry loop — same call, no progress

**Symptoms:** 5+ identical or near-identical tool calls; conversation growing rapidly with no new information.

**Fix — interrupt immediately:**
```
Stop all tool calls. You have attempted [tool name] N times without success.
Describe the error you're seeing and list 3 different approaches before trying again.
```

**Prevent — build backoff into your task prompt:**
```
If any tool call fails, do not retry more than once with the same parameters.
After 2 failures, stop and explain what's wrong before asking permission to continue.
```

---

### Cascading failure — corrupted from step 1

**Symptoms:** Final output is wrong but agent reported success throughout; bug traces back to step 1 or 2.

**Fix — replay from the last good checkpoint:**
1. Find the last step where output was verifiably correct (re-read the actual file/result).
2. Discard everything after that point.
3. Restart from that step with an explicit: "Start from [step N]. The state at that point was: [paste]."

**Prevent — checkpoint after every destructive step:**
```
After each of the following steps, confirm the result before proceeding:
1. [step] — success check: [what I'll verify]
2. [step] — success check: [what I'll verify]
```

---

### Sycophantic confirmation — "Done!" but it isn't

**Symptoms:** Agent says task is complete; output file is empty, measure is missing, PR wasn't opened.

**Fix — demand evidence:**
```
Show me the evidence this is done:
- Read back the file you wrote and paste the first 5 lines.
- Confirm the row count / measure name / PR number.
Do not say "done" until you've shown me one of these.
```

**Prevent — make completion criteria explicit at the start:**
```
Task complete means:
- [File X exists and contains Y]
- [Measure Z returns N when filtered to FY25]
- [PR is open at URL]
Do not stop until all three are true.
```

---

## Pre-flight checklist — before a long agent task

Run this before any task that will take >10 tool calls:

- [ ] Write the goal in one sentence at the top of the prompt
- [ ] List completion criteria (what does "done" look like — measurably)
- [ ] Specify the constraint: "Do not edit any file outside folder X"
- [ ] Set retry policy: "If a tool fails twice, stop and explain"
- [ ] Set checkpoint policy: "After each phase, confirm result before proceeding"
- [ ] Identify reversible vs. irreversible actions: flag the irreversible ones for approval
- [ ] Specify output format: "Write the result to `output.md` — do not just print it in chat"

---

## Recovery template — paste this when an agent is stuck

```
RECOVERY CHECKPOINT

State at failure:
- I asked you to: [original goal]
- You last successfully completed: [last good step]
- The error or problem is: [describe it]

Rules for recovery:
- Do not retry the failing approach
- List your 3 options before choosing one
- After each step, confirm it worked before the next
- If you're unsure, ask me — don't guess

Continue from: [specific step]
```

---

## Structured output — enforce a machine-readable result

When the agent's output feeds another tool (a script, a dashboard, a Power Query formula), free-text
answers cause downstream failures. Enforce structure upfront.

### For data/tables
```
Return the result as a markdown table with exactly these columns:
| Column A | Column B | Column C |
Do not include narrative before or after the table.
```

### For code patches
```
Return only the modified function, wrapped in a single code fence.
Do not include explanation outside the code fence.
```

### For lists of actions taken
```
Return a JSON array of objects:
[{"step": 1, "action": "...", "file": "...", "result": "success|fail", "detail": "..."}]
```

### For DAX measures
```
Return only the complete DAX expression starting with the measure name.
No preamble. No alternatives. No explanation unless I ask.
```

### Claude Code structured output (SDK pattern)
Claude Code's agent SDK accepts a `jsonSchema` parameter — it injects a synthetic tool that forces
the final response to match the schema. Use this for any automated pipeline where the output
is consumed by code, not a human.

---

## Try asking:

**"My agent keeps calling the filesystem tool over and over and not finishing. How do I stop it?"**

**"Give me a pre-flight checklist prompt I can paste before I start a long Cursor agent session."**

**"My agent said 'done' but the output file is empty. How do I debug that?"**

**"Write me a recovery checkpoint prompt — the agent drifted off from the original goal halfway through."**

**"I want the agent to return a markdown table and nothing else — how do I enforce that?"**

**"What are the six ways an AI agent fails and how do I diagnose which one I'm dealing with?"**

---

## Quick reference card

| I see… | Failure mode | First fix |
|---------|-------------|-----------|
| Same tool called 5+ times | Retry loop | "Stop. List 3 alternatives first." |
| Agent re-asks what you told it | Context loss | "Summarise state, then continue." |
| Output is correct but not what you wanted | Goal drift | "Re-read my original goal. Restart." |
| Agent says done — output is wrong/empty | Sycophantic confirmation | "Show evidence. Read back what you wrote." |
| Later steps are wrong, root is step 1 | Cascading failure | "Roll back to last good checkpoint." |
| Wrong MCP, wrong file, wrong args | Tool misuse | "Stop. Explain the error. Ask before retrying." |
