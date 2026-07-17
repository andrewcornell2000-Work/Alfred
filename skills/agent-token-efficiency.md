# Agent Token Efficiency

Use this skill when driving Claude Code, Codex, or Cursor agents on multi-step tasks.
Goal: same outcome, fewer tokens — without cutting corners on correctness.

---

## 1. Core token rules

1. **Search before read** — use `grep` / `rg` / targeted `SemanticSearch` to find the right file and line range before opening whole files.
2. **Read partial files** — use line offsets and limits; never dump a 2000-line file when 40 lines answer the question.
3. **One tool per job** — prefer the narrowest tool:
   - Live Excel open → `excel` MCP, not bash + openpyxl
   - Power BI model → `powerbi-modeling-mcp` or `pbi`, not re-describing the whole model in chat
   - Web facts → parallel-search or fetch, not pasting long page HTML into context
   - File edits in repo → editor patch, not rewrite entire file in the reply
4. **Batch independent lookups** — parallel tool calls when queries do not depend on each other.
5. **Do not re-read** — if content is already in the conversation, reference it; do not `read_file` again.
6. **Structured output over prose** — tables, bullet deltas, and code citations beat long explanations.

---

## 2. Effort levels — the single biggest lever in Claude Code / Cursor

Claude Code has five effort levels that control how many tokens Claude spends **thinking** before it produces output. Using the wrong level is the most common source of unnecessary cost or poor quality.

> **In Cursor:** right-click in the agent panel → "effort" or add `/effort medium` at the start of your prompt.
> **In Claude Code:** `/effort medium` or set `settings.json → { "thinking": { "budget_tokens": 8000 } }`.

| Level | Token budget (approx.) | Use when |
|-------|----------------------|----------|
| **low** | ~1 k thinking tokens | Quick lookups: "what does this function return?" / rename / trivial one-liners |
| **medium** | ~8 k (default Claude Code) | Most standard coding tasks — refactors, adding features, writing unit tests |
| **high** | ~32 k | Multi-file refactors, architectural decisions, debugging tricky state bugs |
| **max** | ~64 k, no constraint | Novel algorithm design, full codebase audit, security review — rarely worth it day-to-day |
| **ultra code** | uncapped (Opus 4+ only) | Extremely long autonomous runs; very expensive — budget it before you start |

### Matching effort to task type

```
Trivial    → low
Routine    → medium   ← default; leave it here unless output is wrong
Complex    → high
Novel/audit → max
```

**The counterintuitive rule:** Extra thinking budget gets spent **reconstructing state you should have given it upfront**. Before bumping effort, ask: *have I given it the right context?* Context first, effort second.

### Try asking (effort control)
- "This is a simple rename — use low effort and just do it."
- "I need to audit every reference to `FTE_Cost` across the whole finance folder — use max effort so you don't miss anything."
- "The bug is intermittent and I've been chasing it for an hour. Use high effort — think step-by-step before touching any file."
- "Don't overthink this. It's a one-line fix in the logging helper. Low effort, patch it and show me the diff."
- "I want a proper architectural review of how we handle auth tokens across all three services. Take your time — this warrants max effort."

---

## 3. Extended thinking / "thinking budget" (Claude API / Cursor advanced)

Extended thinking lets the model reason in a scratchpad before it answers. **Not always better** — here is when to use it and when to skip it.

### Use extended thinking when:
- The task is a **first-principles decision** with no clear right answer (architecture, data model design)
- You are **debugging a non-obvious bug** where the symptom is far from the cause
- You need **multi-step planning** where mistakes early compound later
- Output **correctness matters more than speed** (financial formula, compliance check)

### Skip extended thinking when:
- The task is **retrieval, not reasoning** — "what does this function return?" doesn't need deep thought
- You are **inside a tight loop** (e.g., 10 sub-agent calls in sequence) — thinking cost multiplies
- Context is large but answer is small — the model will waste its budget re-reading context
- The question is **factual and the answer is in the provided document** — just read it

### Try asking (thinking control)
- "Think step by step before writing any code — explain your reasoning in bullet points first, then write."
- "Don't use extended thinking for this — it's just a lookup. Tell me which file and line."
- "Before proposing a solution, reason out loud: what are the two most likely causes of this null pointer?"

---

## 4. Prompt caching — making long sessions faster and cheaper

Claude caches the **prefix** of your context window. If your next message starts with the same tokens as the previous one, the model skips re-processing that prefix. This is automatic in Cursor and Claude Code — but you can make it work *much better* with structure.

### How cache hits work in practice

```
System prompt (stable)          ← cached after first use
Pasted file / SPEC / rules      ← cached if you don't modify it
─────────────────────────────── ← cache breakpoint
"Now do step 2: …"              ← new tokens only, cheap
```

The cache expires after **~5 minutes** of inactivity on the API, or between Cursor sessions. It persists across turns **within** a session as long as the prefix doesn't change.

### Rules for maximising cache hits

1. **Never modify the system prompt between turns.** Even one word change invalidates the entire cache.
2. **Put stable content at the top** — system prompt, rules, pasted file — and put your actual question at the bottom.
3. **Don't re-paste the same file.** Once it's in context, reference it by name. "The file we already loaded" is free; pasting it again resets the breakpoint.
4. **Don't rephrase instructions already given** — even minor rewordings move the cache breakpoint and cost full tokens.
5. **Use HANDOFF.md to preserve context between sessions** — a fresh session has no cache. The faster you rebuild the stable prefix, the sooner you get cache hits.

### Try asking (prompt caching)
- "Don't re-paste that file — you already have it. Reference the content you loaded earlier."
- "I'm going to give you the spec once. Don't ask me to repeat it — check your context window first."
- "We're starting a new session. Here's the context: [SPEC.md content]. Keep this at the top of your memory — everything I ask today builds on it."

---

## 5. MCP tools that save tokens

| MCP | Token-saving use |
|-----|------------------|
| `context7` | SDK/library docs without pasting long API pages into chat |
| `filesystem` | Finance-folder file ops without pasting directory listings into chat |
| `parallel-search` | Research question → cited excerpt, not raw HTML dump |
| `fetch` | Pull a URL to Markdown instead of browser MCP for read-only docs |
| `duckdb` | Query CSV/exports in SQL instead of loading sheets into context |
| `markitdown` | Convert PDF/Office to Markdown once; work from the text artifact |
| `firecrawl` | Clean structured extraction from JS-heavy sites — avoids Playwright cost for read-only |

---

## 6. Anti-patterns (burn tokens)

| Anti-pattern | Fix |
|---|---|
| Reading every file in a directory "to understand the project" | Ask: what specific question am I answering? Grep for that. |
| Pasting full API responses or log files into the reply | Pipe to a file; reference it; ask for key fields only |
| Re-running the same DAX query because the prior result wasn't saved | Write results to SCRATCH.md immediately |
| Using Playwright when `fetch` or `parallel-search` suffices | Playwright for interaction; fetch for read-only |
| Bumping effort level before improving context | Better context first; then increase effort |
| Asking for explanation + output in one pass | Chain it: plan first → confirm → build |
| Re-pasting the SPEC into every message | Load it once; reference it by name in subsequent turns |

---

## 7. Context compression checkpoints

On tasks that span many turns, use these prompts to compress context before it overflows:

**Checkpoint (every 20+ tool calls):**
```
Summarise what we've confirmed so far in 5 bullets — decisions made, files touched, open questions. 
Then continue with step [N].
```

**Before handing off to another agent:**
```
Write a HANDOFF.md. Include: goal, decisions made, files changed, 
current state, next step, and the one thing the next agent must NOT assume.
```

**Before a complex output:**
```
Before writing the output: state what the correct answer should be for 
[specific edge case], then write it and verify your answer matches.
```

---

## 8. Context hygiene (from former context-engineering)

- Prefer graphify / grep before dumping directories into chat
- One MCP path per job (see always-on `00-agent-tooling` rule) — do not ping-pong
- Checkpoint long sessions: 5-bullet summary of decisions, then continue
- Do not load overlapping meta-skills; planning lives in `agent-planning`

## 9. Alfred routing tie-in

Alfred routes by cost: `GENERAL` (cheap) → `CLAUDE_EXECUTION` / `POWERBI` (expensive).
When Alfred dispatches to an agent, the prompt should include **only** the scoped context needed —
not the whole repo state.

**Effort level guidance for Alfred's routed tasks:**

- Routine retrieval (file lookup, quick formula) → `GENERAL` route, low effort
- Standard coding / report work → `CLAUDE_EXECUTION`, medium effort  
- Architectural reviews, data model audits → `CLAUDE_EXECUTION`, high effort
- Full-codebase security / compliance audits → max effort, budget it explicitly

---

## Quick reference

```
Task type                   → Effort    → Thinking?
─────────────────────────────────────────────────────
Trivial rename/lookup       → low       → off
Routine feature/test        → medium    → off
Multi-file refactor         → high      → on (if debugging)
Novel algorithm/audit       → max       → on
Financial formula check     → high      → on
Sub-agent inside a loop     → low-med   → off (multiplies cost)
```
