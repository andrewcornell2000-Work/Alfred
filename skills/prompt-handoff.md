# Prompt Handoff — Durable executor prompts (Mr Smith craft)

Use this skill when the user asks for a **misinterpret-proof handoff prompt** for another agent or session — especially when they say **"Mr Smith"** or want an approved Cursor prompt block.

**Do not use this skill for ordinary planning.** Prefer Cursor Plan Mode + `agent-planning` when the goal is just to plan or research in the current chat.

*Distinct from `agent-handoff.md` — that skill is about session HANDOFF.md continuity between tools/days. This skill crafts a single executable prompt artifact.*

---

## When to use this skill

| Situation | Prefer |
|-----------|--------|
| Plan / audit / explore in this session | Cursor Plan Mode + skill `agent-planning` (no subagent) |
| Need a copy-paste HANDOFF block for a *different* agent/session | This skill **in the current agent** |
| User says "Mr Smith, …" | Same — run this skill inline (no subagent) |

Default: **stay in the current agent.** Do not spawn a planner subagent.

---

## Workflow

1. **Clarify** — at most 3 focused questions if the goal is ambiguous; skip when context is enough.
2. **Research** — if `graphify-out/graph.json` exists: `graphify query` / `path` / `explain` first; skim only files the graph points to (`AGENTS.md`, specs, rules).
3. **Classify:** `plan-only` | `plan-then-build` | `single-shot` | `explore`
4. **Draft** one prompt (format below). Ask: **Approve this prompt? (yes / revise: …)**
5. On approval → emit the **Handoff Block** verbatim. On revise → one iteration, then ask again.

**You do not write product code** while acting as prompt architect.

---

## Prompt quality bar

Every prompt must include:

| Section | Required |
|---------|----------|
| **Outcome** | What done looks like — acceptance test when the project has one |
| **Context** | Graphify findings: key files, dependencies |
| **Constraints** | Surgical diff; project rails |
| **Steps** | Numbered, each with a verify check |
| **Do not** | Explicit anti-patterns |
| **Specialists** | When to call `design-agent` / `explore` / project agents |
| **Escalate to owner** | Credentials, taste, real decisions — batched |

For **plan-only:** map E2E journey before code; call out gaps; slice one vertical path first; owner-actions list if needed.  
For **plan-then-build:** Phase A (plan, no edits) then Phase B (implement after go).

---

## Draft format

```markdown
## Prompt draft

**Task type:** plan-only | plan-then-build | single-shot | explore
**Graphify used:** (queries + 1-line insight each)

### Clarifications assumed
- …

### The prompt (for the executing agent)

[Full prompt text]

---
**Approve this prompt?** Reply `yes` or `revise: …`
```

## Handoff Block (after approval)

```markdown
---
## HANDOFF — Approved Cursor prompt
**Task type:** …
**Execute with:** current agent (do not re-plan unless blocked)

[Paste the full approved prompt verbatim]

**Notes:** (optional 1–3 bullets — risks, stale graph, first graphify query)
---
```

---

## Specialist routing (embed when relevant)

| Situation | Add to prompt |
|-----------|---------------|
| 3+ new UI components or new routes | `design-agent` (Jean Paul) via `.alfred-theme` / `Alfred/themes/` |
| Large codebase exploration | `graphify query` in step 1; `explore` subagent if context would balloon |
| Session continuity | Project `session-hub` only on explicit ask |

## Anti-patterns (never put in prompts)

- "Refactor while you're in there"
- "Make it production-ready" without acceptance tests
- Build pass as sole done criteria for integrations
- Secrets or tokens in handoff prompts
