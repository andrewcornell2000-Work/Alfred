"""
Alfred Autonomous Growth Loop
Runs in GitHub Actions every 4 hours.
Researches, builds, and writes improvements back to the repo.
"""

import anthropic
import os
import json
import subprocess
import requests
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
OWNER_EMAIL = "andrewcornell2000@gmail.com"

# Set once an email actually goes out, so the end-of-run fallback never
# double-sends when Alfred already emailed via the send_email tool.
_email_sent = False


def send_update_email(subject, body):
    """Send Alfred's loop summary via Resend API."""
    global _email_sent
    print(f"[Email] RESEND_API_KEY present: {bool(RESEND_API_KEY)}")
    if not RESEND_API_KEY:
        print("[Email] RESEND_API_KEY not set in GitHub Secrets — skipping")
        return
    try:
        payload = {
            "from": "Alfred <onboarding@resend.dev>",
            "to": [OWNER_EMAIL],
            "subject": subject,
            "text": body
        }
        print(f"[Email] Sending to {OWNER_EMAIL} via Resend...")
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        print(f"[Email] Response: {r.status_code} — {r.text}")
        if r.ok:
            _email_sent = True
            print(f"[Email] SUCCESS — sent to {OWNER_EMAIL}")
        else:
            print(f"[Email] FAILED: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[Email] ERROR: {e}")

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
        "description": "Run a shell command (git log, python, etc). Ubuntu environment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an update email to Andrew (andrewcornell2000@gmail.com) at the END of your loop. Use plain-English DOT POINTS, not paragraphs — Andrew wants a scannable list of exactly what you added and how it works.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Short subject line, e.g. 'Alfred update — added a Power Query transformations skill'"},
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
            result = subprocess.run(
                inp["command"], shell=True, capture_output=True, text=True, timeout=60
            )
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
                model="claude-opus-4-7",
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
    skills_list = ", ".join(sorted(os.listdir("skills"))) if os.path.exists("skills") else "none"

    # Alfred's growth loop is about UPGRADING HIMSELF: the tools he can use
    # (MCP servers, CLIs) and the skills for driving those tools well.
    # It must NOT touch the finance/domain skills (cash flow, labour, Excel,
    # Power BI, data-*) — those are owned by Andrew, not the loop.
    DOMAIN_ROTATION = [
        "NEW MCP TOOL: research one promising MCP server that gives Alfred a genuinely new capability "
        "(official modelcontextprotocol servers or well-regarded community ones that launch via npx or uvx). "
        "ADD it for real to the portable template cursor/mcp.json: an entry with command (npx or uvx), args, "
        "and a \"_requiresCommand\" guard (npx or uvx) so it auto-skips on machines lacking that runtime. "
        "If it needs a key, put \"${env:VAR}\" in env and list VAR under \"_requires\" — NEVER write the key itself. "
        "Then write a short how-to skill in skills/ for it and add a one-line entry to requirements/mcp-tools.md. "
        "Result: the tool becomes usable by Claude, Codex AND Cursor the next time Andrew provisions. "
        "Do NOT duplicate a server already in cursor/mcp.json.",
        "TOOL SKILL: write a how-to skill for driving ONE tool Alfred already has (e.g. the GitHub MCP, "
        "Playwright MCP, Power BI MCP, Excel MCP, or the claude/codex CLI) — concrete commands, common "
        "workflows, gotchas, and when to reach for it. Skills go in skills/.",
        "NEW CLI TOOL: research one useful CLI tool Alfred should be able to drive. Add it to the right "
        "manifest (requirements/npm-tools.txt or requirements/python-requirements.txt) in the documented "
        "format AND mirror it into requirements/alfred-tools.json, with purpose and routing category.",
        "DEEPEN a TOOL skill: pick an existing tool/how-to skill and make it materially better "
        "(add a worked example, fix gaps, sharpen triggers). Do NOT touch finance/domain skills.",
        "ROUTING: review backend/main.py routing keywords for the tools Alfred has and propose/document "
        "improvements so the right tool is picked for the right request. Keep destructive tools behind the safety gate.",
        "CONSOLIDATE: if two existing TOOL skills overlap, merge them into one stronger file and delete the weaker.",
    ]
    focus = DOMAIN_ROTATION[int(iteration_num) % len(DOMAIN_ROTATION)] if iteration_num.isdigit() else DOMAIN_ROTATION[0]

    system = (
        "You are Alfred — an autonomous AI agent running in GitHub Actions (ubuntu-latest). "
        "Your growth loop is for UPGRADING YOURSELF: the tools you can use (MCP servers, CLIs) and the "
        "how-to skills for driving those tools well. Do NOT edit the finance/domain skills "
        "(cash flow, labour, working capital, Excel, Power BI, data-*) — those belong to Andrew, not you. "
        "You have tools: read_file, write_file, list_files, web_search, fetch_url, run_command, send_email. "
        "Each run must leave the repo genuinely better — a new tool documented or a tool how-to improved. "
        "An empty or stub file counts as a FAILED run, not a completed one. "
        "Files you write are automatically committed to https://github.com/andrewcornell2000-Work/Alfred"
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

=== YOUR MISSION THIS ITERATION ===
{focus}

Steps:
1. Read the existing skills list above. If your mission touches a topic that already has a
   skill, IMPROVE or MERGE that file — do NOT create a near-duplicate with a slightly different name.
2. Do 1-2 targeted web searches if the topic needs current facts.
3. Write a COMPLETE file with write_file. Then read_file it back to confirm it is non-empty and
   genuinely useful before you move on.
4. Update memory/learning-log.md with what you did.
5. Call send_email with an update for Andrew. Use plain-English DOT POINTS (not paragraphs):
   a "What I added" list, a "How it works" list (everyday language — what it does and how he'd
   use it), and a short "What's next". Be specific. No file paths or jargon. Only claim you built
   something if the file is real and complete.

This is your ONE run today. Don't rush and don't pad — go deep and ship a single excellent,
complete deliverable. Depth and correctness matter far more than covering extra ground.

QUALITY BAR (this is the whole point of the loop):
- SCOPE: this loop only upgrades Alfred's TOOLS and tool how-to skills. NEVER edit the finance/domain
  skills (cash-flow-forecasting, labour-cost-forecasting, working-capital-metrics, excel-*, powerbi-*,
  powerquery-*, data-*). If your mission would touch one of those, pick a different tool-focused mission.
- NEVER leave an empty or stub file. An empty file is worse than no file — it is noise. If you cannot
  write a complete, useful file this run, improve an existing tool skill instead.
- NO near-duplicates. Prefer one excellent tool guide over three thin ones.
- A run that consolidates or sharpens an existing tool skill is MORE valuable than a shallow new file.
- Be efficient — do not re-read files already shown above.
- Tool how-to skills go in skills/, tool manifests in requirements/, memory updates in memory/.

TOOLING MISSIONS (MCP / CLI) — extra rules:
- MCP server: ADD it to the portable template cursor/mcp.json with a "_requiresCommand" guard (npx/uvx)
  so it auto-skips where the runtime is absent. This is SAFE — it installs nothing on Andrew's machine;
  it just makes the tool available the next time he provisions (which registers it for Claude + Codex + Cursor).
  Also write a how-to skill in skills/.
- CLI tool: document it in the right manifest (requirements/). Do NOT edit setup.ps1 — Andrew owns install policy.
- NEVER write an API key, token, or credential into any file — use "${env:VAR}" in env + list it under "_requires".
- Never say a tool is "installed on the machine". Say it is "added to the catalog, applied on next provision".
- If a tool is destructive (can write/delete/modify live data), say so in its skill and note it must be added
  to the safety gate (DANGEROUS_KEYWORDS in backend/main.py) before it is ever allowed to dispatch.
- Don't duplicate a server already in cursor/mcp.json or a tool already in requirements/.

Start immediately. Pick your mission and begin.
"""
        }
    ]

    print("=== Alfred Growth Loop starting ===\n")

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

        if response.stop_reason == "end_turn" or not tool_uses:
            print("\n=== Alfred loop complete ===")
            break

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for t in tool_uses:
            print(f"\n[{t.name}] {json.dumps(t.input)[:120]}")
            result = handle_tool(t.name, t.input)
            result_str = str(result)
            print(f"  → {result_str[:200]}")
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
            os.remove(p)  # `git add -A` in the workflow will stage the removal
            print(f"[QualityGate] Removed empty/stub file: {p}")
            continue
        substantive.append(p)

    if _email_sent:
        print("[Email] Alfred already emailed this run — skipping fallback")
    elif substantive:
        files_summary = "\n".join(f"  - {f}" for f in substantive)
        send_update_email(
            subject=f"Alfred update — {datetime.utcnow().strftime('%d %b %Y, %H:%M')} AEST",
            body=(
                f"Hi Andrew,\n\n"
                f"Just finished my latest growth loop. Here's what I got done:\n\n"
                f"Files I built or updated:\n{files_summary}\n\n"
                f"You can see everything at:\n"
                f"https://github.com/andrewcornell2000-Work/Alfred\n\n"
                f"I'll run again tomorrow at noon.\n\n"
                f"— Alfred"
            )
        )
    else:
        print("[QualityGate] No substantive output this run — sending honest note")
        send_update_email(
            subject="Alfred update — quiet run, nothing worth shipping",
            body=(
                "Hi Andrew,\n\n"
                "I ran my growth loop but didn't produce anything solid enough to keep this time, "
                "so I'm not padding the repo with busywork. Just a heads-up that I'm alive — "
                "I'll try again tomorrow at noon.\n\n"
                "— Alfred"
            )
        )


if __name__ == "__main__":
    run()
