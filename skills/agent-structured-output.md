# Agent Structured Output — Reliable, Machine-Readable Results

Use this skill when you need an agent to return **data in a predictable, parseable shape** rather
than free prose — tables you can copy into Excel, JSON another agent can consume, or lists with
consistent fields. Covers schema design, enforcement techniques, validation loops, and real
prompts for finance workflows.

*Distinct from:*
- *`agent-self-check.md` — self-check is about logical correctness; this is about data shape*
- *`agent-output-evaluation.md` — the critic pattern reviews quality; this enforces format before
  the output even leaves the agent*
- *`agent-spec-driven.md` — the spec defines what to build; output contracts here define the exact
  envelope the result must fit into*

*Sources: Anthropic Structured Outputs docs (Claude API, 2026); collinwilkins.com "LLM Structured
Outputs: Schema Validation for Real Pipelines" (2026); kenhuangus.substack.com "Chapter 15:
Structured Output" (2026); Reddit r/ClaudeAI structured outputs launch thread (2026); Peace of Code
"Claude Certified Architect Ep 16: Structured Output & JSON Schema" (May 2026)*

---

## Why free-form output breaks pipelines

When you ask "summarise the cost breakdown" you get a paragraph. When you need that cost breakdown
to feed into a Power BI data model, or a DuckDB query, or a second agent's context, a paragraph
is unusable. You have to re-read it, re-parse it, and hope the agent used the same category names
it used last month.

Structured output fixes this by **constraining the response to a declared shape** — not just
"JSON please" (which the model frequently ignores) but a typed schema the agent must conform to.

Two costs make this worth the setup effort:
1. **Parsing failure** — free-form output breaks downstream tools silently, often hours after the
   agent ran
2. **Schema drift** — the same prompt produces different field names week to week
   ("FTE Count" vs "headcount" vs "fte_count"), breaking every formula that references them

---

## The four enforcement levels

Choose the level that matches the downstream need. Don't over-engineer.

| Level | Use when | Reliability | Overhead |
|-------|----------|-------------|----------|
| **1 — Format hint** | One-off, you'll copy-paste manually | ~70% | Zero |
| **2 — Output contract** | Repeated task, you'll eyeball the result | ~85% | Minimal |
| **3 — Schema declaration** | Result feeds another tool or agent | ~97% | Low |
| **4 — Tool-call enforcement** | Production pipeline, zero tolerance for drift | 99%+ | Moderate |

---

## Level 1 — Format hint (bare minimum)

Append a format instruction to any prompt. Better than nothing; don't rely on it for pipelines.

**Prompt pattern:**
```
Return ONLY a markdown table with these exact columns:
| Department | Headcount | Monthly Cost | Cost per FTE |

No introductory text. No footnotes. No commentary. Table only.
```

**When it fails:** Claude adds "Here's the table:" or drops a column when the data is sparse.
That's expected — format hints are advisory. Upgrade to Level 2 if you copy-paste this weekly.

---

## Level 2 — Output contract

State the exact fields, types, and constraints before asking the agent to produce anything.
Then tell it to self-check the contract before it responds.

**Prompt pattern:**
```
OUTPUT CONTRACT — read this before you start:
- Format: JSON array
- Each item has exactly 4 keys: "department" (string), "headcount" (integer),
  "monthly_cost_aud" (number, 2 decimal places), "cost_per_fte" (number, 2 decimal places)
- No extra keys. No null values (use 0 if unknown).
- The array must have one item per department in the source data.

Before you respond: check your output against this contract. If any item is missing a field
or has the wrong type, fix it before sending.

Now extract the department cost breakdown from the following report:
[paste report text or use markitdown MCP to convert PDF first]
```

**Why this works better than a format hint:** The agent reads the contract before it starts
generating, not after — so it structures its working towards the schema rather than retrofitting.

---

## Level 3 — Schema declaration (JSON Schema)

For tasks you run repeatedly (weekly cost extraction, monthly variance report, PDF invoice parsing),
write a formal JSON Schema once and reuse it. Paste the schema into the system prompt or a
dedicated `OUTPUT_SCHEMA.json` file the agent reads.

### Writing the schema

Keep schemas **flat and simple** — nested objects multiply failure modes.

**Example: department cost row**
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["department", "headcount", "monthly_cost_aud", "cost_per_fte"],
    "additionalProperties": false,
    "properties": {
      "department": { "type": "string" },
      "headcount":  { "type": "integer", "minimum": 0 },
      "monthly_cost_aud": { "type": "number", "minimum": 0 },
      "cost_per_fte": { "type": "number", "minimum": 0 }
    }
  }
}
```

**Prompt pattern with schema:**
```
Return a JSON array that conforms exactly to the schema below.
No markdown fences, no commentary — raw JSON only.

SCHEMA:
[paste schema]

SOURCE DATA:
[paste or reference file]
```

### Schema design rules (from 2026 production experience)

1. **Use `additionalProperties: false`** — prevents the model inventing new fields when uncertain
2. **Require every field** — optional fields create drift (absent this week, present next week)
3. **Use `enum` for categories** — `"type": "string", "enum": ["labour", "non-labour", "capex"]`
   stops "Labour" vs "labour" vs "Labour costs" divergence
4. **Avoid deep nesting** — one level of array-of-objects is the sweet spot; two levels breaks often
5. **Integer vs number** — use `integer` for counts, `number` for currency; agents drift otherwise

---

## Level 4 — Tool-call enforcement (most reliable)

Claude Code's implementation detail (confirmed in production 2026): when you pass a JSON Schema
as the expected output shape, the SDK wraps it as a **synthetic tool definition** — the model
"calls" the tool with structured arguments, which forces schema conformity at the inference level
rather than relying on text generation to produce valid JSON.

You don't need to implement this yourself in Cursor — but you can exploit the same mechanism by
**describing the output as a tool call** in your prompt:

**Prompt pattern:**
```
You have access to one tool: `save_result`. It takes exactly one argument:

save_result({
  "rows": [
    {
      "department": string,
      "headcount": integer,
      "monthly_cost_aud": number,
      "cost_per_fte": number
    }
  ]
})

Call save_result once with the extracted data. Do not respond in prose. Call the tool.
```

This prompt pattern triggers the model's tool-use pathway rather than its text-generation pathway.
Tool-use outputs are dramatically more consistent in structure because the model is trained to
fill typed arguments, not generate arbitrary JSON strings.

**Use this for:** nightly automation, data pipelines, extractions that feed formulas or models.

---

## Validation + retry pattern

Even Level 3–4 outputs occasionally fail (truncated JSON, wrong numeric type). The fix is a
lightweight validation loop — catch the failure and ask for a targeted correction.

**Retry prompt (paste if output fails validation):**
```
Your previous response failed validation:
- Error: [paste the specific error, e.g. "missing field 'cost_per_fte' in item 3"]

Produce the corrected JSON only. Do not explain the error. Do not repeat the valid rows —
only output the fixed item(s) so I can patch the array:
[paste the failing item]
```

**Retry budget guideline:** Allow 2 retries. If it fails on the third attempt, the schema or the
source data is ambiguous — ask the agent to explain what it found before you retry.

### What causes validation failures (and how to prevent them)

| Failure | Cause | Prevention |
|---------|-------|------------|
| Missing field | Source data had no value | Add `"default": 0` guidance in schema description |
| Wrong numeric type | Currency shown as string ("$12,450") | Add note: "strip currency symbols, return raw number" |
| Extra keys | Agent added "notes" to explain uncertainty | `additionalProperties: false` |
| Truncated array | Output hit context limit mid-array | Use Level 4 tool call; or split source data |
| Float precision | 12.3000000000001 | Add: "round all numbers to 2 decimal places" |

---

## Finance-specific recipes

### Recipe A — Extract a cost table from a PDF

```
1. Use the markitdown MCP to convert the PDF to markdown text.
2. Then use this prompt:

   "The markdown below is a converted payroll/cost report. Extract all department rows into
   a JSON array with exactly these fields: department (string), period (string, format YYYY-MM),
   headcount (integer), total_cost (number, AUD, strip $ and commas).
   Return raw JSON only — no fences, no commentary."

3. Paste the result directly into a DuckDB MCP query:
   SELECT * FROM read_json_auto('[paste JSON or save to file first]')
```

### Recipe B — Consistent weekly variance extraction

For any prompt you run more than once, keep a `SCHEMA_variance_row.json` in your project folder
and reference it:

```
Read SCHEMA_variance_row.json from the project folder.
Extract all variance rows from this week's report and return a JSON array conforming to that schema.
If any field is ambiguous, use null — do not guess.
```

This stops schema drift across weeks. The file is the single source of truth for field names.

### Recipe C — Markdown table for Excel paste

When you need a table to paste into Excel (not feed a pipeline), Level 2 + format hint is enough:

```
Return a markdown table with exactly these headers in this order:
| Month | Revenue | Cost | Labour % | Variance |

Rules:
- Months in format "Jan-2026" (not "January 2026" or "01/2026")
- All currency in AUD as plain numbers (no $ sign, no commas)
- Labour % as a decimal (0.42 not 42%)
- One row per month, ordered oldest to newest
- No totals row
- No footnotes

Table only. No other text.
```

---

## Multi-agent output contracts

When one agent's output is another agent's input, structured output is not optional — it is the
interface definition between agents.

**The handoff contract pattern:**
```
AGENT 1 PROMPT:
"Extract the cost data and save it to HANDOFF_data.json using this schema:
[paste schema]. Do not start the analysis — just extract and save."

AGENT 2 PROMPT:
"Read HANDOFF_data.json (schema: [paste schema]). Each row is guaranteed to have
[fields]. Run the variance analysis on this data."
```

Why this matters: if Agent 1 produces "cost_AUD" and Agent 2 expects "monthly_cost_aud", the
second agent either fails silently or hallucinates column values. The contract makes the field
names a shared agreement rather than a lucky guess.

See `agent-handoff.md` for full HANDOFF.md discipline. See `agent-workflow-orchestration.md` for
how to chain agents in longer pipelines.

---

## Checklist — before you run a structured extraction

```
[ ] Do I have a schema, or at least an explicit field list?
[ ] Have I specified the numeric format? (AUD, plain number, 2dp, no commas)
[ ] Have I told the agent what to do with missing values? (null vs 0 vs skip row)
[ ] Is the output going to a pipeline? If yes, use Level 3 or 4.
[ ] Do I need this to work the same way next week? If yes, save the schema to a file.
```

---

## Try asking

```
Use the markitdown MCP to convert this PDF invoice to text, then extract all line items
into a JSON array with fields: description, quantity, unit_price_aud, line_total_aud.
Return raw JSON only.
```

```
I run this extraction every Monday. Write me a reusable output schema (JSON Schema format)
for a department cost row with headcount, monthly cost, and cost per FTE — I'll save it
as SCHEMA_dept_cost.json and reference it in every future prompt.
```

```
Your last JSON output failed — the 'headcount' field was a string in row 4 instead of an integer.
Fix row 4 only and return the corrected item as JSON.
```

```
Return this analysis as a markdown table I can paste directly into Excel — exactly these columns
in this order: Month, Revenue, Cost, Variance, Variance %. All numbers plain (no $ or % signs).
One row per month, ordered Jan to Jun.
```

```
I'm chaining two agents: the first extracts cost data, the second runs variance analysis.
Write the output contract for the first agent — the exact JSON schema the second agent
will expect — so they share a field-name agreement and don't break each other.
```
