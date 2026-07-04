"""
Alfred Secure Learning Loop — GitHub Actions / cloud agent.
Researches trusted sources, proposes candidates via review queue (secure mode).
"""

import anthropic
import os
import sys
import json
import re
import shlex
import subprocess
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_utils import OWNER_EMAIL, send_alfred_email

SECURE_MODE = os.environ.get("ALFRED_SECURE_MODE", "1") == "1"
MAX_WEB_SEARCHES = 3
MAX_ITERATIONS = 8 if SECURE_MODE else 12
MAX_NEW_CANDIDATES_PER_RUN = 2

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")

_email_sent = False
_web_search_count = 0
_candidates_added = 0


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
        "name": "add_review_candidate",
        "description": (
            "Add or update a capability candidate in requirements/review-queue.json. "
            "Use for NEW MCPs/CLIs before any manifest install. Required fields: slug, type, "
            "name, source_url, trust_level, license, description, install_notes, try_asking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate": {
                    "type": "object",
                    "description": "Candidate object matching review queue schema",
                }
            },
            "required": ["candidate"],
        },
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


def load_review_queue() -> dict:
    path = Path("requirements/review-queue.json")
    if not path.exists():
        return {"items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_review_queue(data: dict) -> None:
    path = Path("requirements/review-queue.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def approved_slugs() -> set[str]:
    return {
        item["slug"]
        for item in load_review_queue().get("items", [])
        if item.get("status") == "approved" and item.get("slug")
    }


def add_review_candidate(candidate: dict) -> str:
    global _candidates_added
    required = ["slug", "type", "name", "source_url", "trust_level", "description"]
    missing = [k for k in required if not candidate.get(k)]
    if missing:
        return f"Rejected: missing fields {missing}"

    if candidate.get("requires_admin"):
        return "Rejected: requires_admin not allowed"

    slug = candidate["slug"].lower().strip()
    candidate["slug"] = slug
    candidate.setdefault("status", "discovered")
    candidate.setdefault("security_status", "pending")
    candidate.setdefault("discovered_at", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    data = load_review_queue()
    items = data.get("items", [])
    for i, existing in enumerate(items):
        if existing.get("slug") == slug:
            items[i] = {**existing, **candidate}
            data["items"] = items
            data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            save_review_queue(data)
            return f"Updated review candidate: {slug}"

    if _candidates_added >= MAX_NEW_CANDIDATES_PER_RUN:
        return f"Rejected: max {MAX_NEW_CANDIDATES_PER_RUN} new candidates per run"

    items.append(candidate)
    data["items"] = items
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_review_queue(data)
    _candidates_added += 1
    return f"Added review candidate: {slug} (status={candidate['status']})"


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
            err = validate_write(p, inp["content"])
            if err:
                return f"Rejected: {err}"
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
            global _web_search_count
            if _web_search_count >= MAX_WEB_SEARCHES:
                return f"Rejected: max {MAX_WEB_SEARCHES} web searches per run (stop and write findings)."
            _web_search_count += 1
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

        elif name == "add_review_candidate":
            return add_review_candidate(inp["candidate"])

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


def validate_write(path: str, content: str) -> str | None:
    """Return error string if write should be rejected, else None."""
    norm = path.replace("\\", "/").lstrip("./")

    if norm.startswith("skills/taste-") or "/taste-" in norm:
        return "NEVER write skills/taste-*.md — use Leonxlnx/taste-skill via npx on user machines."

    if norm == "skills/lean-ctx.md" or norm == "skills/mcp-routing.md":
        return (
            f"{norm} is repo documentation only — covered by cursor/rules/. "
            "Improve cursor/rules/ instead of syncing as a skill."
        )

    if norm.startswith("skills/agent-") and os.path.exists("skills/agent-playbook.md"):
        return "Use skills/agent-playbook.md — do not create new agent-* skills."

    if norm.startswith("skills/agent-") and os.path.exists(norm):
        stem = Path(norm).stem
        for existing in os.listdir("skills"):
            if not existing.endswith(".md") or existing == Path(norm).name:
                continue
            if existing.startswith("agent-") and existing != Path(norm).name:
                # block near-duplicate agent-* filenames
                a = stem.replace("agent-", "")
                b = existing.replace(".md", "").replace("agent-", "")
                if a in b or b in a:
                    return (
                        f"Topic overlaps skills/{existing}. IMPROVE that file instead of creating {norm}."
                    )

    if norm == "cursor/mcp.json" and SECURE_MODE:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return f"Invalid JSON for cursor/mcp.json: {e}"
        servers = data.get("mcpServers", {})
        approved = approved_slugs()
        existing_path = Path("cursor/mcp.json")
        old_keys = set()
        if existing_path.exists():
            old_keys = set(json.loads(existing_path.read_text(encoding="utf-8")).get("mcpServers", {}).keys())
        new_keys = set(servers.keys()) - old_keys
        unapproved = [k for k in new_keys if k not in approved]
        if unapproved:
            return (
                f"Secure mode: new MCP keys {unapproved} must be approved in review-queue first. "
                "Use add_review_candidate, then SHIP after approval."
            )

    if norm == "cursor/mcp.json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return f"Invalid JSON for cursor/mcp.json: {e}"
        servers = data.get("mcpServers", {})
        retired = set(data.get("_retiredServers", []))
        keys = list(servers.keys())
        if len(keys) != len(set(keys)):
            return "Duplicate MCP server keys in mcp.json"
        for r in retired:
            if r in servers:
                return f"Retired server '{r}' must not appear in mcpServers"
        fps = {}
        for name, cfg in servers.items():
            fp = f"{cfg.get('command')}:{cfg.get('args', [])[:2]}"
            if fp in fps:
                return f"MCP '{name}' duplicates fingerprint of '{fps[fp]}'"
            fps[fp] = name

    if norm == "requirements/discovered-tools.md":
        new_slugs = set(re.findall(r"^###\s+([a-z0-9-]+)", content, flags=re.MULTILINE))
        if os.path.exists(norm):
            old = open(norm, encoding="utf-8").read()
            old_slugs = set(re.findall(r"^###\s+([a-z0-9-]+)", old, flags=re.MULTILINE))
            added = new_slugs - old_slugs
            if len(added) > 3:
                return (
                    f"Too many new catalog slugs in one write ({len(added)}). "
                    "Merge into existing ### blocks or run CATALOG refresh mission."
                )

    if norm.startswith("skills/") and len(content) > 20000:
        return f"{norm} exceeds 20KB — trim reference material into docs/ or merge with existing skill."

    return None


def run():
    import time

    # Pre-load critical context so Alfred starts working immediately
    git_log = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True).stdout
    iteration_num = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip()
    active_projects = read_file_safe("memory/active-projects.md")
    recent_log = read_file_safe("memory/learning-log.md", limit=800)
    discovered = read_file_safe("requirements/discovered-tools.md", limit=12000)
    mcp_catalog = read_file_safe("cursor/mcp.json", limit=8000)
    catalog_index = read_file_safe("requirements/catalog-index.json", limit=4000)
    tool_discovery = read_file_safe("skills/tool-discovery.md", limit=4000)
    skills_list = ", ".join(
        sorted(
            f for f in os.listdir("skills")
            if f.endswith(".md") and not f.startswith("taste-")
        )
    ) if os.path.exists("skills") else "none"

    # Alfred Pack growth loop: DISCOVER tools Andrew wouldn't find himself.
    # Ship to manifests so Provision-Cursor.ps1 wires Cursor + Claude + Codex globally.
    # NEVER edit finance/domain skills (cash-flow*, labour*, data-*, excel-financial*, powerbi-*, powerquery-*).
    review_queue = read_file_safe("requirements/review-queue.json", limit=6000)
    cloud_prompt = read_file_safe(".github/prompts/cloud-learning.md", limit=4000)

    DOMAIN_ROTATION = [
        "REVIEW QUEUE: pick one status=candidate or discovered item — run security checks, "
        "update trust_level, add install_notes, or mark rejected/duplicate. Use add_review_candidate.",
        "DISCOVER MCP (trusted sources only): 1-2 web searches on official MCP repos / vendor docs. "
        "add_review_candidate — do NOT write cursor/mcp.json until approved.",
        "DISCOVER CLI: trusted GitHub only. add_review_candidate or improve existing skill.",
        "IMPROVE skill: update ONE existing skills/*.md (not finance domain). Include Try asking.",
        "SHIP approved: find status=approved in review-queue — promote to cursor/mcp.json + skill + manifests.",
        "CATALOG refresh: merge duplicates in discovered-tools.md and review-queue.json.",
    ]
    focus = DOMAIN_ROTATION[int(iteration_num) % len(DOMAIN_ROTATION)] if iteration_num.isdigit() else DOMAIN_ROTATION[0]

    system = (
        "You are Alfred's SECURE learning agent (GitHub Actions cloud loop). "
        "Follow .github/prompts/cloud-learning.md and docs/LEARNING-WORKFLOW.md. "
        "SECURITY FIRST: new MCPs/CLIs go to add_review_candidate — NOT cursor/mcp.json until approved. "
        "Max 3 web_search calls. Max 2 new candidates per run. Max 8 iterations. "
        "Prefer official sources. Reject admin installs and suspicious scripts. "
        "Improve existing skills before creating new ones. Use agent-playbook.md not new agent-* files. "
        "Never edit finance/domain skills. Tools: read_file, write_file, list_files, web_search, "
        "fetch_url, run_command, add_review_candidate, send_email."
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

=== CATALOG INDEX (canonical slugs — do not duplicate) ===
{catalog_index}

=== TOOL DISCOVERY CHECKLIST ===
{tool_discovery}

=== REVIEW QUEUE ===
{review_queue}

=== CLOUD AGENT RULES (summary) ===
{cloud_prompt}

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
- NEW tools → add_review_candidate first (secure pipeline)
- SHIP only status=approved items to cursor/mcp.json
- Max 3 web searches — cite queries in learning-log.md
- NEVER leave empty/stub files
- Update memory/learning-log.md every run

Start immediately. Pick your mission and begin.
"""
        }
    ]

    print("=== Alfred Secure Learning Loop starting ===\n")

    files_written = 0

    for iteration in range(MAX_ITERATIONS):
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
