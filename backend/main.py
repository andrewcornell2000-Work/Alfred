from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.markdown import Markdown
from rich import box
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import webbrowser
import mimetypes

import power_query as pq_helper


# Always load .env from the Alfred project root, regardless of working directory.
# Computed from __file__ so it works whether Alfred is started from any CWD.
_ENV_PATH = (
    os.path.join(os.path.dirname(sys.executable), ".env")
    if getattr(sys, "frozen", False)
    else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)
load_dotenv(_ENV_PATH, override=True)   # override=True so .env wins over empty system env vars

# On corporate networks with SSL inspection, Python's bundled CA bundle
# doesn't include the corporate root cert. truststore makes Python use the
# Windows certificate store (where IT has already installed the corp CA).
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Force UTF-8 output so rich does not fall back to the cp1252 legacy renderer
# on Windows when stdout is not a recognised VT terminal (e.g. piped or
# redirected).
_stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_stdout_utf8, highlight=False)

CLASSIFIER_PROMPT = """
You are an AI task router.

Classify requests into ONE category only:

GENERAL
POWERBI
CLAUDE_EXECUTION

CLAUDE_EXECUTION: Any request that requires taking direct action on files, systems, or external services.
This includes:
- File and code tasks: organise/organize folders, read/edit/create/delete files, run scripts,
  fix bugs, write code, refactor, inspect files, scan directories, execute commands
- Browser automation: navigating websites, filling forms, scraping data, taking screenshots
- GitHub operations: creating PRs, managing issues, reviewing diffs, searching repositories,
  pushing files, creating branches
- Excel or Power BI operations: reading/writing spreadsheets, editing charts, building visuals

POWERBI: Questions about Power BI design, architecture, or DAX that can be answered without
live tool use (no execution needed).

GENERAL: Conversation, factual questions, research, and anything that does not require acting
on a file or external system — including questions about latest versions, current events,
prices, people, or anything that benefits from a web search.

Return ONLY the category name.
"""

GENERAL_RESPONSE_PROMPT = """
You are Alfred — a personal AI assistant running on the user's Windows PC.

You have real tools on this machine:
- Files & folders: read, write, organise anything on this PC or OneDrive
- Excel: live workbook automation (open, read, write, pivot tables, charts, VBA)
- Power BI: DAX, model editing, relationships, visuals, Power Query
- Code: write, fix, refactor, test in any language
- Browser: navigate websites, fill forms, scrape data, take screenshots
- GitHub: pull requests, issues, code review, commits, branches
- Office documents: Word reports, PowerPoint decks, PDF extraction
- Web search: live news, prices, documentation, current events

How to behave:
- Be direct. If they ask you to find a file, find it. If they want a report checked, check it.
- Match the user's tone — casual when they're casual, precise when they need it.
- When you've done something, briefly say what you found or changed.
- If something's unclear, ask one short question rather than guessing or refusing.
- Never use filler phrases like "Certainly!", "Great question!", or "Of course!".
- Don't describe what you're about to do at length — just do it and report back.
"""

ALFRED_EXECUTOR_PROMPT = """
You are Alfred's execution engine running on the user's Windows PC.

Complete the task using available tools — file system, MCP servers (Excel, Power BI, GitHub, browser), code execution.

Rules:
1. Act directly. Use your tools. Don't just plan — complete the task.
2. Before deleting, overwriting, or publishing anything irreversible, describe exactly what you're about to do and ask for confirmation.
3. After finishing, give a plain-English summary: what you found, what you changed, what's next if anything.
4. If a required target (file, workbook, URL) isn't specified and can't be inferred, ask one short question.
5. Keep your response focused — the user sees everything you output.
"""

LEARNING_DISCUSSION_PROMPT = """
You are Alfred, a personal AI assistant helping a user update how you work.

Before writing any code, briefly discuss the proposed change:
1. Describe what's being proposed in plain English (1 sentence)
2. Flag any trade-off worth knowing about (1 sentence — skip if it's straightforward)
3. End with exactly: **Proposed change:** <one-line summary>

Keep it to 3–4 sentences max. No filler phrases.
"""

CLAUDE_SCOPE_PROMPT = """
You are an AI orchestration planner.

Your job:
Generate a SAFE and TOKEN-EFFICIENT Claude Code prompt.

General rules:
- minimize MCP usage
- avoid broad scans
- inspect minimum scope
- stop after diagnosis unless user asked for fixes
- prefer targeted inspection
- always include a hard stop condition
- never tell Claude to scan all source files

Power BI architecture and design questions:
If the user asks about architecture, scalability, model design, data model, star schema, fact/dim tables, relationships, or query count strategy, focus the plan on:
- model architecture and table grain
- fact/dimension layout and relationship strategy
- refresh design and incremental refresh scope
- query dependency structure and fan-out risk
- maintenance complexity and documentation gaps
Do NOT mention Transform Sample File, Transform File function, Changed Type, Removed Columns, or Expanded Table Column steps for these questions.

Power Query error debugging (conditional):
Only apply the following when the user explicitly mentions Power Query combine, schema drift, missing columns, folder combine, or source file errors:
- inspect query steps before source file contents
- prefer Transform Sample File, Transform File function, Changed Type, Removed Columns, Expanded Table Column steps
- only inspect source files after query steps confirm the issue cannot be diagnosed

Return:
1. likely issue
2. first inspection target
3. forbidden scope
4. optimized Claude prompt
"""

if getattr(sys, "frozen", False):
    _ROOT = os.path.dirname(sys.executable)
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _call_claude(system_prompt: str, user_content: str, timeout: int = 60) -> str:
    """Send a prompt to Claude and return the response text.

    Fast path (ANTHROPIC_API_KEY in .env): direct Anthropic Python SDK call — ~1-2s.
    Slow path (no API key): claude CLI subprocess — ~8-12s due to Node.js + MCP init overhead.
    """
    # ── Fast path ──────────────────────────────────────────────────────────────
    result_fast = _call_anthropic(system_prompt, user_content, timeout)
    if result_fast:
        return result_fast

    # ── Slow path: claude CLI subprocess ───────────────────────────────────────
    full_prompt = f"{system_prompt.strip()}\n\n---\n\n{user_content.strip()}"
    # Windows command line limit is ~8191 chars — write long prompts to a temp file
    exe = _resolve_claude_executable()
    try:
        if len(full_prompt) > 6000:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(full_prompt)
                tmp_path = f.name
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-Content -Raw '{tmp_path}' | & '{exe}' -p -"],
                    capture_output=True, text=True, timeout=timeout,
                )
            finally:
                try: os.unlink(tmp_path)
                except Exception: pass
        else:
            result = subprocess.run(
                [exe, "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        if result.returncode == 0:
            return result.stdout.strip()
        console.print(f"[dim red]Claude CLI: {result.stderr.strip()[:120]}[/dim red]")
    except FileNotFoundError:
        msg = (
            "Claude Code CLI is not installed.\n"
            "Fix it now:\n"
            "  1. npm install -g @anthropic-ai/claude-code\n"
            "  2. claude login\n"
            "Then restart Alfred."
        )
        console.print(f"[bold red]Setup required:[/bold red]\n{msg}")
        return msg
    except subprocess.TimeoutExpired:
        console.print("[dim red]Claude CLI timed out.[/dim red]")
    return ""




def _action_pbi_connect() -> None:
    """Open a new terminal and run 'pbi connect' to link pbi-cli to Power BI Desktop."""
    pbi_exe = shutil.which("pbi.cmd") or shutil.which("pbi")
    if not pbi_exe:
        venv_pbi = os.path.join(_ROOT, ".venv", "Scripts", "pbi.exe")
        if os.path.isfile(venv_pbi):
            pbi_exe = venv_pbi
    if not pbi_exe:
        console.print(
            "[bold red]pbi not found.[/bold red] "
            "Re-run Alfred-Install.exe to install pbi-cli-tool, then try again."
        )
        return
    console.print("[dim]Opening terminal to connect pbi-cli to Power BI Desktop...[/dim]")
    console.print("[dim]Make sure Power BI Desktop is open with your file before confirming.[/dim]")
    try:
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", pbi_exe, "connect"])
        console.print("[bold green]Terminal opened. Run 'pbi connect' completes the link.[/bold green]")
        console.print("[dim]Once connected, ask Alfred to create or edit Power BI visuals.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Could not open terminal:[/bold red] {e}")
        console.print(f"Run manually in a new terminal (with .venv active): [bold yellow]pbi connect[/bold yellow]")


# ── Memory system ──────────────────────────────────────────────────────────────

AUTOSAVE_THRESHOLD = 10
AUTOSAVE_KEEP = 5

AUTOSAVE_COMPRESS_PROMPT = """You are a memory consolidation assistant for Alfred, an AI orchestrator.

Given the existing summaries and recent autosave entries, produce updated content for two files.

Return exactly this format (no code fences, no extra text outside the delimiters):
---SESSION-SUMMARY---
<updated session-summary.md: bullet-pointed sections for Current Architecture, Current Features, Current Skills, Important Design Rules, Next Planned Features. Preserve all existing history; incorporate new changes.>
---RECENT-CONTEXT---
<updated recent-context.md: 3-8 bullet points covering the most recent activity — what was worked on, decisions made, outcomes, and what to continue next.>
"""

SESSION_EXIT_PROMPT = """You are a memory consolidation assistant for Alfred, an AI orchestrator.

Given autosave entries from this session, produce two concise memory sections.

Return exactly this format (no code fences, no extra text outside the delimiters):
---CURRENT-FOCUS---
<2-5 bullet points: what the user worked on this session, key problems solved or in progress>
---RECENT-CONTEXT---
<3-8 bullet points: what was done, decisions made, current state, what is ready to continue>
"""

_memory_context: str = ""

# ── Conversation history (per-session, not persisted) ─────────────────────────
_chat_history: list[dict] = []
MAX_HISTORY_TURNS = 8


def _append_to_history(role: str, content: str) -> None:
    """Append to conversation history, prune to limit, and persist after each exchange."""
    global _chat_history
    _chat_history.append({"role": role, "content": content})
    limit = MAX_HISTORY_TURNS * 2
    if len(_chat_history) > limit:
        _chat_history = _chat_history[-limit:]
    # Persist to disk after each assistant reply so history survives restarts
    if role == "assistant":
        _save_chat_history()


def _save_chat_history() -> None:
    """Write _chat_history to memory/chat-history.json (gitignored)."""
    path = os.path.join(_ROOT, "memory", "chat-history.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_chat_history[-(MAX_HISTORY_TURNS * 2):], f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _load_chat_history() -> None:
    """Load persisted chat history from disk on startup."""
    global _chat_history
    path = os.path.join(_ROOT, "memory", "chat-history.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, list):
            _chat_history = saved[-(MAX_HISTORY_TURNS * 2):]
    except Exception:
        pass


# ── Project Memory State ───────────────────────────────────────────────────────
_active_project: dict = {}          # {} when no project is active
_project_memory_context: str = ""   # combined context from active project files
_project_interaction_count: int = 0 # interactions since last project autosave compress


def _ensure_memory_files() -> None:
    """Create placeholder memory files if they do not already exist."""
    memory_dir = os.path.join(_ROOT, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    today = datetime.date.today().isoformat()
    defaults = {
        "current-focus.md": f"# Current Focus\n*Last updated: {today}*\n\nNo session data yet.\n",
        "active-projects.md": f"# Active Projects\n*Last updated: {today}*\n\nNo active projects recorded yet.\n",
        "recent-context.md": f"# Recent Context\n*Last updated: {today}*\n\nNo recent context yet.\n",
        "tool-history.md": f"# Tool History\n*Last updated: {today}*\n\nNo tool history recorded yet.\n",
        "notes.md": "",
        "autosave.md": "",
        "workspace.md": f"# Workspace\n*Last updated: {today}*\n\nNo workspace configured yet.\n",
    }
    for fname, content in defaults.items():
        path = os.path.join(memory_dir, fname)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


_MEMORY_SKIP_INJECTION = {"autosave.md"}   # raw logs — excluded from all LLM injection
_MEMORY_HOT_FILES = (                       # focused context injected into every LLM call
    "current-focus.md", "recent-context.md", "active-projects.md", "notes.md", "workspace.md"
)
_MEMORY_DEFAULT_MARKERS = {                 # placeholder text created by _ensure_memory_files
    "No session data yet.", "No active projects recorded yet.",
    "No recent context yet.", "No tool history recorded yet.",
    "No workspace configured yet.",
}


def load_all_memory() -> str:
    """Read processed memory/*.md files (excluding raw autosave log) for the viewer."""
    memory_dir = os.path.join(_ROOT, "memory")
    if not os.path.isdir(memory_dir):
        return ""
    parts = []
    for fname in sorted(os.listdir(memory_dir)):
        if not fname.endswith(".md") or fname in _MEMORY_SKIP_INJECTION:
            continue
        path = os.path.join(memory_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                parts.append(f"### {fname}\n{content}")
        except OSError:
            pass
    return "\n\n".join(parts)


def _load_hot_memory() -> str:
    """Return a compact context string from the most relevant memory files.
    Injected into every LLM call — stays small and focused."""
    memory_dir = os.path.join(_ROOT, "memory")
    if not os.path.isdir(memory_dir):
        return ""
    parts = []
    for fname in _MEMORY_HOT_FILES:
        path = os.path.join(memory_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except OSError:
            continue
        if not content or any(m in content for m in _MEMORY_DEFAULT_MARKERS):
            continue
        # Extract bullet points only (first 5) — skip headers, blank lines
        bullets = [
            ln.strip() for ln in content.splitlines()
            if ln.strip().startswith(("- ", "* ", "• "))
        ][:5]
        if bullets:
            label = fname.replace(".md", "").replace("-", " ").title()
            parts.append(f"**{label}:**\n" + "\n".join(bullets))
    return "\n\n".join(parts)


def reload_memory() -> None:
    global _memory_context
    _memory_context = _load_hot_memory()


def _setup_workspace_if_needed() -> None:
    """On first run (or when workspace.md is blank), ask where files live.

    Saves the answer to memory/workspace.md which gets injected into every
    execution prompt — so Alfred knows where to look for reports and spreadsheets
    without being told each time.
    """
    workspace_path = os.path.join(_ROOT, "memory", "workspace.md")
    # Skip if already configured
    if os.path.isfile(workspace_path):
        try:
            with open(workspace_path, "r", encoding="utf-8") as f:
                content = f.read()
            if content and "No workspace configured yet." not in content:
                return
        except OSError:
            pass

    console.print()
    console.print(
        "[bold cyan]Quick setup:[/bold cyan] Where do you keep most of your work files?"
    )
    console.print(
        "[dim]This helps Alfred find reports, spreadsheets, and documents without guessing.[/dim]"
    )
    console.print("[dim]Example: C:\\Users\\You\\OneDrive - Company\\Finance[/dim]")
    try:
        path = console.input(
            "[bold yellow]Workspace path (or press Enter to skip) > [/bold yellow]"
        ).strip()
    except EOFError:
        return

    if not path:
        console.print("[dim]Skipped — you can set this later by saying 'my workspace is ...'[/dim]")
        return

    _write_workspace(path)


def _write_workspace(path: str) -> None:
    """Save a workspace path to memory/workspace.md and reload memory."""
    workspace_file = os.path.join(_ROOT, "memory", "workspace.md")
    today = datetime.date.today().isoformat()
    with open(workspace_file, "w", encoding="utf-8") as f:
        f.write(
            f"# Workspace\n*Configured: {today}*\n\n"
            f"- Primary files: {path}\n"
        )
    reload_memory()
    console.print(f"[dim]Workspace saved. Alfred will look in [bold]{path}[/bold] first.[/dim]")


def read_memory_summary() -> str:
    path = os.path.join(_ROOT, "memory", "session-summary.md")
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def append_interaction_log(
    user_input: str, category: str, scope: str = "", provider: str = ""
) -> None:
    logs_dir = os.path.join(_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    path = os.path.join(logs_dir, "interactions.md")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## {timestamp}\n"
        f"**Category:** {category}\n"
        f"**Provider:** {provider}\n"
        f"**Input:** {user_input}\n"
        f"**Scope:** {scope[:500]}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def append_autosave_entry(
    user_input: str, category: str, provider: str, outcome: str
) -> None:
    """Append a lightweight autosave entry to memory/autosave.md."""
    memory_dir = os.path.join(_ROOT, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    path = os.path.join(memory_dir, "autosave.md")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = user_input[:200].replace("\n", " ")
    outcome_short = (outcome or "")[:300].replace("\n", " ")
    entry = (
        f"\n## {timestamp}\n"
        f"**Request:** {summary}\n"
        f"**Category:** {category}\n"
        f"**Provider:** {provider}\n"
        f"**Outcome:** {outcome_short}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def compress_autosave_if_needed() -> None:
    """Every AUTOSAVE_THRESHOLD entries, compress autosave.md into session-summary.md
    and recent-context.md, then trim autosave.md to AUTOSAVE_KEEP entries."""
    autosave_path = os.path.join(_ROOT, "memory", "autosave.md")
    if not os.path.isfile(autosave_path):
        return

    with open(autosave_path, "r", encoding="utf-8") as f:
        content = f.read()

    count = len(re.findall(r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content, re.MULTILINE))
    if count < AUTOSAVE_THRESHOLD:
        return

    existing_summary = read_memory_summary()
    existing_recent = ""
    recent_path = os.path.join(_ROOT, "memory", "recent-context.md")
    if os.path.isfile(recent_path):
        with open(recent_path, "r", encoding="utf-8") as f:
            existing_recent = f.read().strip()

    user_content = (
        f"Existing session-summary.md:\n{existing_summary}\n\n"
        f"Existing recent-context.md:\n{existing_recent}\n\n"
        f"Recent autosave entries:\n{content}"
    )
    raw = _call_claude(AUTOSAVE_COMPRESS_PROMPT, user_content, timeout=120)

    session_match = re.search(
        r"---SESSION-SUMMARY---\s*(.*?)(?=---RECENT-CONTEXT---|$)", raw, re.DOTALL
    )
    recent_match = re.search(r"---RECENT-CONTEXT---\s*(.*)", raw, re.DOTALL)

    if session_match:
        summary_path = os.path.join(_ROOT, "memory", "session-summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(session_match.group(1).strip())

    if recent_match:
        with open(recent_path, "w", encoding="utf-8") as f:
            f.write(recent_match.group(1).strip())

    entries = re.split(
        r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content, flags=re.MULTILINE
    )
    entries = [e for e in entries if e.strip()]
    with open(autosave_path, "w", encoding="utf-8") as f:
        f.write("\n".join(entries[-AUTOSAVE_KEEP:]).lstrip("\n") + "\n")

    reload_memory()
    console.print("[dim]Memory compressed.[/dim]")


def save_session_exit_summary() -> None:
    """On exit, summarize this session's autosave entries into current-focus.md
    and recent-context.md."""
    autosave_path = os.path.join(_ROOT, "memory", "autosave.md")
    if not os.path.isfile(autosave_path):
        return

    with open(autosave_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not re.search(r"^## \d{4}-\d{2}-\d{2}", content, re.MULTILINE):
        return

    try:
        raw = _call_claude(SESSION_EXIT_PROMPT, content, timeout=120)
        if not raw:
            return
    except Exception:
        return

    today = datetime.date.today().isoformat()
    focus_match = re.search(
        r"---CURRENT-FOCUS---\s*(.*?)(?=---RECENT-CONTEXT---|$)", raw, re.DOTALL
    )
    recent_match = re.search(r"---RECENT-CONTEXT---\s*(.*)", raw, re.DOTALL)

    if focus_match:
        focus_path = os.path.join(_ROOT, "memory", "current-focus.md")
        with open(focus_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Current Focus\n*Last updated: {today}*\n\n"
                + focus_match.group(1).strip()
                + "\n"
            )

    if recent_match:
        recent_path = os.path.join(_ROOT, "memory", "recent-context.md")
        with open(recent_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Recent Context\n*Last updated: {today}*\n\n"
                + recent_match.group(1).strip()
                + "\n"
            )

    console.print("[dim]Session summary saved.[/dim]")


def check_github_updates() -> bool:
    """Fetch origin/main, show any new commits, and ask before pulling.
    Re-runs setup.ps1 and reloads memory after a successful pull.
    Returns True if the repo was updated."""
    try:
        subprocess.run(
            ["git", "-C", _ROOT, "fetch", "origin", "main", "--quiet"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return False

    result = subprocess.run(
        ["git", "-C", _ROOT, "rev-list", "HEAD..origin/main", "--count"],
        capture_output=True, text=True,
    )
    try:
        behind_count = int(result.stdout.strip())
    except ValueError:
        return False

    if behind_count == 0:
        return False

    console.print(
        f"\n[bold yellow]Update available:[/bold yellow] "
        f"{behind_count} new commit(s) on origin/main."
    )
    log_result = subprocess.run(
        ["git", "-C", _ROOT, "log", "HEAD..origin/main", "--oneline"],
        capture_output=True, text=True,
    )
    if log_result.stdout.strip():
        console.print(f"[dim]{log_result.stdout.strip()}[/dim]")

    try:
        answer = console.input("[bold yellow]Pull and update? (y/n) > [/bold yellow]")
    except EOFError:
        return False

    if answer.strip().lower() not in {"y", "yes"}:
        console.print("[dim]Skipping update.[/dim]")
        return False

    pull_result = subprocess.run(
        ["git", "-C", _ROOT, "pull", "origin", "main"],
        capture_output=True, text=True,
    )
    if pull_result.returncode != 0:
        console.print(f"[bold red]Pull failed:[/bold red] {pull_result.stderr.strip()}")
        return False

    console.print("[bold green]Updated.[/bold green]")
    setup_path = os.path.join(_ROOT, "setup.ps1")
    if os.path.isfile(setup_path):
        console.print("[dim]Re-running setup.ps1 to apply new packages...[/dim]")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", setup_path]
        )
    reload_memory()
    return True


def check_and_offer_git_commit() -> None:
    """If memory, skills, routing manifests, or setup files changed this session,
    offer to commit and optionally push them."""
    watched_prefixes = (
        "memory/", "skills/", "requirements/", "plugins/",
        "setup.ps1", "run-alfred.bat", "backend/main.py",
    )
    result = subprocess.run(
        ["git", "-C", _ROOT, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return

    changed = []
    for line in result.stdout.splitlines():
        if len(line) > 3:
            filepath = line[3:].strip().replace("\\", "/")
            if any(filepath.startswith(p) or filepath == p for p in watched_prefixes):
                changed.append(filepath)

    if not changed:
        return

    console.print("\n[bold yellow]Files changed this session:[/bold yellow]")
    for f in changed:
        console.print(f"  [cyan]{f}[/cyan]")

    try:
        answer = console.input("[bold yellow]Commit these changes? (y/n) > [/bold yellow]")
    except EOFError:
        return

    if answer.strip().lower() not in {"y", "yes"}:
        console.print("[dim]Changes not committed.[/dim]")
        return

    for f in changed:
        subprocess.run(["git", "-C", _ROOT, "add", f], capture_output=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"Alfred autosave: memory/config update {timestamp}"
    commit_result = subprocess.run(
        ["git", "-C", _ROOT, "commit", "-m", msg],
        capture_output=True, text=True,
    )
    if commit_result.returncode != 0:
        console.print(f"[bold red]Commit failed:[/bold red] {commit_result.stderr.strip()}")
        return

    console.print(f"[bold green]Committed:[/bold green] {msg}")

    push_result = subprocess.run(
        ["git", "-C", _ROOT, "push", "origin", "main"],
        capture_output=True, text=True,
    )
    if push_result.returncode == 0:
        console.print("[bold green]Pushed to GitHub.[/bold green]")
    else:
        console.print(f"[bold yellow]Push skipped:[/bold yellow] {push_result.stderr.strip()[:120]}")


STOPWORDS = {
    "power", "query", "error", "errors", "issue", "issues",
    "data", "file", "files", "the", "and", "for", "not", "found",
}

COMPOUND_EXPANSIONS = {
    "powerquery": "power query",
    "powerbi": "power bi",
}

SKILL_MATCH_THRESHOLD = 2


def _build_skill_matchers(fname: str, content: str):
    raw_parts = fname[:-3].lower().split("-")
    expanded_parts = [COMPOUND_EXPANSIONS.get(p, p) for p in raw_parts]

    title_words = []
    for line in content.splitlines():
        text = line.lstrip("\\").lstrip("#").strip().lower()
        if text:
            title_words = re.findall(r"[a-z]+", text)
            break

    single_keywords = set()
    for part in expanded_parts:
        if " " not in part and part not in STOPWORDS and len(part) > 2:
            single_keywords.add(part)
    for word in title_words:
        if word not in STOPWORDS and len(word) > 2:
            single_keywords.add(word)

    strong_phrases = set()
    for part in expanded_parts:
        if " " in part:
            strong_phrases.add(part)
    for i in range(len(expanded_parts) - 1):
        strong_phrases.add(f"{expanded_parts[i]} {expanded_parts[i + 1]}")
    for i in range(len(expanded_parts) - 2):
        strong_phrases.add(
            f"{expanded_parts[i]} {expanded_parts[i + 1]} {expanded_parts[i + 2]}"
        )

    return single_keywords, strong_phrases


def load_relevant_skills(user_input: str) -> str:
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
    if not os.path.isdir(skills_dir):
        return ""

    lowered = user_input.lower()
    relevant = []

    for fname in sorted(os.listdir(skills_dir)):
        if not fname.endswith(".md"):
            continue

        skill_path = os.path.join(skills_dir, fname)
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()

        single_keywords, strong_phrases = _build_skill_matchers(fname, content)

        match_count = sum(1 for kw in single_keywords if kw in lowered)
        match_count += sum(1 for phrase in strong_phrases if phrase in lowered)

        if match_count >= SKILL_MATCH_THRESHOLD:
            relevant.append(f"--- Skill: {fname} ---\n{content}\n")
            console.print(f"[dim]Loaded skill: {fname}[/dim]")

    return "\n".join(relevant)


def generate_general_response(user_input: str, brain_says_search: bool = False) -> str:
    system = GENERAL_RESPONSE_PROMPT
    if _memory_context:
        system += f"\n\n## Project context\n{_memory_context}"

    # Build search-augmented content
    # Use Tavily if the brain flagged it OR if our local heuristic agrees
    content = user_input
    if brain_says_search or _should_search(user_input):
        results = _tavily_search(user_input)
        if results:
            console.print(f"[dim]Web search: {len(results)} result(s) found.[/dim]")
            snippets = "\n\n".join(
                f"[{r['title']}]({r['url']})\n{r['content']}"
                for r in results
            )
            content = (
                f"{user_input}\n\n"
                f"---\n"
                f"Live search results (use these to answer accurately):\n\n"
                f"{snippets}"
            )

    # Inject prior conversation turns as a transcript so claude -p has context
    if _chat_history:
        turns = []
        for msg in _chat_history:
            label = "User" if msg["role"] == "user" else "Alfred"
            turns.append(f"{label}: {msg['content']}")
        history_block = "\n\n".join(turns)
        system += f"\n\n## Conversation so far\n{history_block}"

    response = (
        _call_claude(system, content)
        or _call_openai(system, content, history=_chat_history)
        or "No response."
    )
    _append_to_history("user", user_input)
    _append_to_history("assistant", response)
    return response


def _build_execution_prompt(
    user_input: str,
    skills_context: str = "",
    search_context: str = "",
) -> str:
    """Build a context-rich execution prompt for Claude Code / Codex.

    Unlike generate_claude_scope(), this is pure string formatting — no extra LLM
    call required. Alfred's executor prompt sets the agent's behaviour; context
    blocks give it the information it needs to act accurately.
    """
    parts: list[str] = [ALFRED_EXECUTOR_PROMPT, f"\n## Task\n{user_input}"]

    if _memory_context:
        parts.append(f"\n## User context\n{_memory_context}")

    if search_context:
        parts.append(f"\n## Reference material (from live search)\n{search_context}")

    if skills_context:
        parts.append(f"\n## Relevant skills / how-to notes\n{skills_context}")

    if _chat_history:
        recent = _chat_history[-4:]
        turns = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Alfred'}: {m['content'][:200]}"
            for m in recent
        )
        parts.append(f"\n## Recent conversation\n{turns}")

    return "\n".join(parts)


def extract_structured_response(raw_response: str) -> dict:
    stripped = raw_response.strip()

    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    json_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return {
        "summary": raw_response,
        "root_cause": "",
        "recommended_next_step": "",
        "needs_user_approval": False,
    }


def run_claude(prompt: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a task through Claude Code CLI. Returns plain-text response — no JSON forcing."""
    exe = _resolve_claude_executable()
    # Write long prompts to a temp file to avoid Windows CLI length limits
    if len(prompt) > 6000:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(prompt)
            tmp_path = f.name
        try:
            args = ["powershell", "-NoProfile", "-Command",
                    f"Get-Content -Raw '{tmp_path}' | & '{exe}' -p -"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass
        return result
    else:
        args = [exe, "-p", prompt]
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(args, 1, "", f"Claude timed out after {timeout}s.")
        except FileNotFoundError:
            return subprocess.CompletedProcess(
                args, 127, "",
                "Claude Code CLI not found. Run: npm install -g @anthropic-ai/claude-code && claude login",
            )


_openai_disabled = False    # set True on auth failure so we don't retry every call
_anthropic_disabled = False  # same guard for direct Anthropic SDK path


def _call_anthropic(
    system_prompt: str,
    user_content: str,
    timeout: int = 60,
) -> str:
    """Call Anthropic API directly via Python SDK — no subprocess, no MCP init delay.
    Only active when ANTHROPIC_API_KEY is in .env. Falls back gracefully to subprocess path."""
    global _anthropic_disabled
    if _anthropic_disabled:
        return ""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            timeout=timeout,
        )
        return msg.content[0].text.strip()
    except ImportError:
        _anthropic_disabled = True  # package not installed — fall back silently
        return ""
    except Exception as exc:
        err = str(exc)
        if any(k in err for k in ("401", "authentication_error", "invalid_x_api_key")):
            _anthropic_disabled = True
            console.print("[dim red]Anthropic API key invalid — falling back to Claude CLI.[/dim red]")
        else:
            console.print(f"[dim red]Anthropic API: {err[:120]}[/dim red]")
        return ""


def _call_openai(
    system_prompt: str,
    user_content: str,
    model: str = "gpt-4o-mini",
    timeout: int = 60,
    history: "list[dict] | None" = None,
) -> str:
    """Call OpenAI API with the stored API key.
    Pass `history` to maintain multi-turn conversation context."""
    global _openai_disabled
    if _openai_disabled:
        return ""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_content})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=timeout,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "401" in err or "Incorrect API key" in err or "invalid_api_key" in err:
            _openai_disabled = True
            # OpenAI is optional — Claude is primary, no need to alarm the user
        else:
            console.print(f"[dim red]OpenAI: {err[:120]}[/dim red]")
        return ""


def _setup_openai_key() -> bool:
    """Guide the user to get and save their OpenAI API key."""
    console.print("\n[bold yellow]OpenAI API key not found.[/bold yellow]")
    console.print("Alfred uses GPT-4o-mini for fast classification and general chat.")
    console.print("\nGet your key at: [bold cyan]https://platform.openai.com/api-keys[/bold cyan]")
    try:
        ans = console.input("Open browser now? (y/n) > ")
        if ans.strip().lower() in {"y", "yes"}:
            webbrowser.open("https://platform.openai.com/api-keys")
        key = console.input("Paste your API key (sk-...): ").strip()
    except EOFError:
        return False

    if not key.startswith("sk-"):
        console.print("[bold red]Invalid key — must start with sk-[/bold red]")
        return False

    env_path = os.path.join(_ROOT, ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "OPENAI_API_KEY" in content:
            content = re.sub(r"OPENAI_API_KEY=.*", f"OPENAI_API_KEY={key}", content)
        else:
            content += f"\nOPENAI_API_KEY={key}\n"
    else:
        content = f"OPENAI_API_KEY={key}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

    os.environ["OPENAI_API_KEY"] = key
    global _openai_disabled
    _openai_disabled = False  # reset so next call tries the new key
    console.print("[bold green]API key saved to .env (stays on this PC only).[/bold green]")
    return True


def _resolve_claude_executable() -> str:
    return (
        os.getenv("CLAUDE_BIN")
        or shutil.which("claude.cmd")
        or shutil.which("claude")
        or "claude.cmd"
    )


def _resolve_codex_executable() -> str:
    return (
        os.getenv("CODEX_BIN")
        or shutil.which("codex.cmd")
        or shutil.which("codex")
        or "codex.cmd"
    )


def _extract_codex_response(jsonl_output: str) -> str:
    """Parse Codex --json JSONL output and return the agent response text.

    Codex emits one JSON object per line. We collect every agent_message text
    from item.completed events, which is the actual response from the model.
    """
    texts: list[str] = []
    for line in jsonl_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "item.completed":
                item = obj.get("item", {})
                if item.get("type") == "agent_message" and item.get("text"):
                    texts.append(item["text"])
        except (json.JSONDecodeError, KeyError):
            continue
    return "\n".join(texts)


def run_codex(prompt: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a prompt through Codex CLI using non-interactive exec mode.

    Uses `codex exec --json -` which reads the prompt from stdin and emits
    JSONL events — no TTY required, fully headless. Falls back to Claude Code
    only if the Codex executable is not found.
    """
    exe = _resolve_codex_executable()
    args = [exe, "exec", "--json", "-"]
    try:
        result = subprocess.run(
            args,
            input=prompt,            # pipe prompt via stdin — no TTY needed
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            # Extract clean response text from JSONL event stream
            response_text = _extract_codex_response(result.stdout)
            if response_text:
                return subprocess.CompletedProcess(args, 0, response_text, result.stderr)
        return result
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 1, "", f"Codex timed out after {timeout}s.")
    except FileNotFoundError:
        console.print("[dim]Codex CLI not found — falling back to Claude Code.[/dim]")
        return run_claude(prompt, timeout=timeout)


DANGEROUS_KEYWORDS = [
    "delete", "remove", "overwrite", "credentials", "password",
    "entire onedrive", "all folders", "whole workspace",
]

ACTION_KEYWORDS = ["inspect", "run", "edit", "use mcp", "use claude"]

# Keywords that suggest the user wants to teach Alfred a new rule, feature, or behavior
LEARNING_MODE_KEYWORDS = {
    "add a rule", "new rule", "add rule", "routing rule",
    "update alfred", "modify alfred", "change alfred", "teach alfred",
    "add to alfred", "add feature", "new feature",
    "add behavior", "update routing", "add routing",
    "update dispatch", "add dispatch",
    "save this rule", "remember this rule", "add this rule",
    "creator mode", "learning mode",
}

# Keywords that strongly suggest a repository coding task → route to Codex
CODEX_ROUTING_KEYWORDS = {
    "refactor", "refactoring", "unit test", "unit tests", "test suite",
    "code review", "review code", "repository", "repo", "function", "class",
    "method", "implement", "implementation", "write code", "fix bug",
    "bug fix", "debug code", "rename", "extract method", "lint", "linting",
    "pytest", "coverage", "docstring", "type hint", "typing", "import",
    "module", "package", "dependency", "tests pass",
    # Alfred self-modification and code-change tasks
    "alfred code", "alfred update", "update alfred",
    # App / UI / website / dashboard design
    "app design", "ui design", "web app", "web application",
    "website design", "dashboard design", "frontend",
    # Code cleanup and implementation tasks
    "code cleanup", "clean up", "dead code",
}

# Keywords that suggest MCP / file-system / execution tasks → route to Claude Code
CLAUDE_CODE_ROUTING_KEYWORDS = {
    "mcp", "inspect file", "read file", "execute", "run script",
    "power bi", "powerbi", "power query", "folder", "database", "scan",
    "filesystem", "file system", "workspace", "onedrive", "sharepoint",
    # Excel live editing via excellm MCP
    "excel", "spreadsheet", "workbook", "pivot table", "macro", "vba",
    # Office mastery
    "word document", "document", "docx", "report", "proposal",
    "powerpoint", "presentation", "slide deck", "pptx", "pdf",
    # Repository/file exploration and deep tool use
    "explore", "file exploration", "repository exploration", "deep tool",
    # Browser automation via Playwright MCP
    "playwright", "navigate to http", "browser automation",
    "web scrape", "scrape the", "take a screenshot of", "open the browser",
    # GitHub operations via GitHub MCP
    "pull request", "create pr", "create a pr", "open pr",
    "github issue", "open issue", "create issue", "review pr",
    "github.com", "merge pr", "push to github",
}

# Keywords that suggest the query needs live web data — trigger Tavily search
SEARCH_TRIGGER_KEYWORDS = {
    # Recency / time
    "latest", "newest", "current", "recent", "today", "right now",
    "this week", "this month", "this year",
    "2024", "2025", "2026",
    # Explicit lookup intent
    "search for", "search the web", "look up", "find out", "find me",
    "what is the price", "how much does", "price of", "cost of",
    # Version / release queries
    "latest version", "new version", "version of", "release of",
    "what version", "current version", "just released", "just launched",
    # News / events
    "news about", "what happened", "recently announced", "just announced",
    # General knowledge gaps
    "who is", "what is", "where is", "when did", "how does",
}


# ── Alfred Capability Registry ────────────────────────────────────────────────
# Single source of truth: visible in Control Tower, injected into the Brain prompt.

ALFRED_CAPABILITY_REGISTRY = [
    {
        "name": "General Chat",
        "provider": "claude",
        "category": "GENERAL",
        "description": "Natural conversation, explanations, brainstorming, analysis",
        "requires": "claude_cli",
    },
    {
        "name": "Web Research",
        "provider": "tavily",
        "category": "SEARCH",
        "description": "Live data — news, prices, versions, documentation, current events",
        "requires": "tavily_key",
    },
    {
        "name": "Code & Refactoring",
        "provider": "codex",
        "category": "CODE",
        "description": "Write, fix, refactor, test code in any language",
        "requires": "codex_cli",
    },
    {
        "name": "File & System Operations",
        "provider": "claude_code",
        "category": "EXECUTE",
        "description": "Read/write files, run scripts, inspect directories, execute commands",
        "requires": "claude_cli",
    },
    {
        "name": "Excel Automation",
        "provider": "claude_code",
        "category": "EXECUTE",
        "description": "Live workbook editing — formulas, pivot tables, charts, VBA",
        "requires": "mcp_excel",
    },
    {
        "name": "Power BI",
        "provider": "claude_code",
        "category": "POWERBI",
        "description": "DAX, model editing, relationships, visuals, Power Query diagnosis",
        "requires": "mcp_powerbi",
    },
    {
        "name": "Browser Automation",
        "provider": "claude_code",
        "category": "EXECUTE",
        "description": "Navigate websites, fill forms, scrape data, take screenshots",
        "requires": "mcp_playwright",
    },
    {
        "name": "GitHub Operations",
        "provider": "claude_code",
        "category": "EXECUTE",
        "description": "PRs, issues, diffs, commits, branches, repo management",
        "requires": "mcp_github",
    },
    {
        "name": "Office Documents",
        "provider": "claude_code",
        "category": "EXECUTE",
        "description": "Word reports, PowerPoint decks, PDF extraction via python-docx/pptx",
        "requires": "claude_cli",
    },
]

_CAPABILITY_REQUIRES_LABELS = {
    "claude_cli":     "Claude CLI",
    "codex_cli":      "Codex CLI",
    "tavily_key":     "Tavily API key",
    "mcp_excel":      "Excel MCP",
    "mcp_powerbi":    "Power BI MCP",
    "mcp_playwright": "Playwright MCP",
    "mcp_github":     "GitHub MCP",
}

# ── Tool Registry ─────────────────────────────────────────────────────────────
# Single source of truth for what Alfred can do.
# Add new tools here or call register_tool() from a plugin.
# Powers: /tools display, brain prompt context, routing hints.

TOOL_REGISTRY: dict[str, dict] = {
    "chat": {
        "name": "Chat & Research",
        "description": "Conversation, explanations, brainstorming, analysis",
        "category": "GENERAL",
        "provider": "claude",
        "requires": "claude_api",
        "keywords": [],
        "examples": ["explain this", "what does X mean", "help me think through"],
    },
    "search": {
        "name": "Web Search",
        "description": "Live data — news, prices, docs, current events",
        "category": "SEARCH",
        "provider": "claude",
        "requires": "tavily_key",
        "keywords": ["latest", "current", "news", "price", "version", "today"],
        "examples": ["what's the latest Python version", "price of", "news about"],
    },
    "files": {
        "name": "Files & System",
        "description": "Read, write, organise files and folders on this PC",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "claude_cli",
        "keywords": ["file", "folder", "directory", "read", "write", "organise", "organize", "find file"],
        "examples": ["find my wages report", "organise this folder", "read this file"],
    },
    "code": {
        "name": "Code",
        "description": "Write, fix, refactor, test code in any language",
        "category": "CODE",
        "provider": "claude_code",
        "requires": "claude_cli",
        "keywords": ["code", "function", "bug", "test", "refactor", "script", "write a", "fix this"],
        "examples": ["fix this bug", "write a Python script to", "refactor this function"],
    },
    "excel": {
        "name": "Excel",
        "description": "Live workbook automation — formulas, pivot tables, charts, VBA",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_excel",
        "keywords": ["excel", "spreadsheet", "workbook", "pivot", "chart", "formula", "vba", "macro"],
        "examples": ["check my Excel file", "add a pivot table", "update the formula in"],
    },
    "powerbi": {
        "name": "Power BI",
        "description": "DAX, model editing, relationships, visuals, Power Query",
        "category": "POWERBI",
        "provider": "claude_code",
        "requires": "mcp_powerbi",
        "keywords": ["power bi", "powerbi", "dax", "power query", "visual", "report", "measure"],
        "examples": ["check my DAX measure", "why is Derrimut showing wrong", "add a measure for"],
    },
    "browser": {
        "name": "Browser",
        "description": "Navigate websites, fill forms, scrape data, take screenshots",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_playwright",
        "keywords": ["browser", "website", "navigate", "scrape", "screenshot", "open", "go to"],
        "examples": ["open the website", "screenshot of", "scrape the table from"],
    },
    "github": {
        "name": "GitHub",
        "description": "PRs, issues, code review, commits, branches",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_github",
        "keywords": ["github", "pr", "pull request", "issue", "commit", "branch", "merge"],
        "examples": ["create a PR", "check my open issues", "review this diff"],
    },
    "office": {
        "name": "Office Documents",
        "description": "Word reports, PowerPoint decks, PDF extraction",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "claude_cli",
        "keywords": ["word", "powerpoint", "pdf", "document", "presentation", "report", "docx", "pptx"],
        "examples": ["create a Word report", "build a PowerPoint from", "extract from this PDF"],
    },
}


def register_tool(
    key: str,
    name: str,
    description: str,
    category: str,
    provider: str,
    requires: str,
    keywords: "list[str] | None" = None,
    examples: "list[str] | None" = None,
) -> None:
    """Register a new capability in Alfred's tool registry.

    Call this from a plugin or skill file to make a new tool discoverable.
    The tool will appear in /tools, Control Tower, and influence routing.

    Args:
        key:         Unique identifier, e.g. "my_tool"
        name:        Display name, e.g. "My Custom Tool"
        description: One-line description of what it does
        category:    "GENERAL" | "SEARCH" | "EXECUTE" | "CODE" | "POWERBI"
        provider:    "claude" | "claude_code"
        requires:    Dependency key: "claude_cli" | "tavily_key" | "mcp_excel" | etc.
        keywords:    Trigger words for routing hints (optional)
        examples:    Example phrasings the user might type (optional)
    """
    TOOL_REGISTRY[key] = {
        "name": name,
        "description": description,
        "category": category,
        "provider": provider,
        "requires": requires,
        "keywords": keywords or [],
        "examples": examples or [],
    }


def _tool_registry_status(tool: dict) -> tuple[str, str]:
    """Return (status, note) for a tool based on what's installed."""
    req = tool.get("requires", "")
    # Re-use existing capability check logic
    dummy_cap = {"requires": req}
    return _capability_status(dummy_cap)


def _capability_status(cap: dict) -> tuple[str, str]:
    """Return (status, note) for a capability based on what's installed/configured."""
    req = cap.get("requires", "")
    if req == "claude_cli":
        ok = bool(shutil.which("claude.cmd") or shutil.which("claude"))
        return ("ready", "") if ok else ("attention", "claude not installed")
    if req == "codex_cli":
        ok = bool(shutil.which("codex.cmd") or shutil.which("codex"))
        return ("ready", "") if ok else ("attention", "codex not installed")
    if req == "tavily_key":
        ok = bool(_get_tavily_api_key())
        return ("ready", "") if ok else ("attention", "TAVILY_API_KEY missing")
    if req == "mcp_excel":
        mcp = _load_mcp_servers()
        return ("ready", "") if "excel" in mcp else ("planned", "Excel MCP not configured")
    if req == "mcp_powerbi":
        mcp = _load_mcp_servers()
        return ("ready", "") if "powerbi-modeling-mcp" in mcp else ("planned", "Power BI MCP not configured")
    if req == "mcp_playwright":
        mcp = _load_mcp_servers()
        return ("ready", "") if "playwright" in mcp else ("planned", "Playwright MCP not configured")
    if req == "mcp_github":
        mcp = _load_mcp_servers()
        return ("ready", "") if "github" in mcp else ("planned", "GitHub MCP not configured")
    return ("ready", "")


# ── Alfred Brain ───────────────────────────────────────────────────────────────

ALFRED_BRAIN_PROMPT = """
You are Alfred's routing brain. Given the user's request, return a routing decision as compact JSON.

Alfred is a personal AI assistant with these capabilities:
- GENERAL: conversation, explanations, definitions, brainstorming — Claude replies directly
- SEARCH: questions needing live/current data (prices, news, latest versions, current events) — Tavily + Claude
- CODE: write/fix/refactor/review code, tests, scripts — Claude Code
- EXECUTE: act on files, PC, apps, external services (Excel, browser, GitHub, Office docs, scripts) — Claude Code + MCP
- POWERBI: Power BI model, DAX queries, Power Query, visuals — Claude Code + Power BI MCP

Provider assignment rules:
- "claude": GENERAL and SEARCH (conversation and research only, no tool use)
- "claude_code": CODE, EXECUTE, and POWERBI tasks (anything requiring files, MCP tools, or system access)

Return ONLY compact JSON — no markdown fences, no explanation:
{"category":"GENERAL|SEARCH|CODE|EXECUTE|POWERBI","provider":"claude|claude_code","needs_search":false,"needs_clarification":false,"clarification_question":"","plan":"","steps":[]}

Rules:
- needs_search=true for SEARCH category, and for GENERAL questions about current events, prices, latest versions, or recent news
- needs_clarification=true only when a required target (file, workbook, URL, etc.) is genuinely ambiguous and cannot be inferred
- clarification_question should be a short, specific question — or empty string if needs_clarification is false
- plan is a one-sentence plain-English summary of what will be done for CODE/EXECUTE/POWERBI, empty for GENERAL/SEARCH
- steps: array of 2–5 short action strings for compound requests; empty array [] for single-action tasks or GENERAL/SEARCH
"""


def alfred_brain(user_input: str) -> dict:
    """Single LLM call: classify intent, select provider, optionally plan.
    Falls back to keyword-based routing if Claude is unavailable or returns bad JSON."""
    # Build context block so the brain isn't blind to recent conversation
    context_block = ""
    if _memory_context:
        context_block += f"\n\n## Project context\n{_memory_context}"
    if _chat_history:
        recent = _chat_history[-6:]  # last 3 turns (user + assistant pairs)
        turns = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Alfred'}: {m['content'][:250]}"
            for m in recent
        )
        context_block += f"\n\n## Recent conversation\n{turns}"

    raw = _call_claude(ALFRED_BRAIN_PROMPT, user_input + context_block)
    if raw:
        decision = extract_structured_response(raw)
        category = decision.get("category", "").upper()
        provider = decision.get("provider", "")
        valid_categories = {"GENERAL", "SEARCH", "CODE", "EXECUTE", "POWERBI"}
        valid_providers = {"claude", "claude_code"}
        # Normalise: brain sometimes returns "codex" — remap to claude_code
        if provider == "codex":
            provider = "claude_code"
        if category in valid_categories and provider in valid_providers:
            decision["category"] = category
            return decision

    # Pure keyword fallback — no LLM required
    lowered = user_input.lower()
    if any(kw in lowered for kw in ["power bi", "powerbi", "dax", "power query"]):
        return {
            "category": "POWERBI", "provider": "claude_code",
            "needs_search": False, "needs_clarification": False,
            "clarification_question": "", "plan": "",
        }
    codex_score = sum(1 for kw in CODEX_ROUTING_KEYWORDS if kw in lowered)
    claude_score = sum(1 for kw in CLAUDE_CODE_ROUTING_KEYWORDS if kw in lowered)
    if codex_score > 0 or claude_score > 0:
        prov = "codex" if codex_score >= claude_score else "claude_code"
        cat = "CODE" if prov == "codex" else "EXECUTE"
        return {
            "category": cat, "provider": prov,
            "needs_search": False, "needs_clarification": False,
            "clarification_question": "", "plan": "",
        }
    return {
        "category": "GENERAL", "provider": "claude",
        "needs_search": _should_search(user_input), "needs_clarification": False,
        "clarification_question": "", "plan": "",
    }


def _should_search(query: str) -> bool:
    """Return True if this query likely benefits from live web context.
    Intentionally broad — Tavily's free tier covers ~1,000 requests/month."""
    lowered = query.lower().strip()
    # Skip meta / navigation commands
    if lowered in {"back", "menu", "home", "exit", "help", "clip", "paste", "done"}:
        return False
    if len(lowered) < 8:
        return False
    # Question-pattern prefix → almost always an informational request
    if any(lowered.startswith(w) for w in (
        "what ", "who ", "when ", "where ", "why ", "how ", "is ", "are ",
        "was ", "were ", "tell me", "explain", "describe", "show me",
        "find ", "search ", "look up",
    )):
        return True
    # Explicit question mark → user is asking something
    if "?" in lowered:
        return True
    # Original keyword safety-net
    return any(kw in lowered for kw in SEARCH_TRIGGER_KEYWORDS)


def _get_tavily_api_key() -> str:
    """Read Tavily API key from env or .claude/settings.json."""
    key = os.getenv("TAVILY_API_KEY", "")
    if key:
        return key
    settings_path = os.path.join(_ROOT, ".claude", "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return (
                cfg.get("mcpServers", {})
                .get("tavily", {})
                .get("env", {})
                .get("TAVILY_API_KEY", "")
            )
        except Exception:
            pass
    return ""


def _tavily_search(query: str, max_results: int = 5) -> list:
    """AI-optimised search via Tavily — returns [{title, url, content}] or [].
    Returns [] silently if no TAVILY_API_KEY is configured."""
    api_key = _get_tavily_api_key()
    if not api_key:
        return []

    body = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [
            {
                "title": r.get("title", ""),
                "url":   r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in data.get("results", [])
            if r.get("content")
        ]
    except urllib.error.HTTPError as e:
        if e.code == 401:
            console.print("[dim yellow]Tavily Search: invalid API key.[/dim yellow]")
        else:
            console.print(f"[dim red]Tavily Search: HTTP {e.code}[/dim red]")
        return []
    except Exception as e:
        console.print(f"[dim red]Tavily Search: {e}[/dim red]")
        return []


PROVIDER_OVERRIDE_RE = re.compile(
    r"(?i)^\s*(?:please\s+)?(?:use|with|via|ask)\s+"
    r"(claude(?:[\s_-]+code)?|codex)\b"
    r"\s*(?:(?:to|for)\s+)?[:,\-]?\s*"
)


def detect_provider_override(user_input: str) -> "str | None":
    """Return an explicit provider override from a leading routing directive."""
    match = PROVIDER_OVERRIDE_RE.match(user_input)
    if not match:
        return None
    provider = match.group(1).lower().replace("-", " ").replace("_", " ")
    if provider.startswith("claude"):
        return "claude_code"
    if provider == "codex":
        return "codex"
    return None


def strip_provider_prefix(user_input: str) -> str:
    """Remove the provider directive from the input before passing to the AI."""
    return PROVIDER_OVERRIDE_RE.sub("", user_input, count=1).strip()


def is_learning_mode_task(user_input: str) -> bool:
    lowered = user_input.lower()
    return any(kw in lowered for kw in LEARNING_MODE_KEYWORDS)


def generate_learning_discussion(user_input: str) -> str:
    system = LEARNING_DISCUSSION_PROMPT
    if _memory_context:
        system += f"\n\n## Current project context\n{_memory_context}"
    return _call_claude(system, user_input) or _call_openai(system, user_input) or "No response."


# ── Display helpers ────────────────────────────────────────────────────────────

PROVIDER_COLORS = {
    "claude_code": "bold green",
    "codex": "bold blue",
    "claude": "bold cyan",
    "openai_mini": "bold cyan",   # legacy alias → Claude
}

PROVIDER_LABELS = {
    "claude_code": "Claude Code",
    "codex": "Codex",
    "claude": "Claude",
    "openai_mini": "Claude",      # legacy alias → Claude
}


def _notify(title: str, message: str) -> None:
    """Show a Windows toast notification — silent no-op if winotify is unavailable."""
    try:
        from winotify import Notification
        toast = Notification(
            app_id="Alfred Console",
            title=title,
            msg=message,
            duration="short",
        )
        toast.show()
    except Exception:
        pass


def _render_provider_result(
    provider: str, category: str, result: subprocess.CompletedProcess
) -> None:
    """Legacy display helper — delegates to the unified execution renderer."""
    _render_execution_result(result)


def _render_claude_result(result: subprocess.CompletedProcess) -> None:
    """Legacy display helper — delegates to the unified execution renderer."""
    _render_execution_result(result)


def _render_general_response(response: str) -> None:
    """Render a conversational response — no panel border, just text like a chat assistant."""
    console.print()
    console.print(Markdown(response))
    console.print()


def _show_startup_memory() -> None:
    """Show a brief memory briefing at startup — only if meaningful content exists."""
    focus_path = os.path.join(_ROOT, "memory", "current-focus.md")
    if not os.path.isfile(focus_path):
        return
    try:
        with open(focus_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return
    if not content or any(m in content for m in _MEMORY_DEFAULT_MARKERS):
        return
    bullets = [
        ln.strip() for ln in content.splitlines()
        if ln.strip().startswith(("- ", "* ", "• "))
    ][:3]
    if not bullets:
        return
    console.print(
        Panel(
            Markdown("\n".join(bullets)),
            title="[bold dim]Last session[/bold dim]",
            border_style="dim",
            padding=(0, 2),
        )
    )


def _show_header() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Alfred[/bold cyan]  [dim]v2[/dim]\n"
            "[dim]Your personal AI assistant — just talk to me naturally.[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _show_menu() -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Opt", style="bold yellow", no_wrap=True)
    t.add_column("Action", style="white")
    t.add_row("1", "Ask Alfred")
    t.add_row("2", "Control Tower")
    t.add_row("3", "View Skills")
    t.add_row("4", "Platforms")
    t.add_row("5", "Dev Portal")
    t.add_row("6", "Plugins")
    t.add_row("7", "Publish Update")
    t.add_row("8", "Exit")
    console.print(t)
    console.print("[dim]Type [bold]HOME[/bold] at any prompt to return here.[/dim]")


# ── Menu actions ───────────────────────────────────────────────────────────────

def get_clipboard_text() -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Get-Clipboard failed")
    return result.stdout.strip()


def _render_step_plan(steps: list) -> None:
    """Show a numbered step list conversationally before asking for confirmation."""
    lines = [f"**{i}.** {step}" for i, step in enumerate(steps, 1)]
    console.print()
    console.print("[bold cyan]Here's what I'll do:[/bold cyan]")
    console.print(Markdown("\n".join(lines)))
    console.print()


def _friendly_error(stderr: str) -> str:
    """Translate raw CLI error text into a plain-English explanation with a next step."""
    raw = stderr.strip()
    low = raw.lower()

    if "not found" in low and ("claude" in low or "command" in low):
        return (
            "I couldn't find the Claude CLI on this machine.\n\n"
            "**Fix:** Open a terminal and run:\n"
            "```\nnpm install -g @anthropic-ai/claude-code\nclaude login\n```"
        )
    if "timed out" in low:
        return (
            "The task took too long and I had to stop it.\n\n"
            "**Try:** Break it into smaller steps, or check your internet connection."
        )
    if "authentication" in low or "login" in low or "401" in low:
        return (
            "There's an authentication issue — I'm not signed in to that service.\n\n"
            "**Fix:** Run `claude login` (or `codex login`) in a terminal, then try again."
        )
    if "permission" in low or "access denied" in low:
        return (
            "I don't have permission to access that file or folder.\n\n"
            "**Try:** Check the file isn't locked by another app, or run Alfred as the file's owner."
        )
    if raw:
        # Show a trimmed version of the raw error as a fallback, with context
        trimmed = raw[:300] + ("…" if len(raw) > 300 else "")
        return f"Something went wrong:\n\n```\n{trimmed}\n```\n\n**Try:** Rephrase the request or check the file exists."
    return "Something went wrong, but there was no error message. Try rephrasing the request."


def _render_execution_result(result: subprocess.CompletedProcess) -> None:
    """Show execution result as a friendly chat-style message.

    Renders whatever the model returned — plain text, Markdown, or structured
    JSON (legacy Codex format). No assumptions about output format.
    """
    if result.returncode != 0:
        msg = _friendly_error(result.stderr)
        console.print()
        console.print(Markdown(msg))
        console.print()
        return

    output = result.stdout.strip()
    if not output:
        console.print("[dim]Done — no output returned.[/dim]")
        return

    # Try legacy JSON structure (Codex used to return this) — fall back to raw text
    structured = extract_structured_response(output)
    if (
        isinstance(structured, dict)
        and structured.get("summary")
        and not structured.get("summary") == output  # don't loop if summary == raw
    ):
        parts: list[str] = [structured["summary"]]
        if structured.get("recommended_next_step"):
            parts.append(f"\n**Next:** {structured['recommended_next_step']}")
        if structured.get("needs_user_approval"):
            parts.append("\n*Let me know if you want me to continue.*")
        body = "\n".join(parts)
    else:
        body = output

    console.print()
    console.print(Markdown(body))
    console.print()


def _run_step_sequence(
    original_request: str,
    steps: list,
    provider: str,
    skills_context: str,
    search_context: str,
) -> str:
    """Execute a compound task step-by-step, accumulating context between steps.
    Returns a short outcome summary string."""
    total = len(steps)
    all_outcomes: list[str] = []

    for i, step in enumerate(steps, 1):
        console.print(f"\n[dim]Step {i} of {total} — {step}[/dim]")

        prior = ""
        if all_outcomes:
            prior = "\n\nPrior steps completed:\n" + "\n".join(
                f"  {j}. {o}" for j, o in enumerate(all_outcomes, 1)
            )

        step_prompt = (
            f"Multi-step task — step {i} of {total}.\n\n"
            f"Full original request: {original_request}\n\n"
            f"Current step ({i}/{total}): {step}"
            + prior
        )
        scope = _build_execution_prompt(step_prompt, skills_context, search_context)

        with console.status(f"[dim]Step {i} of {total}…[/dim]", spinner="dots"):
            result = run_codex(scope) if provider == "codex" else run_claude(scope)
        _render_execution_result(result)

        if result.returncode != 0:
            if i < total:
                try:
                    cont = console.input(
                        f"[bold yellow]That step ran into a problem — want me to keep going? (y/n) > [/bold yellow]"
                    ).strip().lower()
                except EOFError:
                    cont = "n"
                if cont not in {"y", "yes"}:
                    console.print("[dim]Stopped. Let me know if you'd like to try a different approach.[/dim]")
                    return f"Stopped at step {i}/{total}"
            all_outcomes.append(f"failed — {result.stderr[:80]}")
        else:
            structured = extract_structured_response(result.stdout)
            outcome = structured.get("summary", "") or result.stdout.strip()[:120]
            all_outcomes.append(outcome)

            if structured.get("needs_user_approval") and i < total:
                try:
                    cont = console.input(
                        "[bold yellow]Ready for the next step — shall I continue? (y/n) > [/bold yellow]"
                    ).strip().lower()
                except EOFError:
                    cont = "n"
                if cont not in {"y", "yes"}:
                    console.print("[dim]Paused. Just say 'continue' when you're ready.[/dim]")
                    return f"Paused at step {i}/{total}"

    # All steps done — show a plain summary
    console.print()
    console.print("[bold green]All done.[/bold green]")
    summary_lines = [f"**{j}.** {o}" for j, o in enumerate(all_outcomes, 1)]
    console.print(Markdown("\n".join(summary_lines)))
    console.print()
    _notify("Alfred", f"Done — {total} steps completed")
    return f"Completed {total} steps"


def _process_alfred_request(
    stripped: str,
    force_learning: bool = False,
    provider_override: "str | None" = None,
) -> bool:
    scope = ""
    outcome = ""
    steps: list = []
    needs_search = False
    decision: dict = {}  # brain decision — kept as reference for plan summary display

    # Explicit provider override — skip Brain and learning check
    if provider_override:
        category = "CLAUDE_EXECUTION"
        provider = provider_override

    # Dev Portal forces the guarded learning flow even for plain-language notes.
    elif force_learning or is_learning_mode_task(stripped):
        console.print("\n[dim]Learning / Creator Mode - discussing before routing.[/dim]")
        discussion = generate_learning_discussion(stripped)
        _render_general_response(discussion)
        try:
            confirm = console.input(
                "\n[bold yellow]Want me to go ahead with this? (y/n) > [/bold yellow]"
            )
        except EOFError:
            return False
        if confirm.strip().lower() not in {"y", "yes"}:
            console.print("[dim]No problem — nothing was changed.[/dim]")
            append_interaction_log(stripped, "LEARNING_DECLINED", "", "openai_mini")
            append_autosave_entry(
                stripped, "LEARNING_DECLINED", "openai_mini", "Request declined by user"
            )
            compress_autosave_if_needed()
            return True
        console.print("[dim]Confirmed. Proceeding with routing...[/dim]")
        category = "CLAUDE_EXECUTION"
        provider = "codex"

    else:
        # ── Alfred Brain: one call to classify, route, and optionally plan ──
        decision = alfred_brain(stripped)
        brain_category = decision.get("category", "GENERAL")
        provider = decision.get("provider", "claude")
        needs_search = bool(decision.get("needs_search", False))

        # Extract multi-step plan — only for compound EXECUTE/CODE/POWERBI tasks
        raw_steps = decision.get("steps", [])
        if (
            isinstance(raw_steps, list)
            and len(raw_steps) >= 2
            and brain_category in {"CODE", "EXECUTE", "POWERBI"}
        ):
            steps = [str(s) for s in raw_steps if s]

        # Mid-task clarification: ask before doing anything
        if decision.get("needs_clarification") and decision.get("clarification_question"):
            q = decision["clarification_question"]
            console.print(f"\n[bold cyan]Alfred:[/bold cyan] {q}")
            try:
                answer = console.input("[bold yellow]> [/bold yellow]").strip()
            except EOFError:
                return False
            if answer and answer.lower() not in {"back", "skip", "exit", "cancel"}:
                stripped = f"{stripped}\n\nContext provided: {answer}"

        # Normalise provider — brain may still return "codex" or "quant" from old sessions
        if provider in {"codex", "quant"}:
            provider = "claude_code"

        # Map Brain categories → pipeline categories (backward-compatible)
        category = {
            "GENERAL": "GENERAL",
            "SEARCH":  "GENERAL",   # search-augmented chat
            "CODE":    "CLAUDE_EXECUTION",
            "EXECUTE": "CLAUDE_EXECUTION",
            "POWERBI": "POWERBI",
        }.get(brain_category, "GENERAL")

    _YES_TOKENS = {"y", "yes", "ok", "okay", "sure", "go", "go ahead", "yep", ""}

    if category == "GENERAL":
        response = generate_general_response(stripped, brain_says_search=needs_search)
        _render_general_response(response)
        outcome = response[:200]

    elif category in ["POWERBI", "CLAUDE_EXECUTION"]:
        # ── Pre-fetch context ────────────────────────────────────────────────
        search_context = ""
        if needs_search:
            search_results = _tavily_search(stripped, max_results=3)
            if search_results:
                search_context = "\n\n".join(
                    f"[{r['title']}]({r['url']})\n{r['content'][:600]}"
                    for r in search_results
                )
        skills_context = load_relevant_skills(stripped)

        # ── Show what Alfred intends to do ───────────────────────────────────
        plan_line = decision.get("plan", "").strip() if isinstance(decision, dict) else ""

        if steps:
            _render_step_plan(steps)
        elif plan_line:
            console.print(f"\n[dim]→ {plan_line}[/dim]")

        # ── Permission layer: stronger confirmation for destructive operations ─
        is_destructive = any(kw in stripped.lower() for kw in DANGEROUS_KEYWORDS)
        if is_destructive:
            console.print(
                "[bold yellow]⚠  This may modify or delete something.[/bold yellow] "
                "Type [bold]yes[/bold] to confirm, anything else to cancel."
            )
            try:
                confirm = console.input("[bold red]Confirm > [/bold red]").strip().lower()
            except EOFError:
                confirm = ""
            if confirm != "yes":
                console.print("[dim]Cancelled — nothing was changed.[/dim]")
                append_interaction_log(stripped, category, "", provider)
                append_autosave_entry(stripped, category, provider, "Cancelled (destructive guard)")
                compress_autosave_if_needed()
                return True
        else:
            try:
                confirm = console.input(
                    "\n[bold yellow]Sound good? Press Enter to go ahead, or describe any changes > [/bold yellow]"
                ).strip()
            except EOFError:
                confirm = ""

            if confirm.lower() in {"n", "no", "cancel", "back", "stop"}:
                console.print("[dim]No problem — let me know if you'd like to try something different.[/dim]")
                append_interaction_log(stripped, category, "", provider)
                append_autosave_entry(stripped, category, provider, "Cancelled by user")
                compress_autosave_if_needed()
                return True

            if confirm and confirm.lower() not in _YES_TOKENS:
                # User described a change — incorporate it
                stripped = f"{stripped}\n\nAdjustment: {confirm}"
                adj = alfred_brain(stripped)
                adj_steps = adj.get("steps", [])
                if isinstance(adj_steps, list) and len(adj_steps) >= 2:
                    steps = [str(s) for s in adj_steps if s]
                    _render_step_plan(steps)
                adj_plan = adj.get("plan", "").strip()
                if adj_plan and not steps:
                    console.print(f"\n[dim]→ {adj_plan}[/dim]")

        # ── Execute ──────────────────────────────────────────────────────────
        if steps:
            outcome = _run_step_sequence(stripped, steps, provider, skills_context, search_context)
        else:
            exec_prompt = _build_execution_prompt(stripped, skills_context, search_context)
            with console.status("[dim]Working…[/dim]", spinner="dots"):
                result = run_codex(exec_prompt) if provider == "codex" else run_claude(exec_prompt)
            _render_execution_result(result)
            _notify("Alfred", "Task " + ("complete" if result.returncode == 0 else "failed"))
            outcome = (
                result.stdout[:200]
                if result.returncode == 0
                else f"Error: {result.stderr[:100]}"
            )

    append_interaction_log(stripped, category, scope, provider)
    append_autosave_entry(stripped, category, provider, outcome)
    compress_autosave_if_needed()
    return True


def _handle_pq_command(raw: str) -> None:
    """Handle `pq` Power Query shortcuts directly from the Alfred prompt.

    Commands:
      pq                        — list all queries in the active workbook
      pq list [workbook]        — same, optional workbook name filter
      pq show <query>           — display M expression for a query
      pq refresh                — refresh all queries
      pq refresh <query>        — refresh a single query
      pq edit <query>           — fetch M expression then prompt for changes via Alfred Brain
    """
    parts = raw.strip().split(None, 2)           # ["pq", sub-cmd?, args?]
    sub = parts[1].lower() if len(parts) >= 2 else "list"
    arg = parts[2].strip() if len(parts) >= 3 else ""

    # ── pq list ──────────────────────────────────────────────────────────────
    if sub in {"list", "queries", "ls"}:
        result = pq_helper.list_queries(arg or None)
        if not result["success"]:
            console.print(f"[bold red]Power Query:[/bold red] {result['error']}")
            return
        qs = result["queries"]
        if not qs:
            console.print(f"[dim]No Power Query queries found in '{result['workbook']}'.[/dim]")
            return
        tbl = Table(title=f"Power Query — {result['workbook']}", box=box.SIMPLE_HEAVY, show_lines=False)
        tbl.add_column("Query", style="bold cyan", no_wrap=True)
        tbl.add_column("Description", style="dim")
        for q in qs:
            tbl.add_row(q["name"], q.get("description", ""))
        console.print(tbl)
        console.print("[dim]  pq show <name>  |  pq refresh <name>  |  pq edit <name>[/dim]")
        return

    # ── pq show ───────────────────────────────────────────────────────────────
    if sub == "show":
        if not arg:
            console.print("[bold red]Usage:[/bold red] pq show <query name>")
            return
        result = pq_helper.get_query(arg)
        if not result["success"]:
            console.print(f"[bold red]Power Query:[/bold red] {result['error']}")
            return
        console.print(
            Panel(
                result["formula"],
                title=f"[bold cyan]{result['name']}[/bold cyan]  [dim]({result['workbook']})[/dim]",
                border_style="cyan",
                padding=(0, 2),
            )
        )
        return

    # ── pq refresh ────────────────────────────────────────────────────────────
    if sub == "refresh":
        result = pq_helper.refresh_query(arg or None)
        if not result["success"]:
            console.print(f"[bold red]Power Query:[/bold red] {result['error']}")
            return
        names = ", ".join(result["refreshed"])
        console.print(f"[dim]Refreshed: {names}[/dim]")
        if result.get("warnings"):
            for w in result["warnings"]:
                console.print(f"[bold yellow]  Warning:[/bold yellow] {w}")
        return

    # ── pq edit ───────────────────────────────────────────────────────────────
    if sub == "edit":
        if not arg:
            console.print("[bold red]Usage:[/bold red] pq edit <query name>")
            return
        result = pq_helper.get_query(arg)
        if not result["success"]:
            console.print(f"[bold red]Power Query:[/bold red] {result['error']}")
            return
        console.print(
            Panel(
                result["formula"],
                title=f"[bold cyan]{result['name']}[/bold cyan] — current M expression",
                border_style="cyan",
                padding=(0, 2),
            )
        )
        console.print("[dim]Describe the change you want, or paste replacement M. Type [bold]cancel[/bold] to abort.[/dim]")
        try:
            change_request = console.input("[bold yellow]Edit > [/bold yellow]").strip()
        except EOFError:
            return
        if not change_request or change_request.lower() == "cancel":
            console.print("[dim]Cancelled.[/dim]")
            return
        # If the user pasted a full M expression directly, write it straight back
        if change_request.startswith("let") or change_request.startswith("="):
            new_m = change_request
        else:
            # Ask Claude to rewrite the M expression
            console.print("[dim]Asking Claude to rewrite the M expression…[/dim]")
            prompt = (
                f"Rewrite the following Power Query M expression to satisfy this change request:\n\n"
                f"Change: {change_request}\n\n"
                f"Current M expression for query '{result['name']}':\n\n"
                f"{result['formula']}\n\n"
                f"Return ONLY the updated M expression — no explanation, no markdown fences."
            )
            new_m = _call_claude("You are a Power Query M expression expert.", prompt, timeout=120)
            if not new_m:
                console.print("[bold red]Claude did not return a result. No changes written.[/bold red]")
                return
            console.print(
                Panel(
                    new_m,
                    title="[bold cyan]Proposed M expression[/bold cyan]",
                    border_style="dim",
                    padding=(0, 2),
                )
            )
            try:
                confirm = console.input("[bold yellow]Write this to Excel? (y/n) > [/bold yellow]").strip().lower()
            except EOFError:
                confirm = "n"
            if confirm not in {"y", "yes"}:
                console.print("[dim]Discarded — no changes written.[/dim]")
                return
        write_result = pq_helper.set_query(result["name"], new_m)
        if write_result["success"]:
            action = write_result.get("action", "updated")
            console.print(f"[dim]Query '{result['name']}' {action} in {write_result['workbook']}.[/dim]")
        else:
            console.print(f"[bold red]Write failed:[/bold red] {write_result['error']}")
        return

    # ── fallback ──────────────────────────────────────────────────────────────
    console.print(
        "[dim]Power Query commands: [bold]pq list[/bold]  |  [bold]pq show <name>[/bold]  "
        "|  [bold]pq refresh [name][/bold]  |  [bold]pq edit <name>[/bold][/dim]"
    )


def _clear_history() -> None:
    """Clear the in-session conversation history and delete the persisted file."""
    global _chat_history
    _chat_history = []
    path = os.path.join(_ROOT, "memory", "chat-history.json")
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass
    console.print("[dim]Conversation history cleared.[/dim]")


def _save_note(note_text: str) -> None:
    notes_path = os.path.join(_ROOT, "memory", "notes.md")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(notes_path, "a", encoding="utf-8") as nf:
        nf.write(f"- [{ts}] {note_text}\n")
    reload_memory()
    console.print("[dim]Noted.[/dim]")


def _read_clipboard() -> str:
    try:
        text = get_clipboard_text()
    except Exception as e:
        console.print(f"[bold red]Clipboard error:[/bold red] {e}")
        return ""
    if not text:
        console.print("[dim]Clipboard is empty.[/dim]")
        return ""
    console.print(f"[dim]Read {len(text)} character(s) from clipboard.[/dim]")
    return text


def _read_multiline() -> str:
    console.print("[dim]Paste your input. Type [bold]done[/bold] on its own line when finished.[/dim]")
    lines = []
    while True:
        try:
            line = console.input("")
        except EOFError:
            break
        if line.strip().lower() == "done":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if text:
        console.print(f"[dim]Captured {len(lines)} line(s).[/dim]")
    return text


def _show_tools() -> None:
    """Show available tools in a compact, chat-friendly list."""
    console.print()
    console.print("[bold cyan]What I can do:[/bold cyan]")
    console.print()
    for _key, tool in TOOL_REGISTRY.items():
        status, note = _tool_registry_status(tool)
        icon = "✓" if status == "ready" else "·"
        color = "green" if status == "ready" else "dim"
        line = f"  [{color}]{icon}[/{color}]  [bold]{tool['name']}[/bold] — {tool['description']}"
        if note and status != "ready":
            line += f" [dim]({note})[/dim]"
        console.print(line)
        if tool.get("examples"):
            eg = tool["examples"][0]
            console.print(f'     [dim italic]e.g. "{eg}"[/dim italic]')
    console.print()
    console.print("[dim]Type [bold]/status[/bold] for full system status and MCP details.[/dim]")
    console.print()


def _show_chat_help() -> None:
    """Show contextual help inside the chat loop."""
    console.print()
    console.print(Markdown("""
**Alfred — quick reference**

Just talk naturally. Examples:
- *"Find my wages report and check if Derrimut looks off this week"*
- *"Fix the bug in backend/main.py where X crashes"*
- *"What's the latest version of pandas?"*
- *"Create a PowerPoint summary of last month's financials"*

**Shortcuts:**
| Command | What it does |
|---------|-------------|
| `clip` | Process what's in your clipboard |
| `paste` | Enter multi-line input |
| `remember: ...` | Save a note to memory |
| `pq list` | List Power Query queries |
| `pbi connect` | Link to open Power BI file |

**Slash commands:**
`/tools` · `/memory` · `/skills` · `/status` · `/clear` · `/menu` · `/dev` · `/help`

**Provider override:** *"use claude code: ..."* or type `auto` to reset.
    """))


def _handle_slash_command(cmd: str, _sticky_provider: "str | None" = None) -> None:
    """Dispatch a /command typed in the chat loop."""
    parts = cmd.strip().split(None, 1)
    name = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if name in {"/help", "/h", "/?"}:
        _show_chat_help()
    elif name in {"/tools", "/capabilities", "/what"}:
        _show_tools()
    elif name in {"/memory", "/mem", "/context"}:
        _action_view_memory()
    elif name in {"/skills", "/skill"}:
        _action_view_skills()
    elif name in {"/status", "/tower"}:
        _action_control_tower()
    elif name in {"/clear", "/reset"}:
        _clear_history()
    elif name in {"/menu"}:
        _show_menu_interactive()
    elif name in {"/dev", "/portal"}:
        _action_dev_portal()
    elif name in {"/pbi"}:
        _action_pbi_connect()
    elif name in {"/note", "/remember"}:
        if args:
            _save_note(args)
        else:
            console.print("[dim]Usage: /note <text>[/dim]")
    elif name in {"/workspace", "/files"}:
        if args:
            _write_workspace(args)
        else:
            # Show current workspace then offer to change it
            ws_path = os.path.join(_ROOT, "memory", "workspace.md")
            if os.path.isfile(ws_path):
                with open(ws_path, "r", encoding="utf-8") as wf:
                    console.print(Markdown(wf.read()))
            console.print("[dim]Usage: /workspace <path>  to set a new workspace.[/dim]")
    else:
        console.print(
            f"[dim]Unknown command [bold]{name}[/bold]. "
            "Try [bold]/help[/bold] for a list.[/dim]"
        )


def _show_menu_interactive() -> None:
    """Show the classic numbered menu and handle a single selection."""
    console.print()
    _show_menu()
    try:
        raw = console.input("[bold yellow]Select (or Enter to return to chat) > [/bold yellow]")
    except EOFError:
        return
    stripped = raw.strip()
    if not stripped:
        return
    choice = "".join(ch for ch in stripped if ch.isdigit())
    if choice == "8":
        raise SystemExit(0)
    action = _ACTIONS.get(choice)
    if action:
        action()
    else:
        console.print("[dim]Invalid option.[/dim]")


def _chat_loop() -> None:
    """Alfred's primary interface — a natural conversation loop.

    Replaces the old numbered menu as the first thing the user sees.
    Supports slash commands (/tools, /help, /memory, etc.) for power users
    while remaining entirely optional — normal speech always works.
    """
    console.print(
        "\n[dim]Just talk naturally. "
        "Type [bold]/help[/bold] for tips · [bold]/tools[/bold] to see what I can do · "
        "[bold]/menu[/bold] for the full menu.[/dim]\n"
    )

    sticky_provider: "str | None" = None

    while True:
        try:
            if sticky_provider:
                label = (
                    f"[bold cyan]Alfred[/bold cyan] "
                    f"[dim][{PROVIDER_LABELS.get(sticky_provider, sticky_provider)}][/dim] > "
                )
            else:
                label = "[bold cyan]Alfred[/bold cyan] > "
            user_input = console.input(label)
        except EOFError:
            return

        stripped = user_input.strip()
        if not stripped:
            continue

        # ── Exit ─────────────────────────────────────────────────────────────
        if stripped.lower() in {"exit", "quit", "bye", "goodbye", "q"}:
            return

        # ── Slash commands ────────────────────────────────────────────────────
        if stripped.startswith("/"):
            _handle_slash_command(stripped, sticky_provider)
            continue

        # ── Legacy navigation shortcuts (still work) ──────────────────────────
        if stripped.upper() == "HOME" or stripped.lower() in {"back", "menu"}:
            _show_menu_interactive()
            continue

        # ── Connectivity shortcuts ────────────────────────────────────────────
        if stripped.lower() in {"pbi connect", "connect pbi", "connect power bi", "power bi connect"}:
            _action_pbi_connect()
            continue

        if "claude login" in stripped.lower() or stripped.lower() in {"login", "claude-login"}:
            console.print("[dim]Opening a terminal for Claude authentication...[/dim]")
            try:
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", _resolve_claude_executable()])
                console.print("[bold green]Terminal opened. Complete login there, then restart Alfred.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Could not open terminal:[/bold red] {e}")
            continue

        # ── Input helpers ─────────────────────────────────────────────────────
        if stripped.lower() in {"clip", "clipboard"}:
            stripped = _read_clipboard()
            if not stripped:
                continue

        if stripped.lower() in {"paste", "multiline"}:
            stripped = _read_multiline()
            if not stripped:
                continue

        # ── Memory shortcuts ──────────────────────────────────────────────────
        if re.match(r"(?i)^(remember|note)\s*:?\s+", stripped):
            note_text = re.sub(r"(?i)^(remember|note)\s*:?\s+", "", stripped).strip()
            if note_text:
                _save_note(note_text)
            continue

        if stripped.lower() in {"context", "memory", "what do you remember", "what do you know"}:
            _action_view_memory()
            continue

        # ── Workspace shortcut ("my workspace is ..." / "my files are in ...") ──
        ws_match = re.match(
            r"(?i)^my\s+(workspace|files?|work\s+folder|folder)\s+(is\s+in|is|are\s+in|are|=)\s+(.+)$",
            stripped,
        )
        if ws_match:
            _write_workspace(ws_match.group(3).strip())
            continue

        # ── Power Query shortcuts ─────────────────────────────────────────────
        if re.match(r"(?i)^pq\b", stripped):
            _handle_pq_command(stripped)
            continue

        # ── Provider override ─────────────────────────────────────────────────
        detected_override = detect_provider_override(stripped)
        if detected_override:
            sticky_provider = detected_override
            stripped = strip_provider_prefix(stripped)
            label = "Claude Code" if sticky_provider == "claude_code" else "Codex"
            console.print(f"[dim]Provider locked to {label} — type [bold]auto[/bold] to let Alfred decide.[/dim]")
        elif stripped.lower() in {"auto", "reset", "reset provider", "auto route", "let alfred decide"}:
            sticky_provider = None
            console.print("[dim]Back to auto-routing.[/dim]")
            continue

        if not _process_alfred_request(stripped, provider_override=sticky_provider):
            return


def _action_ask_alfred() -> None:
    """Legacy entry point — delegates to the unified chat loop."""
    _chat_loop()


def _action_dev_portal() -> None:
    console.print(Rule("[bold cyan]Dev Portal[/bold cyan]"))
    console.print(
        "[dim]Teach Alfred skills, routing rules, tool requirements, or self-improvements."
        "  [bold]paste[/bold] = multiline  |  [bold]clip[/bold] = clipboard  |"
        "  [bold]back[/bold] = menu[/dim]"
    )

    while True:
        try:
            user_input = console.input("\n[bold yellow]Dev Portal > [/bold yellow]")
        except EOFError:
            return

        stripped = user_input.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        if stripped.upper() == "HOME" or lowered in {"back", "menu", "exit"}:
            console.print("[dim]Returning to main menu.[/dim]")
            return

        if lowered in {"skills", "view skills"}:
            _action_view_skills()
            continue

        if lowered in {"rules", "dispatch rules", "routing rules"}:
            _action_show_dispatch_rules()
            continue

        if lowered in {"clip", "clipboard"}:
            try:
                clipboard_text = get_clipboard_text()
            except Exception as e:
                console.print(f"[bold red]Clipboard error:[/bold red] {e}")
                continue
            if not clipboard_text:
                console.print("[dim]Clipboard is empty - nothing to process.[/dim]")
                continue
            console.print(f"[dim]Read {len(clipboard_text)} character(s) from clipboard.[/dim]")
            stripped = clipboard_text

        if lowered in {"paste", "multiline"}:
            console.print("[dim]Paste your input. Type 'done' on its own line when finished.[/dim]")
            lines = []
            while True:
                try:
                    line = console.input("")
                except EOFError:
                    break
                if line.strip().lower() == "done":
                    break
                lines.append(line)
            stripped = "\n".join(lines).strip()
            if not stripped:
                console.print("[dim]No input captured.[/dim]")
                continue
            console.print(f"[dim]Captured {len(lines)} line(s).[/dim]")

        if not _process_alfred_request(stripped, force_learning=True):
            return


def _action_view_memory() -> None:
    console.print(Rule("[bold cyan]Memory[/bold cyan]"))
    memory_dir = os.path.join(_ROOT, "memory")
    if not os.path.isdir(memory_dir):
        console.print("[dim]No memory directory found.[/dim]")
        return
    files = [f for f in sorted(os.listdir(memory_dir)) if f.endswith(".md")]
    if not files:
        console.print("[dim]No memory files found.[/dim]")
        return
    shown = 0
    for fname in files:
        path = os.path.join(memory_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            console.print(
                Panel(
                    Markdown(content),
                    title=f"[bold yellow]{fname}[/bold yellow]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            shown += 1
    if shown == 0:
        console.print("[dim]All memory files are empty.[/dim]")


def _action_view_skills() -> None:
    console.print(Rule("[bold cyan]Available Skills[/bold cyan]"))
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
    if not os.path.isdir(skills_dir):
        console.print("[dim]No skills directory found.[/dim]")
        return

    files = [f for f in sorted(os.listdir(skills_dir)) if f.endswith(".md")]
    if not files:
        console.print("[dim]No skills loaded.[/dim]")
        return

    for i, fname in enumerate(files, 1):
        name = fname[:-3].replace("-", " ").title()
        console.print(f"  [bold yellow]{i}[/bold yellow]  {name}")

    console.print(
        "\n[dim]Type a number to view, or [bold]back[/bold] / [bold]HOME[/bold] to return.[/dim]"
    )

    while True:
        try:
            choice = console.input("\n[bold yellow]Skills > [/bold yellow]").strip()
        except EOFError:
            return

        if not choice:
            continue
        if choice.upper() == "HOME" or choice.lower() in {"back", "menu", "exit"}:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                skill_path = os.path.join(skills_dir, files[idx])
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()
                console.print(
                    Panel(
                        Markdown(content),
                        title=f"[bold yellow]{files[idx]}[/bold yellow]",
                        border_style="dim",
                        padding=(0, 1),
                    )
                )
            else:
                console.print(f"[dim]Enter a number between 1 and {len(files)}.[/dim]")
        except ValueError:
            console.print("[dim]Enter a number or 'back'.[/dim]")


def _load_tool_manifest() -> dict:
    manifest_path = os.path.join(_ROOT, "requirements", "alfred-tools.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_mcp_servers() -> dict:
    settings_path = os.path.join(_ROOT, ".claude", "settings.json")
    if not os.path.isfile(settings_path):
        return {}
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f).get("mcpServers", {})
    except Exception:
        return {}


def _mcp_runtime_status(name: str, configured_servers: dict) -> tuple[str, str]:
    if name not in configured_servers:
        return "planned", "Not configured yet"

    svc = configured_servers.get(name, {})
    if name == "powerbi-modeling-mcp":
        cmd = svc.get("command", "")
        if cmd and not os.path.isfile(cmd):
            return "attention", "Configured path is missing"
        return "ready", "Power BI Desktop model tools available"

    if name == "excel":
        try:
            import excellm  # noqa: F401
            return "ready", "Live workbook tools available"
        except ImportError:
            return "attention", "excellm is not importable"

    if name == "tavily":
        return (
            ("ready", "AI web search available")
            if os.getenv("TAVILY_API_KEY") or svc.get("env", {}).get("TAVILY_API_KEY")
            else ("attention", "Missing Tavily API key")
        )

    if name == "github":
        return (
            ("ready", "GitHub API tools available")
            if svc.get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN")
            else ("attention", "Missing GitHub token")
        )

    if name == "playwright":
        return "ready", "Browser automation configured"

    return "ready", "Configured in Claude MCP settings"


def _status_style(status: str) -> str:
    return {
        "ready": "[green]ready[/green]",
        "attention": "[yellow]attention[/yellow]",
        "planned": "[dim]planned[/dim]",
    }.get(status, status)


def _action_control_tower() -> None:
    console.print(Rule("[bold cyan]Control Tower[/bold cyan]"))
    console.print(
        "[dim]Live capability readiness — providers, MCP stack, and what Alfred can do right now.[/dim]"
    )

    manifest = _load_tool_manifest()
    mcp_servers = _load_mcp_servers()

    # ── Capability Registry ─────────────────────────────────────────────────────
    cap_table = Table(title="Capabilities", box=box.ROUNDED, border_style="dim", padding=(0, 1))
    cap_table.add_column("Capability", style="bold cyan", no_wrap=True)
    cap_table.add_column("Via", style="bold yellow", no_wrap=True)
    cap_table.add_column("Status", style="white", no_wrap=True)
    cap_table.add_column("What Alfred can do", style="white")

    for cap in ALFRED_CAPABILITY_REGISTRY:
        status, note = _capability_status(cap)
        prov_label = PROVIDER_LABELS.get(cap["provider"], cap["provider"])
        prov_color = PROVIDER_COLORS.get(cap["provider"], "white")
        status_str = _status_style(status)
        desc = cap["description"]
        if note:
            desc = f"{desc} [dim]({note})[/dim]"
        cap_table.add_row(cap["name"], f"[{prov_color}]{prov_label}[/{prov_color}]", status_str, desc)

    console.print(cap_table)

    providers = Table(title="Providers", box=box.ROUNDED, border_style="dim", padding=(0, 1))
    providers.add_column("Provider", style="bold yellow")
    providers.add_column("Status", style="white")
    providers.add_column("Role", style="white")
    claude_ok = shutil.which("claude.cmd") or shutil.which("claude")
    codex_ok = shutil.which("codex.cmd") or shutil.which("codex")
    providers.add_row("Claude Code", "[green]installed[/green]" if claude_ok else "[red]missing[/red]", "Chat, execution, MCP tools, Office/PC operations")
    providers.add_row("Codex", "[green]installed[/green]" if codex_ok else "[red]missing[/red]", "Code edits, tests, Alfred self-improvement")
    console.print(providers)

    office = Table(title="Office Mastery", box=box.ROUNDED, border_style="dim", padding=(0, 1))
    office.add_column("Domain", style="bold cyan")
    office.add_column("Capability", style="white")
    office.add_column("Current Path", style="white")
    office.add_row("Excel", "Live workbook read/write, formulas, tables, pivots, charts, VBA", "excellm MCP")
    office.add_row("Power BI", "DAX, model edits, relationships, visuals, Power Query diagnosis", "Power BI MCP + pbi-cli")
    office.add_row("Word", "Reports, proposals, templates, structured documents", "python-docx skill path")
    office.add_row("PowerPoint", "Slide decks from analysis, dashboards, and outlines", "python-pptx skill path")
    office.add_row("PDF", "Extract, compare, summarize, convert source material", "pypdf skill path")
    console.print(office)

    mcp_table = Table(title="MCP Stack", box=box.ROUNDED, border_style="dim", padding=(0, 1))
    mcp_table.add_column("Tool", style="bold yellow", no_wrap=True)
    mcp_table.add_column("Status", style="white", no_wrap=True)
    mcp_table.add_column("Risk", style="white", no_wrap=True)
    mcp_table.add_column("Purpose", style="white")

    for tool in manifest.get("mcp", {}).get("tools", []):
        name = tool.get("name", "")
        status, note = _mcp_runtime_status(name, mcp_servers)
        risk = "[red]write[/red]" if tool.get("destructive") else "[green]read[/green]"
        purpose = tool.get("purpose", "")
        if note:
            purpose = f"{purpose} [dim]({note})[/dim]"
        mcp_table.add_row(name, _status_style(status), risk, purpose)
    console.print(mcp_table)

    gaps = []
    for tool in manifest.get("mcp", {}).get("tools", []):
        status, note = _mcp_runtime_status(tool.get("name", ""), mcp_servers)
        if status != "ready":
            gaps.append(f"{tool.get('name')}: {note}")

    if gaps:
        console.print(Panel("\n".join(f"- {gap}" for gap in gaps), title="[bold yellow]Next Setup Gaps[/bold yellow]", border_style="yellow"))
    else:
        console.print(Panel("[green]All registered MCP tools are configured.[/green]", title="[bold green]Ready[/bold green]", border_style="green"))

    console.print("\n[dim]Type [bold]back[/bold] or [bold]HOME[/bold] to return.[/dim]")
    try:
        console.input("\n[bold yellow]Control Tower > [/bold yellow]")
    except EOFError:
        return


def _action_platforms() -> None:
    console.print(Rule("[bold cyan]Platforms[/bold cyan]"))
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Opt", style="bold yellow", no_wrap=True)
    t.add_column("Platform", style="white")
    t.add_row("1", "Claude Code  [dim](opens new terminal)[/dim]")
    t.add_row("2", "Codex        [dim](opens new terminal)[/dim]")
    t.add_row("3", "Back")
    console.print(t)

    while True:
        try:
            choice = console.input("\n[bold yellow]Platforms > [/bold yellow]").strip()
        except EOFError:
            return

        if not choice:
            continue
        if choice.upper() == "HOME" or choice.lower() in {"back", "menu", "exit", "3"}:
            return

        if choice == "1":
            exe = _resolve_claude_executable()
            console.print("[dim]Opening Claude Code in a new terminal...[/dim]")
            try:
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe])
                console.print("[bold green]Claude Code terminal opened.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Could not open terminal:[/bold red] {e}")
            continue

        if choice == "2":
            exe = _resolve_codex_executable()
            console.print("[dim]Opening Codex in a new terminal...[/dim]")
            try:
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe])
                console.print("[bold green]Codex terminal opened.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Could not open terminal:[/bold red] {e}")
            continue

        console.print("[dim]Enter 1, 2, or 3.[/dim]")


def _discover_plugins() -> list:
    """Return available plugins as dicts with name, description, action callable."""
    plugins = []
    plugins_dir = os.path.join(_ROOT, "plugins")
    if os.path.isdir(plugins_dir):
        for entry in sorted(os.listdir(plugins_dir)):
            entry_path = os.path.join(plugins_dir, entry)
            if os.path.isdir(entry_path) and os.path.isfile(os.path.join(entry_path, "app.py")):
                plugins.append({
                    "name": entry.replace("-", " ").replace("_", " ").title(),
                    "description": f"Plugin at plugins/{entry}",
                    "action": lambda: webbrowser.open("http://127.0.0.1:5000"),
                })
    return plugins


def _action_plugins() -> None:
    console.print(Rule("[bold cyan]Plugins[/bold cyan]"))
    plugins = _discover_plugins()
    if not plugins:
        console.print("[dim]No plugins found.[/dim]")
        console.print("[dim]Type [bold]back[/bold] or [bold]HOME[/bold] to return.[/dim]")
        try:
            console.input("[bold yellow]Plugins > [/bold yellow]")
        except EOFError:
            pass
        return

    for i, p in enumerate(plugins, 1):
        console.print(f"  [bold yellow]{i}[/bold yellow]  {p['name']}  [dim]{p['description']}[/dim]")

    console.print(
        "\n[dim]Type a number to launch, or [bold]back[/bold] / [bold]HOME[/bold] to return.[/dim]"
    )

    while True:
        try:
            choice = console.input("\n[bold yellow]Plugins > [/bold yellow]").strip()
        except EOFError:
            return

        if not choice:
            continue
        if choice.upper() == "HOME" or choice.lower() in {"back", "menu", "exit"}:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(plugins):
                plugins[idx]["action"]()
            else:
                console.print(f"[dim]Enter a number between 1 and {len(plugins)}.[/dim]")
        except ValueError:
            console.print("[dim]Enter a number or 'back'.[/dim]")


# ── GitHub REST API helpers (no gh CLI dependency) ─────────────────────────────

def _get_github_token() -> str:
    """Find a GitHub PAT from .env or Claude MCP settings."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        return token
    settings_path = os.path.join(_ROOT, ".claude", "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            token = (
                cfg.get("mcpServers", {})
                .get("github", {})
                .get("env", {})
                .get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            )
            if token:
                return token
        except Exception:
            pass
    return ""


def _github_api(
    method: str,
    url: str,
    token: str,
    *,
    json_data: "dict | None" = None,
    raw_data: "bytes | None" = None,
    content_type: str = "application/octet-stream",
    timeout: int = 30,
) -> "tuple[dict | list, int]":
    """Make a GitHub API request. Returns (parsed_body, http_status_code).
    The token is only placed in Authorization header — never logged or printed."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Alfred/2.0",
    }
    body = None
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_data is not None:
        body = raw_data
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(raw_data))

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return (json.loads(text) if text.strip() else {}), resp.status
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(text), e.code
        except Exception:
            return {"message": text[:300]}, e.code
    except urllib.error.URLError as e:
        return {"message": f"Network error: {e.reason}"}, 0
    except Exception as e:
        return {"message": str(e)[:200]}, 0


def _github_upload_asset(upload_url: str, token: str, filepath: str) -> bool:
    """Upload a single file to a GitHub release. Returns True on success."""
    filename = os.path.basename(filepath)
    # upload_url looks like: https://uploads.github.com/.../assets{?name,label}
    base_url = upload_url.split("{")[0]
    url = f"{base_url}?name={urllib.parse.quote(filename)}"
    with open(filepath, "rb") as fh:
        data = fh.read()
    # Large EXEs can take a while — allow up to 5 minutes for upload
    _, status = _github_api("POST", url, token, raw_data=data, timeout=300)
    return status in (200, 201)


def _action_publish_update() -> None:
    console.print(Rule("[bold green]Publish Alfred Update[/bold green]"))

    # ── 1. Version tag ─────────────────────────────────────────────────────────
    raw_version = console.input(
        "[bold yellow]Version tag (e.g. Alfredv1.5) > [/bold yellow]"
    ).strip()
    if not raw_version:
        console.print("[red]Version is required.[/red]")
        return
    version = raw_version.replace(" ", "")
    if version != raw_version:
        console.print(
            f"[yellow]Spaces removed from tag: [bold]{raw_version}[/bold] → [bold]{version}[/bold][/yellow]"
        )

    # ── 2. GitHub token ────────────────────────────────────────────────────────
    token = _get_github_token()
    if not token:
        console.print(
            Panel(
                "[bold red]GitHub token not found.[/bold red]\n\n"
                "Alfred uses a GitHub Personal Access Token to publish releases.\n\n"
                "To fix:\n"
                "  1. Go to [cyan]https://github.com/settings/tokens[/cyan]\n"
                "  2. Create a token with [bold]repo[/bold] scope\n"
                "  3. Re-run Alfred-Install.exe and enter your token when prompted,\n"
                "     OR add it to your [bold].env[/bold] file as:\n"
                "     [cyan]GITHUB_TOKEN=ghp_...[/cyan]",
                title="[bold red]Setup Required[/bold red]",
                border_style="red",
            )
        )
        return

    repo = "andrewcornell2000-Work/Alfred"
    project_root = (
        os.path.dirname(_ROOT)
        if os.path.basename(_ROOT).lower() == "dist"
        else _ROOT
    )

    # ── 3. Build Alfred.exe ────────────────────────────────────────────────────
    console.print("[dim]Building Alfred.exe...[/dim]")
    build = subprocess.run(
        ["pyinstaller", "--onefile", "--name", "Alfred", "backend\\main.py"],
        capture_output=True, text=True, cwd=project_root,
    )
    if build.returncode != 0:
        console.print("[bold red]PyInstaller build failed:[/bold red]")
        console.print(build.stderr[:3000])
        return
    alfred_exe = os.path.join(project_root, "dist", "Alfred.exe")
    if not os.path.isfile(alfred_exe):
        console.print("[bold red]Alfred.exe not found after build.[/bold red]")
        return
    console.print("[green]Alfred.exe built.[/green]")

    # ── 4. Build Alfred-Install.exe ────────────────────────────────────────────
    installer_script = os.path.join(project_root, "build-installer.ps1")
    installer_exe: "str | None" = os.path.join(project_root, "Alfred-Install.exe")
    if os.path.isfile(installer_script):
        console.print("[dim]Building Alfred-Install.exe...[/dim]")
        install_build = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", installer_script],
            capture_output=True, text=True, cwd=project_root,
        )
        if install_build.returncode != 0 or not os.path.isfile(installer_exe):
            console.print("[yellow]Alfred-Install.exe build failed — will upload Alfred.exe only.[/yellow]")
            if install_build.stderr.strip():
                console.print(f"[dim]{install_build.stderr.strip()[:400]}[/dim]")
            installer_exe = None
        else:
            console.print("[green]Alfred-Install.exe built.[/green]")
    else:
        console.print("[dim yellow]build-installer.ps1 not found — skipping installer build.[/dim yellow]")
        installer_exe = None

    # ── 5. Safe git commit (source files only) ─────────────────────────────────
    console.print("[dim]Staging source changes...[/dim]")
    safe_paths = [
        "backend/main.py", "requirements", "skills",
        "setup.ps1", "run-alfred.bat", "Alfred-Install.ps1", "build-installer.ps1",
        "memory/session-summary.md", "memory/current-focus.md",
        "memory/recent-context.md", "memory/active-projects.md",
    ]
    for rel in safe_paths:
        full = os.path.join(project_root, rel.replace("/", os.sep))
        if os.path.exists(full):
            subprocess.run(["git", "-C", project_root, "add", rel], capture_output=True)

    staged = subprocess.run(
        ["git", "-C", project_root, "diff", "--cached", "--quiet"], capture_output=True
    )
    if staged.returncode != 0:
        commit = subprocess.run(
            ["git", "-C", project_root, "commit", "-m", f"Alfred release {version}"],
            capture_output=True, text=True,
        )
        if commit.returncode == 0:
            console.print("[green]Changes committed.[/green]")
        else:
            console.print(f"[yellow]Commit note:[/yellow] {commit.stderr.strip()[:120]}")
    else:
        console.print("[dim]No source changes to commit.[/dim]")

    push = subprocess.run(
        ["git", "-C", project_root, "push", "origin", "main"],
        capture_output=True, text=True,
    )
    if push.returncode == 0:
        console.print("[green]Pushed to GitHub.[/green]")
    else:
        console.print(f"[yellow]Push note:[/yellow] {push.stderr.strip()[:120]}")

    # ── 6. GitHub release (REST API — no gh CLI needed) ────────────────────────
    console.print("[dim]Checking GitHub release...[/dim]")
    api_base = f"https://api.github.com/repos/{repo}"

    release_data, status_code = _github_api(
        "GET", f"{api_base}/releases/tags/{version}", token
    )

    if status_code == 200:
        console.print(f"[yellow]Release [bold]{version}[/bold] exists — replacing assets.[/yellow]")
        release_id = release_data["id"]
        upload_url = release_data["upload_url"]
        # Remove old assets with conflicting names so upload doesn't fail
        assets_data, _ = _github_api("GET", f"{api_base}/releases/{release_id}/assets", token)
        if isinstance(assets_data, list):
            for asset in assets_data:
                if asset.get("name") in ("Alfred.exe", "Alfred-Install.exe"):
                    _github_api("DELETE", f"{api_base}/releases/assets/{asset['id']}", token)
                    console.print(f"[dim]Removed old {asset['name']}[/dim]")
    elif status_code == 404:
        console.print(f"[dim]Creating release [bold]{version}[/bold]...[/dim]")
        new_release, create_status = _github_api(
            "POST", f"{api_base}/releases", token,
            json_data={
                "tag_name": version,
                "name": version,
                "body": f"Alfred release {version}",
                "draft": False,
                "prerelease": False,
            },
        )
        if create_status not in (200, 201):
            console.print(
                f"[bold red]Release creation failed ({create_status}):[/bold red] "
                f"{new_release.get('message', '')}"
            )
            return
        upload_url = new_release["upload_url"]
        console.print("[green]Release created.[/green]")
    else:
        console.print(
            f"[bold red]GitHub API error ({status_code}):[/bold red] "
            f"{release_data.get('message', '')}"
        )
        return

    # ── 7. Upload assets ────────────────────────────────────────────────────────
    upload_ok = True
    for label, path in [("Alfred.exe", alfred_exe), ("Alfred-Install.exe", installer_exe)]:
        if not path or not os.path.isfile(path):
            console.print(f"[dim yellow]{label} not available — skipping.[/dim yellow]")
            continue
        console.print(f"[dim]Uploading {label} ({os.path.getsize(path) // 1024} KB)...[/dim]")
        if _github_upload_asset(upload_url, token, path):
            console.print(f"[green]{label} uploaded.[/green]")
        else:
            console.print(f"[bold red]{label} upload failed.[/bold red]")
            upload_ok = False

    # ── 8. Done ─────────────────────────────────────────────────────────────────
    release_url = f"https://github.com/{repo}/releases/tag/{version}"
    if upload_ok:
        console.print(
            Panel.fit(
                f"[bold green]Alfred published successfully.[/bold green]\n\n"
                f"[cyan]{release_url}[/cyan]",
                border_style="green",
            )
        )
        webbrowser.open(release_url)
    else:
        console.print(
            Panel.fit(
                f"[bold yellow]Published with warnings — check assets manually.[/bold yellow]\n"
                f"[cyan]{release_url}[/cyan]",
                border_style="yellow",
            )
        )

def _action_view_logs() -> None:
    console.print(Rule("[bold cyan]Recent Interaction Logs[/bold cyan]"))
    logs_path = os.path.join(_ROOT, "logs", "interactions.md")
    if not os.path.isfile(logs_path):
        console.print("[dim]No interaction logs found.[/dim]")
        return
    with open(logs_path, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.strip():
        console.print("[dim]Log file is empty.[/dim]")
    else:
        console.print(Markdown(content))


def _action_show_dispatch_rules() -> None:
    console.print(Rule("[bold cyan]Dispatch Rules[/bold cyan]"))

    t = Table(
        title="Alfred Brain Routing", box=box.ROUNDED, border_style="dim", padding=(0, 1)
    )
    t.add_column("Brain Decision", style="bold cyan")
    t.add_column("Via", style="bold yellow")
    t.add_column("Outcome", style="white")
    t.add_row(
        "GENERAL — conversation, explanations, definitions",
        "Claude",
        "[cyan]Alfred replies directly — no dispatch[/cyan]",
    )
    t.add_row(
        "SEARCH — current data, prices, news, versions",
        "Claude + Tavily",
        "[cyan]Web pre-fetch → Alfred replies[/cyan]",
    )
    t.add_row(
        "CODE — write / fix / refactor / test code",
        "Codex",
        "[blue]Plan shown → confirm → dispatch to Codex[/blue]",
    )
    t.add_row(
        "EXECUTE — files, Excel, browser, GitHub, Office",
        "Claude Code",
        "[green]Plan shown → confirm → dispatch to Claude Code[/green]",
    )
    t.add_row(
        "POWERBI — DAX, model, visuals, Power Query",
        "Claude Code",
        "[green]Plan shown → confirm → dispatch to Claude Code[/green]",
    )
    t.add_row(
        "Dangerous keyword detected",
        "—",
        "[red]Blocked — no dispatch[/red]",
    )
    t.add_row(
        "Learning / Creator Mode (confirmed)",
        "Codex",
        "[blue]Discuss → confirm → dispatch to Codex[/blue]",
    )
    console.print(t)

    console.print("\n[bold yellow]Learning / Creator Mode[/bold yellow] [dim](triggers confirmation flow)[/dim]")
    console.print("  " + "  ".join(f"[cyan]{k}[/cyan]" for k in sorted(LEARNING_MODE_KEYWORDS)))

    kw_table = Table(
        title="Routing Keywords", box=box.ROUNDED, border_style="dim", padding=(0, 1)
    )
    kw_table.add_column("Provider", style="bold yellow", no_wrap=True)
    kw_table.add_column("Trigger Keywords", style="white")
    kw_table.add_row("codex", ", ".join(sorted(CODEX_ROUTING_KEYWORDS)))
    kw_table.add_row("claude_code", ", ".join(sorted(CLAUDE_CODE_ROUTING_KEYWORDS)))
    console.print(kw_table)

    console.print("\n[bold yellow]Dangerous Keywords[/bold yellow] [dim](block dispatch)[/dim]")
    console.print("  " + "  ".join(f"[red]{k}[/red]" for k in DANGEROUS_KEYWORDS))

    console.print("\n[bold yellow]Action Keywords[/bold yellow] [dim](trigger POWERBI dispatch)[/dim]")
    console.print("  " + "  ".join(f"[green]{k}[/green]" for k in ACTION_KEYWORDS))


def _action_run_claude_directly() -> None:
    console.print(Rule("[bold cyan]Run Claude Directly[/bold cyan]"))
    try:
        prompt = console.input("[bold yellow]Prompt > [/bold yellow]")
    except EOFError:
        return

    if not prompt.strip():
        return

    console.print("\n[bold cyan]Sending to Claude...[/bold cyan]")
    _render_claude_result(run_claude(prompt))


# ── Entry point ────────────────────────────────────────────────────────────────

_ACTIONS = {
    "1": _action_ask_alfred,
    "2": _action_control_tower,
    "3": _action_view_skills,
    "4": _action_platforms,
    "5": _action_dev_portal,
    "6": _action_plugins,
    "7": _action_publish_update,
}


def _write_env_var(env_path: str, key: str, value: str) -> None:
    """Write or update a single KEY=value line in a .env file."""
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        if re.search(rf"(?m)^{re.escape(key)}=", content):
            content = re.sub(rf"(?m)^{re.escape(key)}=.*", f"{key}={value}", content)
        else:
            content = content.rstrip("\n") + f"\n{key}={value}\n"
    else:
        content = f"{key}={value}\n"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)


def _repair_install_claude() -> None:
    console.print("[dim]Running: npm install -g @anthropic-ai/claude-code[/dim]")
    r = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        console.print("[bold green]Installed. Restart Alfred, then authenticate with: claude login[/bold green]")
    else:
        console.print(f"[bold red]Install failed:[/bold red] {r.stderr.strip()[:200]}")


def _repair_claude_login() -> None:
    exe = _resolve_claude_executable()
    try:
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe])
        console.print("[bold green]Terminal opened — sign in, then restart Alfred.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Could not open terminal:[/bold red] {e}")


def _repair_install_codex() -> None:
    console.print("[dim]Running: npm install -g @openai/codex[/dim]")
    r = subprocess.run(["npm", "install", "-g", "@openai/codex"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        console.print("[bold green]Installed. Restart Alfred, then authenticate with: codex login[/bold green]")
    else:
        console.print(f"[bold red]Install failed:[/bold red] {r.stderr.strip()[:200]}")


def _repair_codex_login() -> None:
    exe = _resolve_codex_executable()
    try:
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe])
        console.print("[bold green]Terminal opened — sign in, then restart Alfred.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Could not open terminal:[/bold red] {e}")


def _repair_tavily_key() -> None:
    try:
        ans = console.input("Open app.tavily.com in browser? (y/n) > ").strip()
        if ans.lower() in {"y", "yes"}:
            webbrowser.open("https://app.tavily.com")
        key = console.input("Paste Tavily API key (tvly-...): ").strip()
    except EOFError:
        return
    if not key.startswith("tvly-"):
        console.print("[bold red]Invalid key — must start with tvly-[/bold red]")
        return
    _write_env_var(os.path.join(_ROOT, ".env"), "TAVILY_API_KEY", key)
    os.environ["TAVILY_API_KEY"] = key
    console.print("[bold green]Tavily key saved — web research now active.[/bold green]")


def _repair_github_token() -> None:
    try:
        ans = console.input("Open github.com/settings/tokens in browser? (y/n) > ").strip()
        if ans.lower() in {"y", "yes"}:
            webbrowser.open("https://github.com/settings/tokens/new")
        key = console.input("Paste GitHub Personal Access Token (ghp_...): ").strip()
    except EOFError:
        return
    if not key:
        return
    _write_env_var(os.path.join(_ROOT, ".env"), "GITHUB_TOKEN", key)
    os.environ["GITHUB_TOKEN"] = key
    console.print("[bold green]GitHub token saved.[/bold green]")


def _repair_excel_mcp() -> None:
    pip = os.path.join(_ROOT, ".venv", "Scripts", "pip.exe")
    if not os.path.isfile(pip):
        pip = "pip"
    console.print("[dim]Running: pip install excellm[/dim]")
    r = subprocess.run([pip, "install", "excellm"], capture_output=True, text=True)
    if r.returncode == 0:
        console.print("[bold green]Excel MCP installed — restart Alfred to activate.[/bold green]")
    else:
        console.print(f"[bold red]Install failed:[/bold red] {r.stderr.strip()[:200]}")


def _check_setup() -> None:
    # Each issue is (description, repair_fn | None)
    issues: list[tuple[str, object]] = []

    # ── Claude ────────────────────────────────────────────────────────────────
    claude_installed = bool(shutil.which("claude.cmd") or shutil.which("claude"))
    if not claude_installed:
        issues.append(("Claude Code CLI not installed", _repair_install_claude))
    else:
        creds = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
        if not os.path.isfile(creds) or os.path.getsize(creds) < 10:
            issues.append(("Claude not logged in", _repair_claude_login))

    # ── Codex ─────────────────────────────────────────────────────────────────
    codex_installed = bool(shutil.which("codex.cmd") or shutil.which("codex"))
    if not codex_installed:
        issues.append(("Codex CLI not installed", _repair_install_codex))
    else:
        auth = os.path.join(os.path.expanduser("~"), ".codex", "auth.json")
        if not os.path.isfile(auth) or os.path.getsize(auth) < 10:
            issues.append(("Codex not logged in", _repair_codex_login))

    # ── Optional capabilities ─────────────────────────────────────────────────
    if not _get_tavily_api_key():
        issues.append(("Tavily key missing — web research unavailable", _repair_tavily_key))
    if not _get_github_token():
        issues.append(("GitHub token missing — GitHub operations unavailable", _repair_github_token))

    # ── MCP servers ───────────────────────────────────────────────────────────
    settings_path = os.path.join(_ROOT, ".claude", "settings.json")
    mcp_ready = []
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                mcp_cfg = json.load(f)
            for svc_name, svc in mcp_cfg.get("mcpServers", {}).items():
                if svc_name == "powerbi-modeling-mcp":
                    cmd = svc.get("command", "")
                    if cmd and not os.path.isfile(cmd):
                        issues.append((
                            f"Power BI MCP: server not found at {cmd}",
                            None,  # needs Alfred-Install.exe
                        ))
                    else:
                        mcp_ready.append("Power BI")
                elif svc_name == "excel":
                    try:
                        import excellm  # noqa: F401
                        mcp_ready.append("Excel")
                    except ImportError:
                        issues.append(("Excel MCP: excellm not installed", _repair_excel_mcp))
                elif svc_name == "playwright":
                    mcp_ready.append("Browser")
        except Exception:
            pass

    if mcp_ready:
        console.print(f"[dim green]MCP ready: {', '.join(mcp_ready)}[/dim green]")

    if not issues:
        console.print("[dim green]All systems ready.[/dim green]")
        return

    # ── Show issues with repair options ───────────────────────────────────────
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("n", style="bold yellow", no_wrap=True)
    t.add_column("Issue", style="white")
    t.add_column("", no_wrap=True)
    for i, (desc, fn) in enumerate(issues, 1):
        tag = "[green]fix available[/green]" if fn else "[dim]manual[/dim]"
        t.add_row(str(i), desc, tag)
    console.print(Panel(t, title="[bold yellow]Setup[/bold yellow]", border_style="yellow", padding=(0, 1)))
    console.print("[dim]Type a number to fix it now, or press Enter to continue.[/dim]")

    while True:
        try:
            choice = console.input("[bold yellow]Fix > [/bold yellow]").strip()
        except EOFError:
            break
        if not choice:
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(issues):
                desc, fn = issues[idx]
                if fn:
                    fn()
                else:
                    console.print("[dim]Re-run Alfred-Install.exe to repair this automatically.[/dim]")
            else:
                console.print(f"[dim]Enter 1–{len(issues)} or press Enter to skip.[/dim]")
        except ValueError:
            break



def main():
    _show_header()
    _ensure_memory_files()
    _check_setup()
    reload_memory()
    _load_chat_history()          # restore last session's conversation
    _setup_workspace_if_needed()  # one-time prompt for file location
    _show_startup_memory()
    check_github_updates()

    # Go directly into the chat loop — no menu navigation required.
    # The menu is still available at any time via /menu or the 'menu' keyword.
    try:
        _chat_loop()
    except SystemExit:
        pass  # raised by the menu's "8. Exit" option

    console.print("\n[bold cyan]Alfred signing off. Goodbye.[/bold cyan]")
    save_session_exit_summary()
    check_and_offer_git_commit()


if __name__ == "__main__":
    main()
