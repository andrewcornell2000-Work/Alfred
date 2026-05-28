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


load_dotenv()

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
You are Alfred, a desktop AI command center — precise, calm, and quietly indispensable.

Speak like a senior operator: concise, confident, with the occasional dry observation. Never fawn. Never say "Certainly!", "Great question!", "Of course!", or any variant.

Keep responses to 2–4 sentences unless the question genuinely demands more. When asked what you can do, say you're a unified assistant that handles: natural conversation and reasoning (Claude), live web research (Tavily), code writing and refactoring (Codex), file and system operations, live Excel editing, Power BI model work, browser automation, GitHub operations, Word/PowerPoint/PDF creation, and market intelligence — all through one chat interface. Tools activate invisibly; you only see results.
"""

LEARNING_DISCUSSION_PROMPT = """
You are Alfred, an AI orchestration assistant — precise, calm, operator-mode.

A user wants to add, modify, or teach Alfred a new rule, feature, or behavior. Before any code is written or dispatched, discuss briefly:

1. Identify what is being proposed (1 sentence)
2. Note any design implication or trade-off worth flagging (1 sentence — skip if obvious)
3. End with exactly: **Proposed change:** <one-line summary of the specific change>

Max 4 sentences total. No filler. No "Great!" or "Certainly!".
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
    """Send a prompt to the claude CLI and return the response text.
    No API key needed — uses the credentials from `claude login`."""
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


# ── Quant Intelligence Tool ────────────────────────────────────────────────────

QUANT_PATH = os.getenv("QUANT_PATH", os.path.join(_ROOT, "plugins", "quant"))
QUANT_PORT = int(os.getenv("QUANT_PORT", "5000"))
QUANT_BASE = os.getenv("QUANT_BASE_URL", "https://alfred-production-8fe8.up.railway.app")

_quant_proc: "subprocess.Popen | None" = None

QUANT_COMMAND_PROMPT = """
You are a command parser for the Quant Intelligence System API.

Given a user query about stocks, trading, or market analysis, return ONLY a compact JSON
object describing the command to execute. No explanation, no code fences.

Available commands:
{"cmd": "analyze",      "ticker": "AAPL"} — full technical + sentiment + options analysis
{"cmd": "backtest",     "ticker": "AAPL"} — backtest strategy for a ticker
{"cmd": "institutional","ticker": "AAPL"} — smart-money / institutional flow
{"cmd": "opportunities"}                  — scan all tracked stocks for trade signals
{"cmd": "macro"}                          — current macro environment
{"cmd": "paper"}                          — paper trading portfolio stats
{"cmd": "alerts"}                         — recent trade alerts
{"cmd": "learning"}                       — signal reliability and learning performance
{"cmd": "refresh"}                        — clear the data cache

Return ONLY the JSON.
"""

QUANT_SUMMARY_PROMPT = """
You are Alfred, a precise and unflappable AI assistant.

Summarize the following Quant Intelligence System data in 3-6 bullet points.
Focus on actionable signals: direction, score, key drivers, risks.
Be concise and direct. No filler. No "Certainly!".
"""


def _quant_is_running() -> bool:
    try:
        urllib.request.urlopen(f"{QUANT_BASE}/api/alerts", timeout=2)
        return True
    except Exception:
        return False


def _quant_start_server() -> bool:
    global _quant_proc
    python_exe = sys.executable
    try:
        _quant_proc = subprocess.Popen(
            [python_exe, "app.py"],
            cwd=QUANT_PATH,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            time.sleep(0.5)
            if _quant_is_running():
                return True
        return False
    except Exception as e:
        console.print(f"[bold red]Failed to start Quant server:[/bold red] {e}")
        return False


def _quant_ensure_running() -> bool:
    if _quant_is_running():
        return True
    console.print("[dim]Starting Quant server...[/dim]")
    ok = _quant_start_server()
    if ok:
        console.print("[bold green]Quant server ready.[/bold green]")
    else:
        console.print(
            f"[bold red]Could not start Quant server.[/bold red] "
            f"Check that app.py exists at [cyan]{QUANT_PATH}[/cyan]"
        )
    return ok


def _quant_fetch(endpoint: str) -> dict:
    url = f"{QUANT_BASE}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except Exception:
            return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _quant_parse_command(user_input: str) -> dict:
    raw = _call_claude(QUANT_COMMAND_PROMPT, user_input)
    try:
        parsed = extract_structured_response(raw)
        if "cmd" in parsed:
            return parsed
        return json.loads(raw)
    except Exception:
        return {"cmd": "opportunities"}


def _quant_summarize(data: dict, user_input: str) -> str:
    payload = json.dumps(data, default=str)[:4000]
    return (
        _call_claude(QUANT_SUMMARY_PROMPT, f"User asked: {user_input}\n\nData:\n{payload}", timeout=90)
        or "No summary available."
    )


def run_quant_query(user_input: str) -> str:
    if not _quant_ensure_running():
        return "Quant server unavailable."

    cmd = _quant_parse_command(user_input)
    console.print(f"[dim]Quant command: {cmd}[/dim]")

    c = cmd.get("cmd", "opportunities")
    ticker = cmd.get("ticker", "").upper()

    endpoint_map = {
        "opportunities": "/api/opportunities",
        "macro":         "/api/macro",
        "paper":         "/api/paper",
        "alerts":        "/api/alerts",
        "learning":      "/api/learning",
        "refresh":       "/api/refresh",
    }
    ticker_map = {
        "analyze":       "/api/analyze/",
        "backtest":      "/api/backtest/",
        "institutional": "/api/institutional/",
    }

    if c in ticker_map:
        if not ticker:
            return "Please specify a ticker — e.g. 'analyze AAPL'."
        data = _quant_fetch(f"{ticker_map[c]}{ticker}")
    elif c in endpoint_map:
        data = _quant_fetch(endpoint_map[c])
    else:
        data = _quant_fetch("/api/opportunities")

    if "error" in data and len(data) == 1:
        return f"Quant error: {data['error']}"

    return _quant_summarize(data, user_input)


def _render_quant_result(summary: str) -> None:
    console.print(
        Panel(
            Markdown(summary),
            title="[bold green]Quant Intelligence[/bold green]",
            border_style="green",
            padding=(0, 2),
        )
    )


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


def _action_quant_dashboard() -> None:
    console.print(Rule("[bold green]Quant Dashboard[/bold green]"))
    console.print(f"[dim]Opening {QUANT_BASE}[/dim]")
    webbrowser.open(QUANT_BASE)
    console.print("[bold green]Dashboard launched in browser.[/bold green]")

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
    """Append to conversation history; prune beyond MAX_HISTORY_TURNS turns."""
    global _chat_history
    _chat_history.append({"role": role, "content": content})
    limit = MAX_HISTORY_TURNS * 2
    if len(_chat_history) > limit:
        _chat_history = _chat_history[-limit:]


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
    }
    for fname, content in defaults.items():
        path = os.path.join(memory_dir, fname)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


_MEMORY_SKIP_INJECTION = {"autosave.md"}   # raw logs — excluded from all LLM injection
_MEMORY_HOT_FILES = (                       # focused context injected into every LLM call
    "current-focus.md", "recent-context.md", "active-projects.md", "notes.md"
)
_MEMORY_DEFAULT_MARKERS = {                 # placeholder text created by _ensure_memory_files
    "No session data yet.", "No active projects recorded yet.",
    "No recent context yet.", "No tool history recorded yet.",
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


def classify_task(user_input: str) -> str:
    raw = _call_claude(CLASSIFIER_PROMPT, user_input) or _call_openai(CLASSIFIER_PROMPT, user_input)
    for cat in ["POWERBI", "CLAUDE_EXECUTION", "GENERAL"]:
        if cat in raw.upper():
            return cat
    return "GENERAL"


def generate_general_response(user_input: str) -> str:
    system = GENERAL_RESPONSE_PROMPT
    if _memory_context:
        system += f"\n\n## Project context\n{_memory_context}"

    # Build search-augmented content
    content = user_input
    if _should_search(user_input):
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


def generate_claude_scope(user_input: str, skills_context: str = "", search_context: str = "") -> str:
    system_prompt = CLAUDE_SCOPE_PROMPT
    if _memory_context:
        system_prompt += f"\n\n## Current project memory\n{_memory_context}"
    if skills_context:
        system_prompt += f"\n\nRelevant skills loaded for this task:\n{skills_context}"
    if search_context:
        system_prompt += f"\n\n## Pre-fetched reference material (use to inform the plan)\n{search_context}"
    return _call_claude(system_prompt, user_input) or "Could not generate scope."


CLAUDE_JSON_INSTRUCTION = (
    "Respond ONLY in compact JSON with no markdown, no prose, and no code fences. "
    "Use exactly these keys: summary, root_cause, recommended_next_step, needs_user_approval. "
    "needs_user_approval must be a boolean. All other values must be strings."
)


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
    full_prompt = f"{CLAUDE_JSON_INSTRUCTION}\n\n{prompt}"
    exe = _resolve_claude_executable()
    args = [exe, "-p", full_prompt]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 1, "", f"Claude timed out after {timeout}s.")
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args, 127, "",
            "Claude Code CLI not found. Run: npm install -g @anthropic-ai/claude-code && claude login",
        )


_openai_disabled = False  # set True on auth failure so we don't retry every call


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


def _call_codex(system_prompt: str, user_content: str, timeout: int = 60) -> str:
    """Send a prompt to the codex CLI and return the response text.
    No API key needed — uses credentials from `codex login`."""
    full_prompt = f"{system_prompt.strip()}\n\n---\n\n{user_content.strip()}"
    exe = _resolve_codex_executable()
    try:
        result = subprocess.run(
            [exe, full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            console.print(f"[dim red]Codex CLI: {result.stderr.strip()[:120]}[/dim red]")
    except FileNotFoundError:
        msg = (
            "Codex CLI not found. Run:\n"
            "  npm install -g @openai/codex\n"
            "  codex login"
        )
        console.print(f"[bold red]Setup required:[/bold red]\n{msg}")
        return msg
    except subprocess.TimeoutExpired:
        console.print("[dim red]Codex CLI timed out.[/dim red]")
    return ""


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


def run_codex(prompt: str, timeout: int = 300) -> subprocess.CompletedProcess:
    full_prompt = f"{CLAUDE_JSON_INSTRUCTION}\n\n{prompt}"
    args = [_resolve_codex_executable(), full_prompt]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 1, "", f"Codex timed out after {timeout}s.")
    except FileNotFoundError:
        message = (
            "Codex CLI was not found. Run Install-Alfred.bat to install @openai/codex, "
            "then open a new terminal and run 'codex login'. If Codex is installed in a "
            "custom location, set CODEX_BIN to the full path of codex.cmd."
        )
        return subprocess.CompletedProcess(args, 127, "", message)


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
    {
        "name": "Market Intelligence",
        "provider": "quant",
        "category": "QUANT",
        "description": "Trading signals, stock analysis, paper portfolio, institutional flow",
        "requires": "quant_server",
    },
]

_CAPABILITY_REQUIRES_LABELS = {
    "claude_cli":   "Claude CLI",
    "codex_cli":    "Codex CLI",
    "tavily_key":   "Tavily API key",
    "mcp_excel":    "Excel MCP",
    "mcp_powerbi":  "Power BI MCP",
    "mcp_playwright": "Playwright MCP",
    "mcp_github":   "GitHub MCP",
    "quant_server": "Quant plugin",
}


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
    if req == "quant_server":
        ok = os.path.isdir(QUANT_PATH)
        return ("ready", "") if ok else ("planned", "Quant plugin not installed")
    return ("ready", "")


# ── Alfred Brain ───────────────────────────────────────────────────────────────

ALFRED_BRAIN_PROMPT = """
You are Alfred's routing brain. Given the user's request, return a routing decision as compact JSON.

Alfred is a unified desktop AI command center with these capabilities:
- GENERAL: conversation, explanations, definitions, brainstorming — Claude replies directly
- SEARCH: questions needing live/current data (prices, news, latest releases, current events) — Tavily + Claude
- CODE: write/fix/refactor/review code, tests, scripts — Codex CLI
- EXECUTE: act on files, PC, apps, external services (Excel, browser, GitHub, Office docs, scripts) — Claude Code + MCP
- POWERBI: Power BI model, DAX queries, Power Query, visuals — Claude Code + Power BI MCP
- QUANT: trading signals, stock analysis, paper portfolio, market data — Quant plugin

Provider assignment rules:
- "claude": GENERAL and SEARCH (conversation only, no tool use)
- "codex": CODE tasks (repository changes, tests, refactoring)
- "claude_code": EXECUTE and POWERBI tasks (anything requiring files, MCP tools, or system access)
- "quant": QUANT tasks only

Return ONLY compact JSON — no markdown fences, no explanation:
{"category":"GENERAL|SEARCH|CODE|EXECUTE|POWERBI|QUANT","provider":"claude|codex|claude_code|quant","needs_search":false,"needs_clarification":false,"clarification_question":"","plan":"","steps":[]}

Rules:
- needs_search=true for SEARCH category, and for CODE/EXECUTE/POWERBI tasks that would benefit from pre-fetching API docs or reference material
- needs_clarification=true only when a required target (specific file, workbook, ticker, URL, etc.) is genuinely ambiguous and cannot be inferred
- clarification_question should be a short, specific question — or empty string if needs_clarification is false
- plan is a one-sentence summary of the execution approach for CODE/EXECUTE/POWERBI, empty for GENERAL/SEARCH/QUANT
- steps: array of 2–5 short action strings for compound requests with multiple distinct sequential actions (e.g. ["Read workbook structure", "Identify data issues", "Fix formulas", "Summarise changes"]); empty array [] for single-action tasks, GENERAL, SEARCH, or QUANT
"""


def alfred_brain(user_input: str) -> dict:
    """Single LLM call: classify intent, select provider, optionally plan.
    Falls back to keyword-based routing if Claude is unavailable or returns bad JSON."""
    raw = _call_claude(ALFRED_BRAIN_PROMPT, user_input)
    if raw:
        decision = extract_structured_response(raw)
        category = decision.get("category", "").upper()
        provider = decision.get("provider", "")
        valid_categories = {"GENERAL", "SEARCH", "CODE", "EXECUTE", "POWERBI", "QUANT"}
        valid_providers = {"claude", "codex", "claude_code", "quant"}
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


def should_send_to_claude(user_input: str, category: str, provider: str = "") -> bool:
    lowered = user_input.lower()
    if any(kw in lowered for kw in DANGEROUS_KEYWORDS):
        return False
    # Chat-only providers — no auto-dispatch
    if provider in {"openai_mini", "claude"}:
        return False
    if category == "CLAUDE_EXECUTION":
        return True
    if category == "POWERBI" and any(kw in lowered for kw in ACTION_KEYWORDS):
        return True
    return False


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


def choose_provider(user_input: str, category: str) -> str:
    """Deterministic provider routing — returns 'openai_mini', 'codex', or 'claude_code'."""
    if category == "GENERAL":
        return "openai_mini"
    if category == "POWERBI":
        return "claude_code"
    # CLAUDE_EXECUTION: score keyword matches and pick the stronger signal
    lowered = user_input.lower()
    codex_score = sum(1 for kw in CODEX_ROUTING_KEYWORDS if kw in lowered)
    claude_score = sum(1 for kw in CLAUDE_CODE_ROUTING_KEYWORDS if kw in lowered)
    # No keyword signal — stay cheap rather than firing a heavy CLI
    if codex_score == 0 and claude_score == 0:
        return "openai_mini"
    if codex_score > claude_score:
        return "codex"
    return "claude_code"


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
    "quant": "bold green",
}

PROVIDER_LABELS = {
    "claude_code": "Claude Code",
    "codex": "Codex",
    "claude": "Claude",
    "openai_mini": "Claude",      # legacy alias → Claude
    "quant": "Quant plugin",
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
    color = PROVIDER_COLORS.get(provider, "bold white")
    label = PROVIDER_LABELS.get(provider, provider)
    if result.returncode == 0:
        structured = extract_structured_response(result.stdout)
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_column("Field", style="bold cyan", no_wrap=True)
        t.add_column("Value", style="white")
        t.add_row("Provider", f"[{color}]{label}[/{color}]")
        t.add_row("Category", category)
        t.add_row("Summary", structured.get("summary", ""))
        t.add_row("Root Cause", structured.get("root_cause", ""))
        t.add_row("Next Step", structured.get("recommended_next_step", ""))
        approval = structured.get("needs_user_approval", False)
        approval_str = (
            "[bold yellow]Yes — awaiting approval[/bold yellow]"
            if approval
            else "[bold green]No[/bold green]"
        )
        t.add_row("Needs Approval", approval_str)
        console.print(f"\n[{color}]{label} Response[/{color}]")
        console.print(t)
    else:
        console.print(f"\n[bold red]{label} Error:[/bold red]\n{result.stderr}")


def _render_claude_result(result: subprocess.CompletedProcess) -> None:
    if result.returncode == 0:
        structured = extract_structured_response(result.stdout)
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_column("Field", style="bold cyan", no_wrap=True)
        t.add_column("Value", style="white")
        t.add_row("Summary", structured.get("summary", ""))
        t.add_row("Root Cause", structured.get("root_cause", ""))
        t.add_row("Next Step", structured.get("recommended_next_step", ""))
        approval = structured.get("needs_user_approval", False)
        approval_str = "[bold yellow]Yes[/bold yellow]" if approval else "[bold green]No[/bold green]"
        t.add_row("Needs Approval", approval_str)
        console.print("\n[bold green]Claude Response[/bold green]")
        console.print(t)
    else:
        console.print(f"\n[bold red]Claude Error:[/bold red]\n{result.stderr}")


def _render_general_response(response: str) -> None:
    console.print(
        Panel(
            Markdown(response),
            title="[bold cyan]Alfred[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


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
            "[bold cyan]Alfred Console[/bold cyan]  [dim]v2[/dim]\n"
            "[dim]AI Command Center — Claude · Codex · Tavily · Excel · Power BI · GitHub · Browser · Office[/dim]",
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
    """Show a numbered step list as a unified Plan panel before execution."""
    lines = [f"**{i}.** {step}" for i, step in enumerate(steps, 1)]
    console.print(
        Panel(
            Markdown("\n".join(lines)),
            title=f"[bold cyan]Plan — {len(steps)} steps[/bold cyan]",
            border_style="dim",
            padding=(0, 2),
        )
    )


def _render_execution_result(result: subprocess.CompletedProcess) -> None:
    """Show execution result cleanly — no provider/category headers."""
    if result.returncode != 0:
        console.print(
            Panel(
                result.stderr.strip()[:400] or "No output.",
                title="[bold red]Failed[/bold red]",
                border_style="red",
                padding=(0, 2),
            )
        )
        return
    structured = extract_structured_response(result.stdout)
    parts = []
    summary  = structured.get("summary", "").strip()
    next_step = structured.get("recommended_next_step", "").strip()
    needs_approval = structured.get("needs_user_approval", False)
    if summary:
        parts.append(summary)
    if next_step:
        parts.append(f"\n**Next:** {next_step}")
    if needs_approval:
        parts.append("\n*Waiting for your approval to proceed.*")
    body = "\n".join(parts) or result.stdout.strip()[:400]
    console.print(
        Panel(
            Markdown(body),
            title="[bold green]Done[/bold green]",
            border_style="green",
            padding=(0, 2),
        )
    )


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
        console.print(Rule(f"[bold cyan]Step {i} / {total}[/bold cyan]"))
        console.print(f"[dim]{step}[/dim]")

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
        scope = generate_claude_scope(step_prompt, skills_context, search_context=search_context)

        result = run_codex(scope) if provider == "codex" else run_claude(scope)
        _render_execution_result(result)

        if result.returncode != 0:
            if i < total:
                try:
                    cont = console.input(
                        f"[bold yellow]Step {i} failed — continue with remaining steps? (y/n) > [/bold yellow]"
                    ).strip().lower()
                except EOFError:
                    cont = "n"
                if cont not in {"y", "yes"}:
                    console.print("[dim]Sequence stopped.[/dim]")
                    return f"Stopped at step {i}/{total}"
            all_outcomes.append(f"failed — {result.stderr[:80]}")
        else:
            structured = extract_structured_response(result.stdout)
            outcome = structured.get("summary", "") or result.stdout.strip()[:120]
            all_outcomes.append(outcome)

            if structured.get("needs_user_approval") and i < total:
                try:
                    cont = console.input(
                        "[bold yellow]Step requires approval — continue to next step? (y/n) > [/bold yellow]"
                    ).strip().lower()
                except EOFError:
                    cont = "n"
                if cont not in {"y", "yes"}:
                    console.print("[dim]Sequence paused.[/dim]")
                    return f"Paused at step {i}/{total}"

    summary_lines = [f"**{j}.** {o}" for j, o in enumerate(all_outcomes, 1)]
    console.print(
        Panel(
            Markdown("\n".join(summary_lines)),
            title="[bold green]All steps complete[/bold green]",
            border_style="green",
            padding=(0, 2),
        )
    )
    _notify("Alfred", f"Task complete — {total} steps done")
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
                "\n[bold yellow]Proceed with this change? (y/n) > [/bold yellow]"
            )
        except EOFError:
            return False
        if confirm.strip().lower() not in {"y", "yes"}:
            console.print("[dim]Change discarded - nothing written or dispatched.[/dim]")
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

        # Route QUANT directly to the plugin — no scope generation needed
        if brain_category == "QUANT":
            summary = run_quant_query(stripped)
            _render_quant_result(summary)
            append_interaction_log(stripped, "QUANT", "", "quant")
            append_autosave_entry(stripped, "QUANT", "quant", summary[:200])
            compress_autosave_if_needed()
            return True

        # Map Brain categories → pipeline categories (backward-compatible)
        category = {
            "GENERAL": "GENERAL",
            "SEARCH":  "GENERAL",   # search-augmented chat
            "CODE":    "CLAUDE_EXECUTION",
            "EXECUTE": "CLAUDE_EXECUTION",
            "POWERBI": "POWERBI",
        }.get(brain_category, "GENERAL")

    if category == "GENERAL":
        response = generate_general_response(stripped)
        _render_general_response(response)
        outcome = response[:200]

    elif category in ["POWERBI", "CLAUDE_EXECUTION"]:
        # Tavily pre-fetch — silent
        search_context = ""
        if needs_search:
            search_results = _tavily_search(stripped, max_results=3)
            if search_results:
                search_context = "\n\n".join(
                    f"[{r['title']}]({r['url']})\n{r['content'][:600]}"
                    for r in search_results
                )

        skills_context = load_relevant_skills(stripped)

        if steps and should_send_to_claude(stripped, category, provider):
            # ── Multi-step path ──────────────────────────────────────────────
            _render_step_plan(steps)
            try:
                confirm = console.input(
                    "[bold yellow]Proceed? (Enter = yes, or type an adjustment) > [/bold yellow]"
                ).strip()
            except EOFError:
                confirm = ""

            if confirm.lower() in {"n", "no", "cancel", "back"}:
                console.print("[dim]Cancelled.[/dim]")
                append_interaction_log(stripped, category, "", provider)
                append_autosave_entry(stripped, category, provider, "Cancelled by user")
                compress_autosave_if_needed()
                return True

            if confirm and confirm.lower() not in {"y", "yes"}:
                # User typed an adjustment — ask Brain to re-plan the steps
                stripped = f"{stripped}\n\nAdjustment: {confirm}"
                adj_decision = alfred_brain(stripped)
                adj_steps = adj_decision.get("steps", [])
                if isinstance(adj_steps, list) and len(adj_steps) >= 2:
                    steps = [str(s) for s in adj_steps if s]
                _render_step_plan(steps)

            outcome = _run_step_sequence(
                stripped, steps, provider, skills_context, search_context
            )

        elif should_send_to_claude(stripped, category, provider):
            # ── Single-step path ─────────────────────────────────────────────
            scope = generate_claude_scope(stripped, skills_context, search_context=search_context)
            outcome = scope[:200]
            console.print(
                Panel(
                    Markdown(scope),
                    title="[bold cyan]Plan[/bold cyan]",
                    border_style="dim",
                    padding=(0, 2),
                )
            )
            try:
                confirm = console.input(
                    "[bold yellow]Proceed? (Enter = yes, or type an adjustment) > [/bold yellow]"
                ).strip()
            except EOFError:
                confirm = ""

            if confirm.lower() in {"n", "no", "cancel", "back"}:
                console.print("[dim]Cancelled.[/dim]")
                append_interaction_log(stripped, category, scope, provider)
                append_autosave_entry(stripped, category, provider, "Cancelled by user")
                compress_autosave_if_needed()
                return True

            if confirm and confirm.lower() not in {"y", "yes"}:
                stripped = f"{stripped}\n\nAdjustment: {confirm}"
                scope = generate_claude_scope(stripped, skills_context, search_context=search_context)
                outcome = scope[:200]
                console.print(
                    Panel(
                        Markdown(scope),
                        title="[bold cyan]Revised Plan[/bold cyan]",
                        border_style="dim",
                        padding=(0, 2),
                    )
                )

            result = run_codex(scope) if provider == "codex" else run_claude(scope)
            _render_execution_result(result)
            _notify("Alfred", "Task " + ("complete" if result.returncode == 0 else "failed"))
            outcome = (
                result.stdout[:200]
                if result.returncode == 0
                else f"Error: {result.stderr[:100]}"
            )

        else:
            # ── Plan-only (no dispatch) ──────────────────────────────────────
            scope = generate_claude_scope(stripped, skills_context, search_context=search_context)
            outcome = scope[:200]
            console.print(
                Panel(
                    Markdown(scope),
                    title="[bold cyan]Plan[/bold cyan]",
                    border_style="dim",
                    padding=(0, 2),
                )
            )

    append_interaction_log(stripped, category, scope, provider)
    append_autosave_entry(stripped, category, provider, outcome)
    compress_autosave_if_needed()
    return True


def _action_ask_alfred() -> None:
    console.print(
        "\n[dim][bold]clip[/bold] = clipboard  |  [bold]pbi connect[/bold] = link to Power BI Desktop  |  [bold]back[/bold] = menu[/dim]"
    )

    while True:
        try:
            user_input = console.input("\n[bold yellow]Alfred > [/bold yellow]")
        except EOFError:
            return

        stripped = user_input.strip()
        if not stripped:
            continue

        if stripped.upper() == "HOME" or stripped.lower() in {"back", "menu", "exit"}:
            console.print("[dim]Returning to main menu.[/dim]")
            return

        if stripped.lower() in {"pbi connect", "connect pbi", "connect power bi", "power bi connect"}:
            _action_pbi_connect()
            continue

        if "claude login" in stripped.lower() or stripped.lower() in {"login", "claude-login"}:
            console.print("[dim]Opening a new terminal for Claude authentication — sign in via the browser that opens.[/dim]")
            try:
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", _resolve_claude_executable()])
                console.print("[bold green]New terminal opened. Complete login there, then restart Alfred.[/bold green]")
            except Exception as e:
                console.print(
                    f"[bold red]Could not open terminal:[/bold red] {e}\n"
                    "Run manually in a new terminal: [bold yellow]claude[/bold yellow]"
                )
            continue

        if stripped.lower() in {"clip", "clipboard"}:
            try:
                clipboard_text = get_clipboard_text()
            except Exception as e:
                console.print(f"[bold red]Clipboard error:[/bold red] {e}")
                continue
            if not clipboard_text:
                console.print("[dim]Clipboard is empty — nothing to process.[/dim]")
                continue
            console.print(f"[dim]Read {len(clipboard_text)} character(s) from clipboard.[/dim]")
            stripped = clipboard_text

        if stripped.lower() in {"paste", "multiline"}:
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

        # ── Memory shortcuts ────────────────────────────────────────────────
        if re.match(r"(?i)^(remember|note)\s*:?\s+", stripped):
            note_text = re.sub(r"(?i)^(remember|note)\s*:?\s+", "", stripped).strip()
            if note_text:
                notes_path = os.path.join(_ROOT, "memory", "notes.md")
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                with open(notes_path, "a", encoding="utf-8") as _nf:
                    _nf.write(f"- [{ts}] {note_text}\n")
                reload_memory()
                console.print("[dim]Noted.[/dim]")
            continue

        if stripped.lower() in {"context", "memory", "what do you remember", "what do you know"}:
            _action_view_memory()
            continue

        # Check for explicit provider override ("use claude ...", "use codex ...")
        provider_override = detect_provider_override(stripped)
        if provider_override:
            stripped = strip_provider_prefix(stripped)
            console.print(f"[dim]Provider override: {provider_override}[/dim]")

        if not _process_alfred_request(stripped, provider_override=provider_override):
            return


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
    if os.path.isdir(QUANT_PATH):
        plugins.append({
            "name": "Quant Intelligence",
            "description": "Live trading analysis — signals, paper trading, alerts",
            "action": _action_quant_dashboard,
        })
    plugins_dir = os.path.join(_ROOT, "plugins")
    if os.path.isdir(plugins_dir):
        for entry in sorted(os.listdir(plugins_dir)):
            if entry == "quant":
                continue
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
        "QUANT — trading signals, stock analysis",
        "Quant plugin",
        "[green]Routed directly to Quant API[/green]",
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
    _show_startup_memory()
    check_github_updates()

    while True:
        console.print()
        _show_menu()

        try:
            raw = console.input("[bold yellow]Select > [/bold yellow]")
        except EOFError:
            break

        stripped_raw = raw.strip()
        if stripped_raw.upper() == "HOME":
            continue

        choice = "".join(ch for ch in stripped_raw if ch.isdigit())

        if choice == "8":
            console.print("\n[bold cyan]Alfred Console signing off. Goodbye.[/bold cyan]")
            break

        action = _ACTIONS.get(choice)
        if action:
            action()
        else:
            console.print("[dim]Invalid option. Enter 1-8.[/dim]")

    save_session_exit_summary()
    check_and_offer_git_commit()


if __name__ == "__main__":
    main()
