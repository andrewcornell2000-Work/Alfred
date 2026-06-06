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
        "description": "Send a plain-English update email to Andrew (andrewcornell2000@gmail.com) at the END of your loop. Write like a smart colleague giving a quick debrief — no code, no markdown, no jargon. Just clear sentences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Short subject line, e.g. 'Alfred update — built a labour forecasting tool'"},
                "body": {"type": "string", "description": "Plain English email. Use this structure: 1) What you worked on this iteration and why. 2) What you actually built and what it does for the team in practical terms. 3) One interesting thing you learned. 4) What you plan to do next. Sign off as Alfred. NO markdown, NO code blocks, NO file paths, NO technical jargon — write it so anyone can understand it."}
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
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
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

    # Rotate the mission so Alfred alternates between DEEPENING the finance/data
    # skills that already pay off and BROADENING into genuinely new territory,
    # instead of grinding out near-duplicate finance docs every run.
    DOMAIN_ROTATION = [
        "DEEPEN an existing high-value skill: pick ONE skill that already exists and make it "
        "materially better (add a worked example, fix gaps, sharpen triggers). Do NOT create a new file.",
        "NEW MCP TOOL: research one promising MCP server that would extend Alfred (look at the "
        "official modelcontextprotocol servers and well-regarded community ones). Document it as a "
        "CANDIDATE following the 'Learning Mode: Adding MCP Tools' process in requirements/mcp-tools.md — "
        "add the entry there AND to the mcp.tools array in requirements/alfred-tools.json as a PLANNED tool.",
        "BROADEN into a NEW domain Alfred can't yet help with — something outside Maersk finance "
        "(e.g. coding/automation, writing, research workflows, a tool Andrew uses). Create one solid new skill.",
        "NEW CLI TOOL: research one useful CLI tool Alfred should be able to drive. Add it to the "
        "right manifest (requirements/npm-tools.txt or requirements/python-requirements.txt) in the "
        "documented format AND mirror it into requirements/alfred-tools.json. Document the purpose and "
        "which routing category it serves.",
        "Excel / Power BI / Power Query power-user techniques the team would actually use.",
        "CONSOLIDATE: if two existing skills overlap, merge them into one stronger file and delete the weaker.",
    ]
    focus = DOMAIN_ROTATION[int(iteration_num) % len(DOMAIN_ROTATION)] if iteration_num.isdigit() else DOMAIN_ROTATION[0]

    system = (
        "You are Alfred — an autonomous AI agent running in GitHub Actions (ubuntu-latest). "
        "You have tools: read_file, write_file, list_files, web_search, fetch_url, run_command, send_email. "
        "Each run must leave the repo genuinely better — either a complete new skill or a real improvement "
        "to an existing one. An empty or stub file counts as a FAILED run, not a completed one. "
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
5. Call send_email with a plain-English update for Andrew — like a colleague, not a computer.
   No markdown, no file paths, no jargon. Only claim you built something if the file is real and complete.

QUALITY BAR (this is the whole point of the loop):
- NEVER leave an empty or stub file. An empty file is worse than no file — it is noise. If you cannot
  write a complete, useful file this run, improve an existing one instead.
- NO near-duplicates. Six overlapping finance docs help no one. Prefer one excellent file over three thin ones.
- A run that consolidates or sharpens an existing skill is MORE valuable than a shallow new file.
- Be efficient — do not re-read files already shown above.
- Skills go in skills/, briefs go in memory/briefs/, memory updates go in memory/.

TOOLING MISSIONS (MCP / CLI) — extra rules:
- DOCUMENT only. Add the tool to the manifests as a CANDIDATE/PLANNED entry. NEVER auto-install it,
  never edit setup.ps1, and never claim it is installed — Andrew approves installs separately.
- NEVER write an API key, token, or credential into any file.
- If a tool is destructive (can write/delete/modify live data), say so in its entry and note it must be
  added to the safety gate (DANGEROUS_KEYWORDS in backend/main.py) before it is ever allowed to dispatch.
- Don't duplicate a tool that's already listed in requirements/ — extend or skip it instead.

Start immediately. Pick your mission and begin.
"""
        }
    ]

    print("=== Alfred Growth Loop starting ===\n")

    for iteration in range(15):
        response = api_call_with_retry(messages, system)

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
                f"I'll run again in 8 hours.\n\n"
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
                "I'll try again in 8 hours.\n\n"
                "— Alfred"
            )
        )


if __name__ == "__main__":
    run()
