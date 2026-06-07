# Alfred Routing & Safety-Gate Audit

**Purpose:** Document how Alfred picks a tool for a request, audit the current keyword
sets in `backend/main.py`, and propose concrete, low-risk improvements so the right
tool is chosen and destructive tools stay behind the safety gate.

**Scope of this skill:** *tool how-to for Alfred itself* — how routing works, where the
gaps are, and how to extend it safely. This does **not** edit finance/domain skills.

**Status:** Audit + improvement proposal. Andrew approves the actual edits to
`backend/main.py`; this file is the spec he can sign off on.

---

## 1. How Alfred routes a request today

When a user types into the chat loop, the request travels through this pipeline
(file: `backend/main.py`):

1. **Provider override** (`detect_provider_override`) — leading directives like
   `use claude` or `use codex` force a provider and skip the brain.
2. **Learning-mode check** (`is_learning_mode_task`) — phrases like "add a rule",
   "teach alfred", "update routing" trigger a discussion-first flow instead of a
   dispatch.
3. **Alfred Brain** (`alfred_brain`) — a single Claude call returns JSON:
   ```
   {category, provider, needs_search, needs_clarification, plan, steps}
   ```
   `category ∈ {GENERAL, SEARCH, CODE, EXECUTE, POWERBI}`,
   `provider ∈ {claude, claude_code}`.
4. **Keyword fallback** — if the brain is unavailable or returns invalid JSON, the
   code falls back to scoring `CODEX_ROUTING_KEYWORDS` vs `CLAUDE_CODE_ROUTING_KEYWORDS`
   and a hard rule for Power BI keywords. `_should_search` decides if Tavily is
   triggered.
5. **Safety gate** — before dispatch, the request is lowered and matched against
   `DANGEROUS_KEYWORDS`. A match forces an explicit `yes` confirmation in the
   terminal; anything else cancels.

### The five keyword sets that drive routing

| Set | Purpose | Effect on dispatch |
|---|---|---|
| `DANGEROUS_KEYWORDS` | Block-and-confirm destructive ops | Requires typed `yes` confirmation |
| `ACTION_KEYWORDS` | Tag a request as actionable | Used for legacy POWERBI dispatch path |
| `LEARNING_MODE_KEYWORDS` | Detect "teach Alfred" requests | Routes to discussion, not dispatch |
| `CODEX_ROUTING_KEYWORDS` | Hint at a coding task | Fallback → category `CODE`, provider `claude_code` |
| `CLAUDE_CODE_ROUTING_KEYWORDS` | Hint at an MCP / file / Office task | Fallback → category `EXECUTE`, provider `claude_code` |
| `SEARCH_TRIGGER_KEYWORDS` | Hint at live-data need | `_should_search` triggers Tavily |

Plus the **Tool Registry** (`TOOL_REGISTRY`) — every entry carries its own `keywords`
list used by `/tools`, the brain prompt, and routing hints.

---

## 2. Audit findings (what's right, what's brittle)

### ✅ What's working well

- The **brain-first, keywords-as-fallback** design is correct: the LLM handles
  ambiguity, and keywords keep Alfred functional when Claude is offline.
- `POWERBI` has a hard short-circuit in the keyword fallback — a real-world request
  like *"check my Power BI model"* never accidentally routes to `CODE`.
- `_should_search` is broad on purpose (question prefixes, `?`, keyword set) — that
  matches the rule that Tavily's free tier has plenty of headroom.
- Provider override (`use claude code …`) gives a clean escape hatch.

### ⚠ Gaps in `DANGEROUS_KEYWORDS` (safety gate is too narrow)

Current list:
```
delete, remove, overwrite, credentials, password,
entire onedrive, all folders, whole workspace
```

It misses verbs that genuinely modify or destroy state, and several destructive
tools are now installed without their verbs being gated:

| Missing keyword | Why it should gate | Risk if not gated |
|---|---|---|
| `drop table`, `truncate` | DuckDB / csvsql destructive SQL | Silent data loss |
| `force push`, `git reset --hard`, `rebase` | Git destructive ops via git/GitHub MCP | Rewrites history |
| `merge pr`, `close pr`, `close issue` | GitHub MCP write ops | Live repo change |
| `rm -rf`, `del /f`, `rmdir` | Shell destruction | Filesystem damage |
| `format`, `wipe` | Disk-level | Catastrophic |
| `kill`, `taskkill`, `stop service` | Process control | Crashes apps |
| `send email`, `send to`, `post to slack` | Outbound side-effects | Comms leak |
| `publish report`, `deploy`, `push to prod` | Power BI / web publishing | Live audience change |
| `move`, `rename file` | Filesystem mutation | Hard to undo |
| `unprotect`, `clear sheet`, `clear range` | Excel MCP destructive | Loses formulas |
| `refresh dataset`, `process model` | Power BI dataset refresh | Long-running, billable |
| `install`, `uninstall`, `pip install`, `npm install` | Environment change | Side-effects on PC |
| `api key`, `token`, `secret` | Adjacent to credentials | Prevent accidental disclosure |

**Proposed:** see `DANGEROUS_KEYWORDS_V2` in section 4.

### ⚠ Routing keyword gaps & overlaps

1. **`document` is overloaded.** It lives in `CLAUDE_CODE_ROUTING_KEYWORDS` for
   Office work, but users type *"write a document explaining…"* meaning a chat reply.
   → **Fix:** remove the bare word `document`; rely on `word document`, `docx`,
   `report`, and the brain. Trust the LLM to disambiguate the bare word.

2. **`report` overlaps GENERAL and EXECUTE.** *"Give me a report on Derrimut"* is
   GENERAL; *"build a report"* is EXECUTE. Brain handles this; the bare keyword
   misroutes when the brain is offline.
   → **Fix:** remove bare `report` from the EXECUTE set; keep `build a report`,
   `create a report`, `word report` as phrases.

3. **Power Query is a Power BI signal, not a generic execute signal.** Currently
   it lives in `CLAUDE_CODE_ROUTING_KEYWORDS`. The fallback already promotes
   Power BI ahead of these sets, so this is correct *only because* of the hard
   short-circuit. Make it explicit.
   → **Fix:** keep the short-circuit, but add `m query`, `merge queries`,
   `unpivot` as POWERBI signals so they don't accidentally score EXECUTE.

4. **GitHub MCP write ops aren't separated from read ops.** *"check my open
   issues"* should route the same as *"close my open issues"*, but only one is
   destructive. Routing is fine (both → claude_code) but the safety gate misses
   the destructive case (see §2.2).

5. **Browser MCP destructive ops are missing.** *"Fill the form and submit"*,
   *"click purchase"*, *"submit the application"* are all destructive via
   Playwright. None are gated.
   → **Fix:** add `submit the`, `click purchase`, `click buy`, `place order` to
   `DANGEROUS_KEYWORDS`.

6. **`open` is too generic.** It appears in the Browser tool's `keywords` list
   (`["browser", "website", "navigate", "scrape", "screenshot", "open", "go to"]`).
   *"Open the wages report"* is Excel/files, not browser. The Tool Registry's
   `open` will mis-bias routing hints.
   → **Fix:** replace bare `open` with `open the website`, `open url`, `open in
   browser`.

7. **`code` is too generic.** Same problem in the Code tool's `keywords`.
   *"Postcode lookup"*, *"code of conduct"* contain `code` but aren't requests.
   → **Fix:** replace bare `code` with `write code`, `code this`, `the code`.

8. **`message`/`email`/`calendar` not present.** Andrew has talked about Outlook
   workflows. There's no keyword that routes those to claude_code.
   → **Fix:** add an `outlook` tool entry (planned) with keywords
   `outlook, send email, draft email, calendar invite, meeting request`.

### ⚠ Brain prompt drift

The brain prompt enumerates categories and provider rules but doesn't enumerate
*the tools available* — it relies on category alone. That's fine for routing, but
the brain can't currently tell the user *which MCP it picked*. The Tool Registry
has the metadata; it just isn't injected into `ALFRED_BRAIN_PROMPT`.

→ **Fix:** at startup, build a one-line-per-tool summary from `TOOL_REGISTRY` and
append it to the brain prompt (only the `name + description + keywords[0..3]` —
keep tokens cheap).

### ⚠ Tool Registry / fallback keyword duplication

`TOOL_REGISTRY[*].keywords` and `CLAUDE_CODE_ROUTING_KEYWORDS` overlap heavily but
drifted independently (e.g. registry has `pivot`, fallback has `pivot table`).
The registry should be the **single source of truth** and the fallback sets
should be *generated* from it at import time.

→ **Fix:** at module load, build `CLAUDE_CODE_ROUTING_KEYWORDS` as the union of
every registry tool whose `provider == "claude_code"` and `category in {EXECUTE,
POWERBI}`, plus a small hand-maintained set of cross-cutting verbs.

---

## 3. Routing decision matrix (target state)

For each request type, this is the tool Alfred *should* pick.

| Request shape | Category | Provider | Tool / MCP | Gate? |
|---|---|---|---|---|
| "what is X" / "explain X" | GENERAL | claude | none | no |
| "latest version of X" | SEARCH | claude | Tavily | no |
| "find news on X" | SEARCH | claude | Tavily | no |
| "refactor this function" | CODE | claude_code | (none) | no |
| "fix the bug in main.py" | CODE | claude_code | filesystem | no (read+write own repo) |
| "delete the temp folder" | EXECUTE | claude_code | filesystem | **yes** |
| "open the wages workbook and add a pivot" | EXECUTE | claude_code | excel MCP | no (additive) |
| "clear sheet 'Working' in wages.xlsx" | EXECUTE | claude_code | excel MCP | **yes** |
| "scrape the products table from example.com" | EXECUTE | claude_code | playwright MCP | no |
| "submit the form on example.com" | EXECUTE | claude_code | playwright MCP | **yes** |
| "open a PR with this branch" | EXECUTE | claude_code | github MCP | no (review step) |
| "merge PR #42" | EXECUTE | claude_code | github MCP | **yes** |
| "check the DAX measure for Derrimut" | POWERBI | claude_code | powerbi MCP | no |
| "refresh the dataset" | POWERBI | claude_code | powerbi MCP | **yes** |
| "publish the Power BI report" | POWERBI | claude_code | powerbi MCP | **yes** |
| "send the daily email" | EXECUTE | claude_code | outlook (planned) | **yes** |
| "draft an email about Q3" | EXECUTE | claude_code | outlook (planned) | no (drafts only) |

The pattern: **read + draft = no gate; send/delete/overwrite/publish/refresh = gate.**

---

## 4. Concrete proposed change to `backend/main.py`

This is the diff Andrew can apply when he's ready. It is **documented only** here;
this skill does not modify `backend/main.py`.

### 4.1 Expand `DANGEROUS_KEYWORDS`

```python
DANGEROUS_KEYWORDS = [
    # File / disk
    "delete", "remove", "overwrite", "rm -rf", "del /f", "rmdir",
    "format drive", "wipe", "move file", "rename file",
    "entire onedrive", "all folders", "whole workspace",
    # Credentials & secrets
    "credentials", "password", "api key", "token", "secret", ".env",
    # SQL / data
    "drop table", "drop database", "truncate table", "delete from",
    # Git / GitHub destructive
    "force push", "git reset --hard", "rebase onto", "delete branch",
    "merge pr", "close pr", "close issue", "force-merge",
    # Process / system
    "kill process", "taskkill", "stop service", "shutdown",
    # Outbound side-effects
    "send email", "send to slack", "post to slack", "post to teams",
    # Browser destructive
    "submit the form", "click purchase", "click buy", "place order",
    "complete checkout", "confirm payment",
    # Excel destructive
    "clear sheet", "clear range", "unprotect", "delete sheet",
    # Power BI destructive / billable
    "refresh dataset", "process model", "publish report", "deploy report",
    # Environment changes
    "pip install", "pip uninstall", "npm install -g", "uninstall",
]
```

### 4.2 Tighten the fallback sets

```python
# Remove from CLAUDE_CODE_ROUTING_KEYWORDS:
#   "document", "report"  (too generic — brain handles these)
# Add as Power BI signals (short-circuit already catches them, make explicit):
#   "m query", "merge queries", "unpivot"
# Add outbound / Outlook signals:
#   "outlook", "draft email", "calendar invite", "meeting request"
```

```python
# In TOOL_REGISTRY["browser"]["keywords"]:
#   replace bare "open" with "open the website", "open url", "open in browser"
# In TOOL_REGISTRY["code"]["keywords"]:
#   replace bare "code" with "write code", "code this", "the code"
```

### 4.3 Generate fallback from registry (single source of truth)

After `TOOL_REGISTRY` is defined, append:

```python
def _derive_routing_keywords() -> tuple[set[str], set[str]]:
    """Build CLAUDE_CODE_ROUTING_KEYWORDS / CODEX_ROUTING_KEYWORDS from the registry.
    Hand-maintained verbs are unioned in below."""
    claude_code, codex = set(), set()
    for tool in TOOL_REGISTRY.values():
        if tool["provider"] != "claude_code":
            continue
        target = codex if tool["category"] == "CODE" else claude_code
        target.update(tool.get("keywords", []))
    return claude_code, codex
```

Then merge the derived sets with the existing hand-maintained sets at module load.
This guarantees that adding a tool via `register_tool(...)` immediately influences
the keyword fallback — no second place to update.

### 4.4 Inject Tool Registry into the brain prompt

```python
def _brain_tool_summary() -> str:
    lines = []
    for t in TOOL_REGISTRY.values():
        kws = ", ".join(t.get("keywords", [])[:3])
        lines.append(f"- {t['name']}: {t['description']} (signals: {kws})")
    return "\n".join(lines)

# Build ALFRED_BRAIN_PROMPT lazily so it always reflects the live registry:
def _alfred_brain_prompt() -> str:
    return ALFRED_BRAIN_PROMPT_TEMPLATE + "\n\nAvailable tools:\n" + _brain_tool_summary()
```

---

## 5. How to add a new tool without breaking routing

This is the procedure for *any* new MCP server or CLI Alfred grows into.

1. **Document the tool** in `requirements/mcp-tools.md` (MCP) or
   `requirements/alfred-tools.json` (CLI/PyPI). Mark `destructive: true|false`
   and `trust: official|community`. **Never** auto-install — Andrew approves.
2. **Add a Tool Registry entry** via `register_tool(...)` with:
   - `keywords`: 3–6 *specific* trigger phrases (not generic words like `open`,
     `code`, `document`).
   - `examples`: 2–3 realistic user phrasings.
3. **If destructive, add gating keywords** to `DANGEROUS_KEYWORDS`. Use *verb
   phrases* (e.g. `merge pr`, not just `merge`).
4. **Smoke-test routing**: in `/menu` → "dispatch rules", confirm the new
   keywords show under the right category and no overlap is created.
5. **Update this skill** with the routing matrix row for the new tool.

---

## 6. Quick reference — what each keyword set is for

```text
DANGEROUS_KEYWORDS         → forces typed-yes confirmation before dispatch
ACTION_KEYWORDS            → legacy POWERBI dispatch trigger
LEARNING_MODE_KEYWORDS     → "teach Alfred" → discussion mode, no dispatch
CODEX_ROUTING_KEYWORDS     → fallback signal for CODE category (provider claude_code)
CLAUDE_CODE_ROUTING_KEYWORDS → fallback signal for EXECUTE category
SEARCH_TRIGGER_KEYWORDS    → fallback signal that Tavily should run
TOOL_REGISTRY[*].keywords  → per-tool signals; should drive the two fallback sets
```

---

## 7. Open questions for Andrew

- **Outlook MCP / CLI** — do you want a planned entry for Outlook draft + send?
  If yes, the safety gate must include `send email`, `send mail`, `send to`.
- **Confirmation level for read-only browser/playwright actions** — currently
  nothing gates a scrape. Probably fine, but worth confirming for paywalled or
  authenticated sites.
- **Per-tool confirmation policy** — should `refresh dataset` use a softer
  confirmation than `delete file`? Today it's binary. A "destructive but
  recoverable" tier could reduce friction.

---

## 8. What this skill does *not* do

- It does **not** modify `backend/main.py`. All changes are proposals; Andrew
  applies them.
- It does **not** install any tool. New MCPs/CLIs are documented in
  `requirements/` and stay `planned` until Andrew approves.
- It does **not** edit any finance/domain skill (cash flow, labour, Excel models,
  Power BI, data-*). Those belong to Andrew.

---

**Companion files:**
- `requirements/mcp-tools.md` — MCP server manifest (installed + planned)
- `requirements/alfred-tools.json` — full tool manifest (Python + npm + MCP)
- `skills/github.md`, `skills/browser-automation.md`, `skills/office-mastery.md` —
  per-tool how-tos that should match the routing matrix above
