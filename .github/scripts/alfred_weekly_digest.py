"""
Alfred Weekly Digest
Runs Monday noon AEST. Summarises the past 7 days of discovery-loop work.
No LLM call — compiles from git log, learning-log, and discovered-tools catalog.
"""

import os
import re
import sys
import subprocess
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_utils import send_alfred_email

DAYS = 7


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, timeout=60
    )
    return (result.stdout or "").strip()


def _commits_since(since_iso: str) -> list[tuple[str, str, str]]:
    raw = _run_git(
        "log",
        f"--since={since_iso}",
        '--pretty=format:%h|%ad|%s',
        "--date=short",
    )
    if not raw:
        return []
    rows = []
    for line in raw.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def _loop_commits(commits: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return [c for c in commits if "alfred loop" in c[2].lower() or "discovery" in c[2].lower()]


def _files_changed_since(since_iso: str, path: str) -> list[str]:
    raw = _run_git("log", f"--since={since_iso}", "--name-only", "--pretty=format:", "--", path)
    return sorted({ln.strip() for ln in raw.splitlines() if ln.strip()})


def _parse_learning_log(since_date) -> list[dict]:
    path = "memory/learning-log.md"
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    for match in re.finditer(
        r"## (\d{4}-\d{2}-\d{2})[^\n]*\n(.*?)(?=\n## \d{4}-\d{2}-\d{2}|\Z)",
        content,
        re.DOTALL,
    ):
        date_str = match.group(1)
        block = match.group(2)
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_date < since_date:
            continue
        title_match = re.search(r"## \d{4}-\d{2}-\d{2}[^\n—]*—\s*(.+)", match.group(0))
        title = title_match.group(1).strip() if title_match else "Update"
        summary = ""
        sm = re.search(r"\*\*Change summary:\*\*\s*\n(.*?)(?=\n\*\*|\n---|\Z)", block, re.DOTALL)
        if sm:
            bullets = [
                ln.strip().lstrip("- ").strip()
                for ln in sm.group(1).splitlines()
                if ln.strip().startswith("-")
            ]
            summary = bullets[0] if bullets else sm.group(1).strip()[:200]
        entries.append({"date": date_str, "title": title, "summary": summary})
    return entries


def _parse_discovered_tools(since_date) -> list[dict]:
    path = "requirements/discovered-tools.md"
    if not os.path.isfile(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "<!-- loop appends below this line -->"
    if marker in content:
        content = content.split(marker, 1)[1]

    entries = []
    for block in re.split(r"\n### ", content):
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        name = block.split("\n", 1)[0].strip()
        if not name or name.startswith("|"):
            continue

        date_match = re.search(r"\*\*Discovered:\*\*\s*(\d{4}-\d{2}-\d{2})", block)
        if not date_match:
            continue
        try:
            discovered = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if discovered < since_date:
            continue

        def _field(label: str) -> str:
            m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
            return m.group(1).strip() if m else ""

        entries.append({
            "name": name,
            "category": _field("Category"),
            "what": _field("What it does"),
            "try_asking": _field("Try asking").strip('"').strip("'"),
            "status": _field("Status"),
            "date": date_match.group(1),
        })
    return entries


def _parse_active_focus() -> list[str]:
    path = "memory/active-projects.md"
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    targets = []
    in_section = False
    for line in content.splitlines():
        if line.strip().startswith("## Discovery targets"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip().startswith("- "):
            targets.append(line.strip()[2:])
    return targets[:5]


def build_digest() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=DAYS)).date()
    since_iso = since.isoformat()
    week_end = now.strftime("%d %b %Y")

    commits = _commits_since(since_iso)
    loop_commits = _loop_commits(commits)
    learning = _parse_learning_log(since)
    discovered = _parse_discovered_tools(since)
    mcp_touches = _files_changed_since(since_iso, "cursor/mcp.json")
    skill_files = _run_git("log", f"--since={since_iso}", "--name-only", "--pretty=format:", "--", "skills/")
    new_skills = sorted({
        ln.strip()
        for ln in skill_files.splitlines()
        if ln.strip().endswith(".md") and "skills/" in ln
    })

    subject = f"Alfred weekly digest — week ending {week_end}"

    lines = [
        f"Hi Andrew,\n",
        f"Your Alfred Pack weekly roundup ({since.isoformat()} → {week_end}).\n",
        "WHAT TO DO",
        "- Pull latest: git pull in %USERPROFILE%\\Alfred (or re-run Alfred-Install.exe)",
        "- Work in Cursor — paste any Try asking prompt below\n",
    ]

    if discovered:
        lines.append("NEW TOOLS TO TRY (paste into Cursor)")
        for d in discovered:
            prompt = d["try_asking"] or f"Show me how to use {d['name']}"
            status = f" [{d['status']}]" if d["status"] else ""
            lines.append(f"- {d['name']}{status}: \"{prompt}\"")
            if d["what"]:
                lines.append(f"  ({d['what']})")
        lines.append("")
    else:
        lines.append("NEW TOOLS TO TRY")
        lines.append("- No new catalog entries this week — daily loop still running.")
        lines.append("  Check requirements/discovered-tools.md for the full list.\n")

    lines.append("THIS WEEK'S SHIPMENTS")
    if learning:
        for e in learning:
            summary = f" — {e['summary']}" if e["summary"] else ""
            lines.append(f"- {e['date']}: {e['title']}{summary}")
    elif loop_commits:
        for h, d, msg in loop_commits[:10]:
            lines.append(f"- {d}: {msg} ({h})")
    elif commits:
        for h, d, msg in commits[:10]:
            lines.append(f"- {d}: {msg} ({h})")
    else:
        lines.append("- Quiet week — no commits in the last 7 days.")
    lines.append("")

    if new_skills:
        lines.append("NEW / UPDATED SKILLS")
        for s in new_skills[:12]:
            lines.append(f"- {s}")
        if len(new_skills) > 12:
            lines.append(f"- …and {len(new_skills) - 12} more")
        lines.append("")

    if mcp_touches:
        lines.append("MCP PACK")
        lines.append("- cursor/mcp.json changed this week — re-run Provision-Cursor.ps1 after pull.")
        lines.append("")

    focus = _parse_active_focus()
    if focus:
        lines.append("NEXT WEEK — DISCOVERY TARGETS")
        for t in focus:
            lines.append(f"- {t}")
        lines.append("")

    lines.append(f"Daily updates continue every day at noon AEST ({len(loop_commits)} loop run(s) this week).")
    lines.append("Repo: https://github.com/andrewcornell2000-Work/Alfred")
    lines.append("\n— Alfred")

    return subject, "\n".join(lines)


def run():
    print("=== Alfred Weekly Digest ===\n")
    subject, body = build_digest()
    print(body)
    print()
    if not send_alfred_email(subject, body):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
