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


def send_update_email(subject, body):
    """Send Alfred's loop summary via Resend API."""
    if not RESEND_API_KEY:
        print("RESEND_API_KEY not set — skipping email")
        return
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": "Alfred <onboarding@resend.dev>",
                "to": [OWNER_EMAIL],
                "subject": subject,
                "text": body
            },
            timeout=15
        )
        if r.ok:
            print(f"Email sent to {OWNER_EMAIL}")
        else:
            print(f"Email failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Email error: {e}")

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
        "description": "Send an email update to the owner (andrewcornell2000@gmail.com). Use this at the END of your loop to summarise what you discovered and built this iteration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Email subject line — include what you built, e.g. 'Alfred Update — Built Labour Planning Skill'"},
                "body": {"type": "string", "description": "Full email body — what you researched, what you built, what files changed, what's next"}
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
                model="claude-sonnet-4-6",
                max_tokens=3000,
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


def run():
    import time

    git_log = subprocess.run(
        ["git", "log", "--oneline", "-5"], capture_output=True, text=True
    ).stdout

    # Keep initial message small — Alfred reads his own files via tools
    system = (
        "You are Alfred — an autonomous AI agent running inside GitHub Actions on ubuntu-latest. "
        "You have tools to read/write files, search the web, and run shell commands. "
        "You cannot access Windows-local files or run the Claude CLI. "
        "Focus on: research, writing/improving skills, updating memory, "
        "improving routing logic, finding new MCPs, writing team briefs. "
        "Files you write are committed to the repo automatically."
    )

    messages = [
        {
            "role": "user",
            "content": (
                "You are Alfred. Read ALFRED_LOOP_PROMPT.md for your full instructions, "
                "then read memory/brain.md, memory/learning-log.md, and memory/active-projects.md "
                "to know where you left off. Then execute your loop.\n\n"
                f"Recent git history:\n{git_log}"
            )
        }
    ]

    print("=== Alfred Growth Loop starting ===\n")

    for iteration in range(12):
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

    # Fallback: auto-send email summary based on git log if Alfred didn't send one
    git_summary = subprocess.run(
        ["git", "log", "--oneline", "-5"], capture_output=True, text=True
    ).stdout
    git_diff_stat = subprocess.run(
        ["git", "diff", "HEAD~1", "--stat"], capture_output=True, text=True
    ).stdout or "No new changes committed this iteration."

    send_update_email(
        subject=f"Alfred Loop Complete — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        body=(
            f"Hi Andrew,\n\n"
            f"Alfred has completed an autonomous growth loop iteration.\n\n"
            f"=== RECENT COMMITS ===\n{git_summary}\n"
            f"=== FILES CHANGED THIS ITERATION ===\n{git_diff_stat}\n"
            f"=== ALFRED'S REPO ===\n"
            f"https://github.com/andrewcornell2000-Work/Alfred\n\n"
            f"— Alfred\n"
            f"alfredTCP2000@gmail.com"
        )
    )


if __name__ == "__main__":
    run()
