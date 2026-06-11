"""
Alfred Autonomous Growth Loop
Runs in GitHub Actions daily at noon AEST.
Researches, builds, and writes improvements back to the repo.
"""

import anthropic
import os
import sys
import json
import shlex
import subprocess
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_utils import OWNER_EMAIL, send_alfred_email

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")

# Set once an email actually goes out, so the end-of-run fallback never
# double-sends when Alfred already emailed via the send_email tool.
_email_sent = False


def send_update_email(subject, body):
    """Send Alfred's daily loop summary via Resend API."""
    global _email_sent
    if not subject.lower().startswith("alfred daily"):
        subject = f"Alfred daily — {subject}"
    if send_alfred_email(subject, body):
        _email_sent = True

# Tools Alfred can use inside GitHub Actions
TOOLS = [
    {
        "name": "read_file",
        "description": "Read any file in the Alfred repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to repo root"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or update a file in the repository. Changes are committed automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to repo root"},
                "content": {"type": "string", "description": "Full file content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: .)"}
            }
        }
    },
    {
        "name": "web_search",
        "description": "Search the web via Tavily. Use for researching AI developments, new tools, techniques.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_url",
        "description": "Fetch and read a web page or raw file URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a read-only git command. Only git log, rev-list, status, diff, and show are allowed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Read-only git command, e.g. 'git log --oneline -5'"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "send_email",
        "description": "Send the DAILY update email to Andrew (andrewcornell2000@gmail.com) at the END of your loop. Subject is prefixed 'Alfred daily —' automatically. Use plain-English DOT POINTS, not paragraphs — Andrew wants a scannable list of exactly what you added and how it works.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Short subject after 'Alfred daily —', e.g. 'new SharePoint MCP candidate + Try asking prompts'"},
                "body": {"type": "string", "description": "Email in plain English using dot points (use '- ' for each bullet, no other markdown). Structure:\n\nOne short opening line of context.\n\nWhat I added:\n- one bullet per concrete thing you added or changed (name it plainly)\n\nHow it works:\n- 2-4 bullets explaining, in everyday language, what it does and how Andrew/the team would actually use it\n\nWhat's next:\n- 1-2 bullets on what you'll tackle next time\n\nSign off as Alfred. Keep each bullet to one clear sentence. No code blocks, no file paths, no jargon — but DO be specific about what the thing actually does."}
            },
            "required": ["subject", "body"]
        }
    }
]


def handle_tool(name, inp):
    try:
        if name == "read_file":
            p = inp["path"]
            if not os.path.exists(p):
                return f"File not found: {p}"
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if len(content) > 4000:
                content = content[:4000] + "\n...[truncated]"
            return content

        elif name == "write_file":
            p = inp["path"]
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(inp["content"])
            return f"Written: {p} ({len(inp['content'])} chars)"

        elif name == "list_files":
            p = inp.get("path", ".")
            if not os.path.exists(p):
                return f"Path not found: {p}"
            items = os.listdir(p)
            return "\n".join(sorted(items))

        elif name == "web_search":
            if not TAVILY_KEY:
                return "TAVILY_API_KEY not configured"
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_KEY, "query": inp["query"], "max_results": 4},
                timeout=30
            )
            if r.ok:
                results = r.json().get("results", [])
                return "\n\n---\n\n".join([
                    f"**{res['title']}**\n{res['url']}\n{res.get('content', '')[:600]}"
                    for res in results
                ])
            return f"Search error {r.status_code}: {r.text[:200]}"

        elif name == "fetch_url":
            r = requests.get(inp["url"], timeout=20, headers={"User-Agent": "Alfred/1.0"})
            return r.text[:3000]

        elif name == "run_command":
            allowed_git = {"log", "rev-list", "status", "diff", "show"}
            try:
                parts = shlex.split(inp["command"].strip())
            except ValueError as e:
                return f"Command parse error: {e}"
            if len(parts) < 2 or parts[0] != "git" or parts[1] not in allowed_git:
                return (
                    "Rejected — only read-only git commands are allowed: "
                    + ", ".join(sorted(allowed_git))
                )
            result = subprocess.run(
                parts, capture_output=True, text=True, timeout=60, shell=False
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "unknown error").strip()
                return f"git failed (exit {result.returncode}): {err[:500]}"
            out = result.stdout
            if result.stderr:
                out += f"\n[stderr]: {result.stderr[:500]}"
            return out or "(no output)"

        elif name == "send_email":
            send_update_email(inp["subject"], inp["body"])
            return f"Email sent to {OWNER_EMAIL}"

    except Exception as e:
        return f"Tool error: {e}"

    return f"Unknown tool: {name}"


def api_call_with_retry(messages, system):
    """Call Claude API with exponential backoff on rate limits."""
    import time
    for attempt in range(5):
        try:
            return client.messages.create(
                # Opus 4.7: runs once daily (noon AEST), so we use the most
                # capable model for best judgment on tool vetting + precise
                # manifest edits, rather than a cheap high-frequency split.
                model="claude-sonnet-4-6",
                # Was 2000 — too low. A full skill file is ~1.5-2k tokens of
                # write_file JSON plus reasoning, so writes hit the cap and got
                # truncated mid-tool-call, producing empty/partial files. 8000
                # gives ample headroom for a complete file in one turn.
                max_tokens=8000,
                system=system,
                tools=TOOLS,
                messages=messages
            )
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"Rate limit hit — waiting {wait}s before retry {attempt + 1}/5...")
            time.sleep(wait)
        except anthropic.APIError as e:
            print(f"API error: {e}")
            raise
    raise RuntimeError("Max retries exceeded on rate limit")


def read_file_safe(path, limit=1500):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return content[:limit] if len(content) > limit else content
    except Exception:
        return f"(not found: {path})"


def run():
    import time

    # Pre-load critical context so Alfred starts working immediately
    git_log = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True).stdout
    iteration_num = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip()
    active_projects = read_file_safe("memory/active-projects.md")
    recent_log = read_file_safe("memory/learning-log.md", limit=800)
    discovered = read_file_safe("requirements/discovered-tools.md", limit=2000)
    mcp_catalog = read_file_safe("cursor/mcp.json", limit=2000)
    skills_list = ", ".join(sorted(os.listdir("skills"))) if os.path.exists("skills") else "none"

    # Alfred Pack growth loop: DISCOVER tools Andrew wouldn't find himself.
    # Ship to manifests so Provision-Cursor.ps1 wires Cursor + Claude + Codex globally.
    # NEVER edit finance/domain skills (cash-flow*, labour*, data-*, excel-financial*, powerbi-*, powerquery-*).
    DOMAIN_ROTATION = [
        "DISCOVER MCP (finance/office): run 2-3 web searches for MCP servers Andrew wouldn't think to "
        "look for (SharePoint, PDF tables, scheduling, email, parquet, Azure, clipboard, OCR). "
        "Read cursor/mcp.json below — do NOT duplicate. If installable (npx/uvx, no admin): ADD to "
        "cursor/mcp.json + skill + mcp-tools.md. Else: append candidate to requirements/discovered-tools.md "
        "with 3 'Try asking:' prompts. Update memory/discoveries.md.",
        "DISCOVER CLI (day-to-day): search for CLIs that help finance/office work (CSV, xlsx, pdf, "
        "markdown, calendar, api-json). Compare requirements/alfred-tools.json. If shippable: add to "
        "npm/python manifest + alfred-tools.json + skill with 'Try asking:'. Else: discovered-tools.md candidate.",
        "DISCOVER technique: search 'context engineering', 'MCP server', 'agent skill' patterns Andrew "
        "doesn't know. Write or improve an agent-* skill with actionable checklist + 'Try asking:' examples. "
        "Append to discovered-tools.md if it's a workflow not a tool.",
        "SHIP discovered candidate: read requirements/discovered-tools.md for status=candidate entries. "
        "Pick the best one, verify it still exists, and either promote to cursor/mcp.json + manifests OR "
        "write a complete how-to skill. Mark status shipped in discovered-tools.md.",
        "MCP HOW-TO: deepen one pack MCP skill — must add a real 'Try asking:' block Andrew can paste into Cursor.",
        "CLI HOW-TO: deepen one pack CLI skill (gh, jq, pandoc, az, pbi, vd, lean-ctx) with day-to-day examples.",
        "CATALOG refresh: read discovered-tools.md + cursor/mcp.json; fix stale entries, merge duplicates, "
        "add missing 'Try asking:' lines to shipped tools. No new tools this run — curation only.",
        "CONSOLIDATE: merge two overlapping tool skills; update discovered-tools.md to point at the survivor.",
    ]
    focus = DOMAIN_ROTATION[int(iteration_num) % len(DOMAIN_ROTATION)] if iteration_num.isdigit() else DOMAIN_ROTATION[0]

    system = (
        "You are Alfred Pack's discovery engine — GitHub Actions (ubuntu-latest). "
        "Andrew cannot find new MCPs and tools himself. YOU search the frontier, evaluate, and ship "
        "catalog entries + skills so Provision-Cursor.ps1 wires them into Cursor, Claude Code, and Codex. "
        "Every deliverable needs 'Try asking:' example prompts Andrew can paste into Cursor. "
        "Never edit finance/domain skills (cash-flow*, labour*, data-*, excel-financial*, powerbi-*, powerquery-*). "
        "Tools: read_file, write_file, list_files, web_search, fetch_url, run_command, send_email. "
        "DISCOVER missions: at least 2 web_search calls before write_file. "
        "Every run MUST call write_file at least once. Analysis-only runs are failures."
    )

    messages = [
        {
            "role": "user",
            "content": f"""You are Alfred. Iteration #{iteration_num}. Running in GitHub Actions.

=== YOUR CURRENT STATE ===
Recent commits:
{git_log}

Active projects:
{active_projects}

Recent learning log (last entry):
{recent_log}

Existing skills: {skills_list}

=== MCP CATALOG (do not duplicate) ===
{mcp_catalog}

=== DISCOVERED TOOLS CATALOG ===
{discovered}

=== YOUR MISSION THIS ITERATION ===
{focus}

Steps:
1. Read the existing skills list above. If your mission touches a topic that already has a
   skill, IMPROVE or MERGE that file — do NOT create a near-duplicate with a slightly different name.
2. Do 1-2 targeted web searches if the topic needs current facts.
3. Write a COMPLETE file with write_file. Then read_file it back to confirm it is non-empty and
   genuinely useful before you move on.
4. Update memory/learning-log.md with what you did.
5. Call send_email with your DAILY update for Andrew (weekly digest is separate — this is today's
   run only). Use plain-English DOT POINTS (not paragraphs): a "What I added" list, a "How it works"
   list (everyday language), 2-3 "Try asking:" prompts he can paste into Cursor, and "What's next".
   Be specific. No file paths or jargon. Only claim you built something if the file is real and complete.

This is your ONE run today. Don't rush and don't pad — go deep and ship a single excellent,
complete deliverable. Depth and correctness matter far more than covering extra ground.

QUALITY BAR:
- PRIMARY VALUE: Andrew discovers tools he didn't know existed. Every email must list 'Try asking:' prompts.
- DISCOVER missions: minimum 2 web_search calls; cite what you searched in learning-log.md.
- SCOPE: pack catalog only — no finance/domain skills.
- Append shipped tools to requirements/discovered-tools.md (status: shipped).
- Candidates go to discovered-tools.md (status: candidate) with install notes.
- NEVER leave empty/stub files.
- Skills → skills/ | MCP → cursor/mcp.json | CLI → requirements/*.txt + alfred-tools.json

ALFRED PACK (global provision — Andrew's real workflow is Cursor):
- cursor/mcp.json is the portable MCP template. Provision-Tools.ps1 (Provision-Cursor.ps1) registers
  servers into ~/.cursor/mcp.json, `claude mcp add --scope user`, AND `codex mcp add`.
- Skills sync to ~/.cursor/skills, ~/.claude/skills, and ~/.codex/skills on provision.
- Say "available after next provision" — the cloud loop cannot install on Andrew's machine.

MCP / CLI rules:
- MCP: add to cursor/mcp.json with _requiresCommand guards; how-to skill required.
- CLI: add to requirements manifests; setup.ps1 picks up python/npm lists automatically.
- NEVER write API keys — use "${env:VAR}" + "_requires".
- Destructive tools: note in skill + DANGEROUS_KEYWORDS gate in backend/main.py.
- Do NOT duplicate existing catalog entries.

Start immediately. Pick your mission and begin.
"""
        }
    ]

    print("=== Alfred Growth Loop starting ===\n")

    files_written = 0

    for iteration in range(15):
        response = api_call_with_retry(messages, system)

        if response.stop_reason == "max_tokens":
            print("[WARN] Response hit max_tokens — output truncated. "
                  "A file write this turn may be incomplete; consider raising max_tokens.")

        tool_uses = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # Do not allow a "research-only" run — must ship at least one write_file.
        if (response.stop_reason == "end_turn" or not tool_uses) and files_written == 0:
            print("[QualityGate] Model tried to finish without writing — nudging to ship a file")
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": (
                    "STOP — you have not called write_file yet. This run is FAILED until you "
                    "write at least one complete, useful file (skill, manifest entry, or "
                    "memory/learning-log update). Do NOT end with analysis only. "
                    "Call write_file now for your deliverable, then read_file to verify it."
                )
            })
            time.sleep(1)
            continue

        if response.stop_reason == "end_turn" or not tool_uses:
            print(f"\n=== Alfred loop complete ({files_written} file(s) written) ===")
            break

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for t in tool_uses:
            print(f"\n[{t.name}] {json.dumps(t.input)[:120]}")
            result = handle_tool(t.name, t.input)
            result_str = str(result)
            print(f"  → {result_str[:200]}")
            if t.name == "write_file" and result_str.startswith("Written:"):
                files_written += 1
            results.append({
                "type": "tool_result",
                "tool_use_id": t.id,
                "content": result_str
            })

        messages.append({"role": "user", "content": results})

        # Prune conversation to keep costs controlled
        if len(messages) > 16:
            messages = messages[:1] + messages[-14:]

        time.sleep(1)

    # --- Quality gate ---------------------------------------------------
    # Look only at what THIS run changed (working tree vs HEAD + untracked),
    # delete any empty/stub markdown the model failed to fill, and report
    # honestly. This is what stops empty files and inflated "success" emails.
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    ).stdout

    changed = [line[3:].strip() for line in status.splitlines() if line[3:].strip()]
    substantive = []
    for p in changed:
        if p.startswith(".github"):
            continue
        if p.endswith(".md") and os.path.exists(p) and os.path.getsize(p) < 50:
            os.remove(p)  # workflow allowlist will stage the deletion on next commit
            print(f"[QualityGate] Removed empty/stub file: {p}")
            continue
        substantive.append(p)

    if _email_sent:
        print("[Email] Alfred already emailed this run — skipping fallback")
    elif substantive:
        files_summary = "\n".join(f"  - {f}" for f in substantive)
        send_update_email(
            subject=datetime.utcnow().strftime("%d %b %Y — shipped updates"),
            body=(
                f"Hi Andrew,\n\n"
                f"Daily discovery loop finished. Here's what I got done today:\n\n"
                f"Files I built or updated:\n{files_summary}\n\n"
                f"Pull latest or re-run Alfred-Install.exe to pick up changes.\n"
                f"https://github.com/andrewcornell2000-Work/Alfred\n\n"
                f"Next daily run: tomorrow at noon AEST. Weekly digest: Monday.\n\n"
                f"— Alfred"
            )
        )
    else:
        print("[QualityGate] No substantive output this run — sending honest note")
        send_update_email(
            subject="quiet run, nothing worth shipping",
            body=(
                "Hi Andrew,\n\n"
                "I ran today's discovery loop but didn't produce anything solid enough to keep, "
                "so I'm not padding the repo with busywork. Just a heads-up that I'm alive — "
                "I'll try again tomorrow at noon. Your weekly digest still arrives Monday.\n\n"
                "— Alfred"
            )
        )


if __name__ == "__main__":
    run()
