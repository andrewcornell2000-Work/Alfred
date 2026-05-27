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
import webbrowser

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

CLAUDE_EXECUTION: Any request that requires taking action on files, folders, or code.
This includes: organise/organize a folder, read/edit/create/delete files, run scripts,
fix bugs, write code, refactor, inspect a file, scan a directory, execute a command,
anything involving the filesystem or coding tasks.

POWERBI: Any request about Power BI reports, dashboards, Power Query, data models.

GENERAL: Conversation, questions, explanations — anything that does NOT require file/code action.

Return ONLY the category name.
"""

GENERAL_RESPONSE_PROMPT = """
You are Alfred, an AI orchestration assistant — precise, calm, and quietly indispensable.

Speak like a senior operator who has seen everything and remains unflappable: concise, confident, with the occasional dry observation. Never fawn. Never say "Certainly!", "Great question!", "Of course!", or any variant.

Keep responses to 2–4 sentences unless the question genuinely demands more. When asked what you can do, mention: task classification (GENERAL / POWERBI / CLAUDE_EXECUTION), provider routing (Claude Code for execution and file tasks, OpenAI Mini or Claude for chat and classification), optimized prompt generation, skill-based context injection, memory consolidation, and auto-dispatch.
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
        "autosave.md": "",
    }
    for fname, content in defaults.items():
        path = os.path.join(memory_dir, fname)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


def load_all_memory() -> str:
    """Read all memory/*.md files and return a combined context string."""
    memory_dir = os.path.join(_ROOT, "memory")
    if not os.path.isdir(memory_dir):
        return ""
    parts = []
    for fname in sorted(os.listdir(memory_dir)):
        if not fname.endswith(".md"):
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


def reload_memory() -> None:
    global _memory_context
    _memory_context = load_all_memory()


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
    raw = _call_openai(CLASSIFIER_PROMPT, user_input)
    if not raw:
        console.print("[dim yellow]OpenAI unavailable — classifying with Claude.[/dim yellow]")
        raw = _call_claude(CLASSIFIER_PROMPT, user_input)
    for cat in ["POWERBI", "CLAUDE_EXECUTION", "GENERAL"]:
        if cat in raw.upper():
            return cat
    return "GENERAL"


def generate_general_response(user_input: str) -> str:
    system = GENERAL_RESPONSE_PROMPT
    if _memory_context:
        system += f"\n\n## Project context\n{_memory_context}"
    return _call_openai(system, user_input) or _call_claude(system, user_input) or "No response."


def generate_claude_scope(user_input: str, skills_context: str = "") -> str:
    system_prompt = CLAUDE_SCOPE_PROMPT
    if _memory_context:
        system_prompt += f"\n\n## Current project memory\n{_memory_context}"
    if skills_context:
        system_prompt += f"\n\nRelevant skills loaded for this task:\n{skills_context}"
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


def run_claude(prompt: str) -> subprocess.CompletedProcess:
    full_prompt = f"{CLAUDE_JSON_INSTRUCTION}\n\n{prompt}"
    return subprocess.run(
        [_resolve_claude_executable(), "-p", full_prompt],
        capture_output=True,
        text=True,
    )


_openai_disabled = False  # set True on auth failure so we don't retry every call


def _call_openai(system_prompt: str, user_content: str, model: str = "gpt-4o-mini", timeout: int = 60) -> str:
    """Call OpenAI API with the stored API key."""
    global _openai_disabled
    if _openai_disabled:
        return ""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            timeout=timeout,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "401" in err or "Incorrect API key" in err or "invalid_api_key" in err:
            _openai_disabled = True
            console.print(
                "[bold red]OpenAI key rejected (401).[/bold red] "
                "Get a new key at [cyan]https://platform.openai.com/api-keys[/cyan] "
                "and update [cyan].env[/cyan] — using Claude as fallback for this session.\n"
                "[dim]Tip: type [bold]update key[/bold] in Alfred to enter a new key without restarting.[/dim]"
            )
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


def run_codex(prompt: str) -> subprocess.CompletedProcess:
    full_prompt = f"{CLAUDE_JSON_INSTRUCTION}\n\n{prompt}"
    args = [_resolve_codex_executable(), full_prompt]
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
        )
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
    # Repository/file exploration and deep tool use
    "explore", "file exploration", "repository exploration", "deep tool",
}


def should_send_to_claude(user_input: str, category: str, provider: str = "") -> bool:
    lowered = user_input.lower()
    if any(kw in lowered for kw in DANGEROUS_KEYWORDS):
        return False
    # Cost-aware: no auto-dispatch when openai_mini was selected (weak keyword signal)
    if provider == "openai_mini":
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
    return _call_openai(system, user_input) or _call_claude(system, user_input) or "No response."


# ── Display helpers ────────────────────────────────────────────────────────────

PROVIDER_COLORS = {
    "claude_code": "bold green",
    "codex": "bold blue",
    "openai_mini": "bold yellow",
}

PROVIDER_LABELS = {
    "claude_code": "Claude Code",
    "codex": "Codex",
    "openai_mini": "OpenAI Mini",
}


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


def _show_header() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Alfred Console[/bold cyan]  [dim]v2[/dim]\n"
            "[dim]Multi-Provider AI Router — OpenAI (classify/chat) · Claude Code (execution) · Codex (refactoring)[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _show_menu() -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Opt", style="bold yellow", no_wrap=True)
    t.add_column("Action", style="white")
    t.add_row("1", "Ask Alfred")
    t.add_row("2", "View Skills")
    t.add_row("3", "Platforms")
    t.add_row("4", "Dev Portal")
    t.add_row("5", "Plugins")
    t.add_row("6", "Exit")
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


def _process_alfred_request(stripped: str, force_learning: bool = False) -> bool:
    scope = ""
    outcome = ""

    # Dev Portal forces the guarded learning flow even for plain-language notes.
    if force_learning or is_learning_mode_task(stripped):
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
        category = classify_task(stripped)
        provider = choose_provider(stripped, category)

    provider_color = PROVIDER_COLORS.get(provider, "bold white")
    provider_label = PROVIDER_LABELS.get(provider, provider)
    console.print(
        f"\n[bold green]Category:[/bold green] {category}  "
        f"[{provider_color}]Provider: {provider_label}[/{provider_color}]"
    )

    if category == "GENERAL":
        response = generate_general_response(stripped)
        _render_general_response(response)
        outcome = response[:200]

    elif category in ["POWERBI", "CLAUDE_EXECUTION"]:
        console.print("\n[bold cyan]Generating scope...[/bold cyan]")
        skills_context = load_relevant_skills(stripped)
        scope = generate_claude_scope(stripped, skills_context)
        console.print(f"\n[bold magenta]Plan:[/bold magenta]\n{scope}")
        outcome = scope[:200]

        if should_send_to_claude(stripped, category, provider):
            if provider == "codex":
                console.print("\n[bold blue]Auto-dispatching to Codex...[/bold blue]")
                result = run_codex(scope)
                _render_provider_result(provider, category, result)
                outcome = (
                    result.stdout[:200]
                    if result.returncode == 0
                    else f"Error: {result.stderr[:100]}"
                )
            else:
                console.print("\n[bold green]Auto-dispatching to Claude Code...[/bold green]")
                result = run_claude(scope)
                _render_provider_result(provider, category, result)
                outcome = (
                    result.stdout[:200]
                    if result.returncode == 0
                    else f"Error: {result.stderr[:100]}"
                )
        else:
            console.print(
                "\n[bold yellow]Plan ready. Send to provider manually if needed.[/bold yellow]"
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

        if stripped.lower() in {"update key", "openai key", "new key", "set key", "update openai key"}:
            _setup_openai_key()
            continue

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

        scope = ""
        outcome = ""

        # Check for explicit provider override ("use claude ...", "use codex ...")
        provider_override = detect_provider_override(stripped)
        if provider_override:
            task = strip_provider_prefix(stripped)
            console.print(f"[dim]Provider override: {provider_override}[/dim]")
            category = "CLAUDE_EXECUTION"
            provider = provider_override
            stripped = task

        # Learning / Creator Mode: discuss first, then confirm before routing to Codex/Claude
        elif is_learning_mode_task(stripped):
            console.print("\n[dim]Learning / Creator Mode — discussing before routing.[/dim]")
            discussion = generate_learning_discussion(stripped)
            _render_general_response(discussion)
            try:
                confirm = console.input(
                    "\n[bold yellow]Proceed with this change? (y/n) > [/bold yellow]"
                )
            except EOFError:
                return
            if confirm.strip().lower() not in {"y", "yes"}:
                console.print("[dim]Change discarded — nothing written or dispatched.[/dim]")
                append_interaction_log(stripped, "LEARNING_DECLINED", "", "openai_mini")
                append_autosave_entry(
                    stripped, "LEARNING_DECLINED", "openai_mini", "Request declined by user"
                )
                compress_autosave_if_needed()
                continue
            console.print("[dim]Confirmed. Proceeding with routing...[/dim]")
            category = "CLAUDE_EXECUTION"
            provider = "codex"
        else:
            category = classify_task(stripped)
            provider = choose_provider(stripped, category)

        provider_color = PROVIDER_COLORS.get(provider, "bold white")
        provider_label = PROVIDER_LABELS.get(provider, provider)
        console.print(
            f"\n[bold green]Category:[/bold green] {category}  "
            f"[{provider_color}]Provider: {provider_label}[/{provider_color}]"
        )

        if category == "GENERAL":
            response = generate_general_response(stripped)
            _render_general_response(response)
            outcome = response[:200]

        elif category in ["POWERBI", "CLAUDE_EXECUTION"]:
            console.print("\n[bold cyan]Generating scope...[/bold cyan]")
            skills_context = load_relevant_skills(stripped)
            scope = generate_claude_scope(stripped, skills_context)
            console.print(f"\n[bold magenta]Plan:[/bold magenta]\n{scope}")
            outcome = scope[:200]

            if should_send_to_claude(stripped, category, provider):
                if provider == "codex":
                    console.print("\n[bold blue]Auto-dispatching to Codex...[/bold blue]")
                    result = run_codex(scope)
                    _render_provider_result(provider, category, result)
                    outcome = (
                        result.stdout[:200]
                        if result.returncode == 0
                        else f"Error: {result.stderr[:100]}"
                    )
                else:
                    console.print("\n[bold green]Auto-dispatching to Claude Code...[/bold green]")
                    result = run_claude(scope)
                    _render_provider_result(provider, category, result)
                    outcome = (
                        result.stdout[:200]
                        if result.returncode == 0
                        else f"Error: {result.stderr[:100]}"
                    )
            else:
                console.print(
                    "\n[bold yellow]Plan ready. Send to provider manually if needed.[/bold yellow]"
                )

        append_interaction_log(stripped, category, scope, provider)
        append_autosave_entry(stripped, category, provider, outcome)
        compress_autosave_if_needed()


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
        title="Provider Routing", box=box.ROUNDED, border_style="dim", padding=(0, 1)
    )
    t.add_column("Condition", style="bold cyan")
    t.add_column("Provider", style="bold yellow")
    t.add_column("Outcome", style="white")
    t.add_row(
        "Category = GENERAL",
        "openai_mini",
        "[yellow]Answer — no CLI dispatch[/yellow]",
    )
    t.add_row(
        "Category = POWERBI",
        "claude_code",
        "[green]Auto-dispatch to Claude Code[/green]",
    )
    t.add_row(
        "CLAUDE_EXECUTION + codex keywords score higher",
        "codex",
        "[blue]Auto-dispatch to Codex[/blue]",
    )
    t.add_row(
        "CLAUDE_EXECUTION (default / claude keywords score higher)",
        "claude_code",
        "[green]Auto-dispatch to Claude Code[/green]",
    )
    t.add_row(
        "CLAUDE_EXECUTION + no keyword signal",
        "openai_mini",
        "[yellow]Plan shown — no auto-dispatch[/yellow]",
    )
    t.add_row(
        "Learning / Creator Mode (confirmed)",
        "codex",
        "[blue]Discuss → confirm → dispatch to Codex[/blue]",
    )
    t.add_row(
        "Dangerous keyword detected",
        "—",
        "[red]Blocked — no dispatch[/red]",
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
    "2": _action_view_skills,
    "3": _action_platforms,
    "4": _action_dev_portal,
    "5": _action_plugins,
}


def _check_setup() -> None:
    issues = []

    # Claude — installed?
    claude_installed = bool(shutil.which("claude.cmd") or shutil.which("claude"))
    if not claude_installed:
        issues.append("Claude Code CLI not installed.\n  Fix: npm install -g @anthropic-ai/claude-code")
    else:
        # Logged in?
        creds = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
        if not os.path.isfile(creds) or os.path.getsize(creds) < 10:
            issues.append("Claude not logged in.\n  Fix: run [bold yellow]claude login[/bold yellow] in a terminal")

    # Codex — installed?
    codex_installed = bool(shutil.which("codex.cmd") or shutil.which("codex"))
    if not codex_installed:
        issues.append("Codex CLI not installed.\n  Fix: npm install -g @openai/codex")
    else:
        # Logged in?
        auth = os.path.join(os.path.expanduser("~"), ".codex", "auth.json")
        if not os.path.isfile(auth) or os.path.getsize(auth) < 10:
            issues.append("Codex not logged in.\n  Fix: run [bold yellow]codex login[/bold yellow] in a terminal")

    # OpenAI key — optional; Claude handles fallback when missing
    openai_missing = not os.getenv("OPENAI_API_KEY")
    claude_logged_in = (
        claude_installed
        and os.path.isfile(os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json"))
        and os.path.getsize(os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")) >= 10
    )
    if openai_missing and not claude_logged_in:
        issues.append(
            "OpenAI API key missing and Claude not logged in.\n"
            "  Alfred needs at least one provider to work.\n"
            "  Option A: add OPENAI_API_KEY to .env\n"
            "  Option B: run 'claude' in a terminal to authenticate"
        )
    elif openai_missing:
        console.print(
            "[dim yellow]No OpenAI key — using Claude as fallback for classification and chat.[/dim yellow]"
        )

    # MCP server health checks — verify registered servers are actually available
    settings_path = os.path.join(_ROOT, ".claude", "settings.json")
    mcp_ready = []
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                mcp_cfg = json.load(f)
            for svc_name, svc in mcp_cfg.get("mcpServers", {}).items():
                cmd = svc.get("command", "")
                if svc_name == "powerbi-modeling-mcp":
                    if cmd and not os.path.isfile(cmd):
                        issues.append(
                            f"Power BI MCP: server exe not found at {cmd}\n"
                            "  Fix: re-run Alfred-Install.exe to repair the VS Code extension"
                        )
                    else:
                        mcp_ready.append("Power BI")
                elif svc_name == "excel":
                    try:
                        import excellm  # noqa: F401
                        mcp_ready.append("Excel")
                    except ImportError:
                        issues.append(
                            "Excel MCP: excellm not installed.\n"
                            "  Fix: activate .venv and run: pip install excellm"
                        )
        except Exception:
            pass
    else:
        console.print(
            "[dim yellow]MCP tools not configured — Power BI and Excel editing unavailable.[/dim yellow]\n"
            "[dim]Re-run Alfred-Install.exe to set up MCP tools.[/dim]"
        )

    if mcp_ready:
        console.print(f"[dim green]MCP ready: {', '.join(mcp_ready)}[/dim green]")

    if issues:
        body = "[bold red]Pre-flight check failed:[/bold red]\n\n"
        body += "\n\n".join(f"[yellow]{i}[/yellow]" for i in issues)
        console.print(Panel(body, title="[bold red]Setup Required[/bold red]", border_style="red", padding=(1, 2)))
    else:
        console.print("[dim green]Pre-flight check passed.[/dim green]")

    if openai_missing and not claude_logged_in:
        _setup_openai_key()


def main():
    _show_header()
    _ensure_memory_files()
    _check_setup()
    reload_memory()
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

        if choice == "6":
            console.print("\n[bold cyan]Alfred Console signing off. Goodbye.[/bold cyan]")
            break

        action = _ACTIONS.get(choice)
        if action:
            action()
        else:
            console.print("[dim]Invalid option. Enter 1–6.[/dim]")

    save_session_exit_summary()
    check_and_offer_git_commit()


if __name__ == "__main__":
    main()
