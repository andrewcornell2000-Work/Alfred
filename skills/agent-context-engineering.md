# Agent Context Engineering

Use this skill when an agent loop goes off-track, drifts, forgets earlier decisions, or wastes
tokens re-reading things it already saw. Context engineering is the discipline of deciding **what
goes into the context window, in what order, and how to manage it over time** — the layer above
individual prompt engineering.

*Companion skills: `agent-reasoning.md` (decompose tasks), `agent-token-efficiency.md` (tactical
tool choices). This skill covers the structural design of what fills the window.*

---

## 1. Anatomy of an agent context window

Every token in the context window competes for the model's limited attention. Know what's eating space:

| Layer | What fills it | Managed by |
|-------|--------------|------------|
| **System prompt** | Persona, rules, tool list | Alfred / Cursor rules file |
| **Memory blocks** | Stable facts (team conventions, paths, TaskKey format) | `memory` MCP |
| **Tool schemas** | MCP tool names + descriptions | Auto-injected; trim bad ones |
| **Conversation history** | Prior turns, tool calls, results | Compressor or summariser |
| **Retrieved context** | RAG chunks, file snippets, search results | You control what you inject |
| **Scratchpad / working state** | Current plan, intermediate results | Explicit in-message structure |

**Rule:** Every layer you let grow unchecked eventually crowds out the layers that matter.

---

## 2. Write context before you need it

**Externalise everything reusable.** If a fact will be needed again, write it somewhere persistent
*immediately*, before it scrolls out of window.

### Tools to write context

- **`memory` MCP** — store stable team knowledge (TaskKey format, finance folder layout, approved
  measures list). Call `memory_create_entities` or `memory_add_observation` right after confirming
  a convention. Zero tokens to retrieve (already in system prompt at next session).
- **Markdown files in repo** — append decisions to `decisions/YYYY-MM.md` or a SCRATCH.md during
  a multi-hour session. Use `filesystem` MCP to write; costs ~50 tokens to read back.
- **Code comments** — after a refactor, write a 2-line header comment explaining *why* the shape
  was chosen. Future sessions read code, not your previous explanation.

### Anti-pattern
Relying on scrollback. If you close and reopen a session, the model starts fresh. Write it down.

---

## 3. Select context — only inject what's relevant

"More context = better answers" is a myth past ~20k tokens. Irrelevant content increases hallucination
and buries signal.

### Selection checklist

- [ ] Use `grep` / `rg` / `ctx_search` (LeanCTX) to find the 10–40 relevant lines, not whole files
- [ ] For a DAX question: inject the measure + the 3 related tables, not the full model JSON
- [ ] For a Power Query error: inject only the failing step + previous step, not all 30 steps
- [ ] For a code change: use `ctx_read` in map mode first → then expand only the relevant functions
- [ ] Remove examples once they've been applied — they consume tokens without adding new signal

### RAG instead of paste

When context is larger than ~5 pages, prefer retrieval over paste:
- `context7` MCP: injects only the relevant doc sections for the library/version being used
- `duckdb`/`sqlite` MCP: run SQL to answer a question instead of pasting the whole CSV
- `markitdown` MCP: convert PDF to plain text *then* search it — don't dump 50 pages into chat

---

## 4. Compress context — stop it growing unbounded

Long agent loops accumulate tool outputs, intermediate results, and error traces. Compress before
the window fills.

### Techniques

**Summarise completed sub-tasks.** After each phase of a multi-step task, write a 3-bullet summary
and ask the model to proceed from the summary rather than the full transcript:

> "Summarise what we've confirmed so far in 3 bullets, then continue with the next step."

**Truncate verbose tool outputs.** Tool results like `ls` listings, full API responses, or stack
traces should be summarised immediately. Example pattern:

> "[Truncated to key lines] Error on line 47: KeyError 'site_id'. Full trace saved to SCRATCH.md."

**Write a numbered plan in chat before complex edits.** Before a multi-file change, outline steps in ~200 tokens instead of exploratory tool churn.

**KV-cache awareness.** If you're using a frontier model with KV-cache billing:
- Keep the system prompt and memory blocks *identical* across turns — every character change
  destroys the cache hit and increases cost.
- Append only to the *end* of the context; never insert or modify earlier content mid-session.
- Write stable reference material (conventions, schema) into the system prompt once and never
  change it during a session.

---

## 5. Isolate context — multi-agent and sub-task patterns

When a task has independent branches, don't mix their contexts. Run them in separate windows or
agent instances so errors don't cross-contaminate.

### When to isolate

- A code-change task and a documentation task triggered by the same PR — run in parallel Cursor
  chats, each scoped to their own file set.
- A Power BI model edit and a Power Query fix — separate Cursor composers; they share no files.
- Research (Tavily) and execution (Codex/Claude Code) — keep research results as a written
  artefact, not raw chat history, before handing off to the execution agent.

### Handoff pattern (write → select → execute)

```
1. RESEARCH AGENT  →  writes summary to SCRATCH.md (filesystem MCP)
2. PLANNING AGENT  →  reads SCRATCH.md, writes step-by-step plan to PLAN.md
3. EXECUTION AGENT →  reads PLAN.md + scoped file context only
                       never sees the full research transcript
```

This keeps each agent's context window small and focused.

---

## 6. MCP tool description quality

The agent sees MCP tool descriptions as injected text. Poorly written descriptions waste tokens and
cause wrong tool selection.

### What makes a good tool description (from arXiv 2025 research)

| Component | Good example | Bad example |
|-----------|-------------|-------------|
| **Purpose** | "Query DuckDB tables with SQL" | "Database tool" |
| **Trigger conditions** | "Use when user has a CSV or Parquet file" | (missing) |
| **What it returns** | "Returns rows as JSON array" | (missing) |
| **Parameter guidance** | "`query`: valid SQL string, SELECT only" | "`query`: string" |
| **Negative scope** | "Does not write; read-only" | (missing) |
| **Example** | `SELECT site_id, SUM(hours) FROM wages GROUP BY 1` | (missing) |

**Six components = good description.** Missing even two causes measurable tool-selection errors.

### In Alfred's pack

When registering a new MCP or CLI, the companion skill doc **is** the tool description extended.
Cursor/Claude read the skill during provisioning. Write all six components in the How-to section.

---

## 7. Context engineering checklist — before a complex task

Run through this before kicking off any multi-step agent task in Cursor:

- [ ] **Write stable facts to memory** — primed LeanCTX `ctx_knowledge` with team conventions for this project?
- [ ] **Scope the file set** — identified the 3–10 files this task actually touches (use LeanCTX map mode)?
- [ ] **Clear irrelevant history** — opened a fresh Cursor composer for this sub-task?
- [ ] **Plan before edit** — write a short step list in chat before any file changes?
- [ ] **Set a compress point** — decided at which step you'll summarise and discard raw tool output?
- [ ] **KV-stable prefix** — system prompt and rules file unchanged from the last session?
- [ ] **Handoff artefact** — if handing to another agent or Codex, is the handoff written to a file (not just in chat)?

---

## 8. Alfred-specific patterns

### LeanCTX as context budget manager (optional)

Use native Read/Grep first. For large files or re-reads, lean-ctx can reduce tokens:

```
ctx_read(file, mode="map")      →  ~200 tokens — structure overview
ctx_read(file, start=40, end=80) →  ~40 tokens  — targeted line range
ctx_search(query, files=[...])   →  ~50 tokens  — semantic hit list
```

Compare: reading a 400-line file with standard `read_file` costs ~3 000 tokens.
LeanCTX map mode costs ~200 tokens when you already know the file is large.

### Session memory (LeanCTX, not memory MCP)

At the start of a long or multi-day task:

```
ctx_knowledge(action="recall", query="alfred pack conventions")
ctx_knowledge(action="remember", content="confirmed fact …")
```

The retired memory MCP is not provisioned — use `ctx_knowledge` only.

### Scratch file pattern for long sessions

If a session will span >1 hour or >15 tool calls:

```
Create: SCRATCH.md in repo root (gitignored)
Write:  confirmed facts, intermediate results, partial plans as you go
Read:   at compress points, summarise SCRATCH into 5 bullets and continue
Delete: at session end (or let .gitignore handle it)
```

---

## Try asking:

- "Use LeanCTX map mode on the backend folder, then pick the 3 files relevant to the routing change — don't open anything else yet"
- "Summarise what we've confirmed so far in 3 bullets so we can compress the context, then continue with step 4"
- "Store the TaskKey format convention we just confirmed in LeanCTX knowledge so I don't have to explain it next session"
- "Outline a numbered plan in chat before touching any file on this refactor"
- "I'm about to hand this plan to Codex — write a clean handoff summary to SCRATCH.md covering what's been decided and what files to touch"
- "What MCP tools are available for this task? List them with their trigger conditions before you pick one"

---

## Related skills

| Skill | Covers |
|-------|--------|
| `agent-token-efficiency.md` | Tactical tool choices to save tokens |
| `agent-reasoning.md` | Decompose + verify + act pattern |
| `lean-ctx.md` | LeanCTX MCP usage in detail |
