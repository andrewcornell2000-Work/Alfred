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
| LeanCTX | "Read `backend/main.py` in map mode — don't dump the whole file" |
| Power BI MCP | "Add a measure for labour cost per FTE in the open Desktop model" |
| Excel MCP | "Update the pivot on the open wages workbook" |
| duckdb MCP | "Run SQL on last week's CSV export without opening Excel" |
| sqlite MCP | "Create a table from this wages CSV and show top 10 sites by hours" |
| markitdown MCP | "Convert this PDF brief to markdown so we can work from text" |
| filesystem MCP | "List xlsx files in the finance folder modified this week" |
| GitHub MCP | "Open a PR for the DLP schema change" |
| pbi CLI | "Add a matrix visual to the open PBIR report" |
| Tavily (Alfred) | "What's the latest Power BI incremental refresh guidance?" |

---

## Discovered by the loop

*Entries below are added by the nightly growth loop.*

<!-- loop appends below this line -->

### context-engineering (technique)
- **Category:** technique
- **What it does:** A structured discipline for deciding what information goes into an agent's context window, in what order, and how to compress and manage it over long sessions — the layer above prompt engineering.
- **Try asking:** "Use LeanCTX map mode on the backend folder, then pick the 3 files relevant to this change — don't open anything else yet"
- **Try asking:** "Summarise what we've confirmed so far in 3 bullets so we can compress the context, then continue with step 4"
- **Try asking:** "Store the TaskKey format convention we just confirmed in the memory MCP so I don't have to explain it next session"
- **Try asking:** "Run sequential-thinking on this refactor before touching any file — give me a numbered plan to approve"
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
