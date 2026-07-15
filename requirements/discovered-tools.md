# Discovered Tools Catalog

*Tools and MCPs found by Alfred's discovery loop — things you wouldn't think to search for.*
*Updated by the loop; provisioned to Cursor + Claude + Codex on next `Provision-Cursor.ps1` run.*

Read this when you wonder **"what can I ask that I don't know exists?"**

## Format (loop maintains this)

```markdown
### tool-name
- **Category:** MCP | CLI | technique
- **What it does:** one sentence
- **Try asking:** "concrete prompt you'd type in Cursor"
- **Install:** how it lands on your machine (or "already in pack")
- **Status:** shipped | candidate | needs-key
- **Discovered:** YYYY-MM-DD
```

---

## Already in the pack (baseline)

| Tool | Try asking |
|------|------------|
| LeanCTX | "Use lean-ctx map mode on large files — don't dump the whole file" |
| Power BI MCP | "Add a measure for labour cost per FTE in the open Desktop model" |
| Excel (excellm) | "Update the pivot on the **open** wages workbook" |
| Excel-mcp | "Inspect Power Query steps in the **closed** billing template xlsm" |
| duckdb MCP | "Run SQL on last week's CSV export without opening Excel" |
| markitdown MCP | "Convert this PDF brief to markdown so we can work from text" |
| filesystem MCP | "List xlsx files in the finance folder modified this week" |
| context7 MCP | "What's the current DAX syntax for SELECTCOLUMNS in Power BI?" |
| GitHub MCP | "Open a PR for the DLP schema change" |
| pbi CLI | "Add a matrix visual to the open PBIR report" |
| Tavily (Alfred) | "What's the latest Power BI incremental refresh guidance?" |

---

## Discovered by the loop

*Entries below are added by the nightly growth loop.*

<!-- loop appends below this line -->

### parallel-agents-git-worktrees (technique)
- **Category:** technique
- **What it does:** Run multiple Cursor or Claude Code agents simultaneously on the same repo without file conflicts — each agent gets its own branch and directory via git worktrees (the same mechanism Cursor's built-in parallel agents use under the hood).
- **Try asking:** "I need to refactor the auth module AND write billing API tests. These are independent — write me the git worktree setup commands and the starting instruction for each agent."
- **Try asking:** "Task A just finished. Write a handoff file summarising what changed and what Task B needs to know before it starts."
- **Try asking:** "List all worktrees in this repo and give me the commands to remove any that are on branches already merged to main."
- **Try asking:** "I want to tackle these 3 tasks in parallel — tell me which can actually run in parallel (no shared files) and which must be sequential."
- **Install:** No install — git worktrees are built into git. Cursor parallel agents are a Cursor UI feature (background agents panel).
- **Status:** shipped
- **Discovered:** 2026-06-15
- **Skill:** `agent-parallel-worktrees.md`

### context-engineering (technique)
- **Category:** technique
- **What it does:** A structured discipline for deciding what information goes into an agent's context window, in what order, and how to compress and manage it over long sessions — the layer above prompt engineering.
- **Try asking:** "Use LeanCTX map mode on the backend folder, then pick the 3 files relevant to this change — don't open anything else yet"
- **Try asking:** "Summarise what we've confirmed so far in 3 bullets so we can compress the context, then continue with step 4"
- **Try asking:** "Store the TaskKey format convention we just confirmed in LeanCTX memory so I don't have to explain it next session"
- **Try asking:** "Before editing files, outline a numbered plan in chat — don't use a planning MCP"
- **Try asking:** "I'm handing this to Codex — write a clean handoff summary to SCRATCH.md covering what's been decided and what files to touch"
- **Install:** Skill file — available in Cursor/Claude/Codex after next provision
- **Status:** shipped
- **Discovered:** 2026-06-15
- **Skill:** `agent-context-engineering.md`

### KV-cache-aware prompting (technique)
- **Category:** technique
- **What it does:** Structuring your system prompt and conversation so the stable prefix never changes between turns, maximising cache hits and slashing time-to-first-token on frontier models (Claude, GPT-4o, Gemini).
- **Try asking:** "Check whether our system prompt has changed since last session — if so, what changed and is the change stable enough to lock in?"
- **Install:** No install — discipline baked into `agent-context-engineering.md`
- **Status:** shipped (covered in skill)
- **Discovered:** 2026-06-15

### MCP tool description quality audit (technique)
- **Category:** technique
- **What it does:** A six-component rubric (purpose, trigger, return type, param guidance, negative scope, example) for evaluating and improving MCP tool descriptions — poor descriptions cause wrong tool selection and wasted tokens (arXiv 2025 research).
- **Try asking:** "Audit the tool descriptions for all MCPs in our mcp.json — score each on the 6-component rubric and flag any that are missing trigger conditions or examples"
- **Install:** No install — rubric in `agent-context-engineering.md` Section 6
- **Status:** shipped (covered in skill)
- **Discovered:** 2026-06-15

### agent-loop-debugging (technique)
- **Category:** technique
- **What it does:** A six-failure-mode taxonomy (tool misuse, context loss, goal drift, retry loop, cascading failure, sycophantic confirmation) with paste-ready recovery prompts, a pre-flight checklist, and structured output enforcement — for when a Cursor or Claude Code agent goes wrong mid-task.
- **Try asking:** "My agent keeps calling the filesystem tool in a loop and not finishing — how do I stop it?"
- **Try asking:** "Give me a pre-flight checklist prompt I can paste before I start a long Cursor agent session"
- **Try asking:** "My agent said 'done' but the output file is empty — how do I debug that?"
- **Try asking:** "Write me a recovery checkpoint prompt — the agent drifted off from the original goal halfway through"
- **Try asking:** "I want the agent to return a markdown table and nothing else — how do I enforce that?"
- **Install:** Skill file — available in Cursor/Claude/Codex after next provision
- **Status:** shipped
- **Discovered:** 2026-06-16
- **Skill:** `agent-loop-debugging.md`

### agent-self-check (technique)
- **Category:** technique
- **What it does:** Four escalating patterns — inline critique, output contracts, reflection pass, and test-first loop — that make an agent verify its own work before declaring done, catching errors proactively rather than reactively.
- **Try asking:** "Before you write this DAX measure — state what the correct output should be for the IT department filter, then write it and verify."
- **Try asking:** "Review what you just produced as a sceptical colleague who will stake their reputation on it. List 3 things that could still be wrong."
- **Try asking:** "Write a test case FIRST: what input and expected output would expose a bug in this formula? Then write the formula and verify it passes."
- **Try asking:** "You're not done until you've shown me the row count before and after this Power Query merge step, and confirmed no unexpected NULLs appeared."
- **Try asking:** "After completing this report section — flag every number that is an estimate or assumption rather than a hard figure from the source data."
- **Install:** Skill file — available in Cursor/Claude/Codex after next provision
- **Status:** shipped
- **Discovered:** 2026-06-19
- **Skill:** `agent-self-check.md`

### agent-handoff (technique)
- **Category:** technique
- **What it does:** The HANDOFF.md discipline — a living session-end document you regenerate every time you stop work, so the next session (in any tool: Cursor, Claude Code, or Codex) can orient itself in 10 seconds without you re-explaining anything.
- **Try asking:** "We're done for today. Write HANDOFF.md so I can resume this tomorrow in a fresh session — assume no memory of our conversation."
- **Try asking:** "Read HANDOFF.md. Summarise what's done, what's next, and any blocker — then ask before you start."
- **Try asking:** "I'm handing this to Codex to run without me watching. Write a HANDOFF.md Codex can follow autonomously — include the test command it should run after each step."
- **Try asking:** "I'm splitting this into two parallel worktrees — write two separate handoffs, one for the data-pipeline work and one for report-formatting, each completely self-contained."
- **Try asking:** "Check HANDOFF.md — have any of the key files changed since yesterday's session? List what changed and whether it affects the next steps."
- **Install:** Skill file — available in Cursor/Claude/Codex after next provision
- **Status:** shipped
- **Discovered:** 2026-07-03
- **Skill:** `agent-handoff.md`

### ms-365 (MCP) — QUARANTINED
- **Category:** MCP
- **What it does:** Microsoft Graph (SharePoint, OneDrive, Outlook, Calendar, Teams, To-Do) via `@softeria/ms-365-mcp-server`.
- **Status:** **quarantined / not provisioned by default** — login path is TENANT-FORBIDDEN (device-code). Do not install or recommend `--login` under corporate CA.
- **Use instead:** OneDrive sync + `filesystem` MCP; `outlook-calendar` for local calendar; Fabric via browser/SSO `az login` ([AUTH-HARD-RULES.md](../skills/_packs/common/AUTH-HARD-RULES.md)).
- **Discovered:** 2026-07-04
- **Skill:** `sharepoint-graph.md` (quarantine notice)

