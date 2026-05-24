from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
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
import subprocess
import sys

load_dotenv()

# Force UTF-8 output so rich does not fall back to the cp1252 legacy renderer
# on Windows when stdout is not a recognised VT terminal (e.g. piped or
# redirected).
_stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_stdout_utf8, highlight=False)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

CLASSIFIER_PROMPT = """
You are an AI task router.

Classify requests into ONE category only:

GENERAL
POWERBI
CLAUDE_EXECUTION

Return ONLY the category name.
"""

GENERAL_RESPONSE_PROMPT = """
You are Alfred, an AI orchestration assistant — precise, calm, and quietly indispensable.

Speak like a senior operator who has seen everything and remains unflappable: concise, confident, with the occasional dry observation. Never fawn. Never say "Certainly!", "Great question!", "Of course!", or any variant.

Keep responses to 2–4 sentences unless the question genuinely demands more. When asked what you can do, mention: task classification (GENERAL / POWERBI / CLAUDE_EXECUTION), provider routing (openai_mini / codex / claude_code), optimized prompt generation, skill-based context injection, memory consolidation, and auto-dispatch.
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
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": AUTOSAVE_COMPRESS_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    raw = response.choices[0].message.content.strip()

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
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SESSION_EXIT_PROMPT},
                {"role": "user", "content": content},
            ],
        )
        raw = response.choices[0].message.content.strip()
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
        "memory/", "skills/", "requirements/",
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

    try:
        push_answer = console.input("[bold yellow]Push to origin/main? (y/n) > [/bold yellow]")
    except EOFError:
        return

    if push_answer.strip().lower() in {"y", "yes"}:
        push_result = subprocess.run(
            ["git", "-C", _ROOT, "push", "origin", "main"],
            capture_output=True, text=True,
        )
        if push_result.returncode == 0:
            console.print("[bold green]Pushed to origin/main.[/bold green]")
        else:
            console.print(f"[bold red]Push failed:[/bold red] {push_result.stderr.strip()}")


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


def classify_task(user_input: str):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_general_response(user_input: str) -> str:
    system = GENERAL_RESPONSE_PROMPT
    if _memory_context:
        system += f"\n\n## Project context\n{_memory_context}"
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_claude_scope(user_input: str, skills_context: str = ""):
    system_prompt = CLAUDE_SCOPE_PROMPT
    if _memory_context:
        system_prompt += f"\n\n## Current project memory\n{_memory_context}"
    if skills_context:
        system_prompt += f"\n\nRelevant skills loaded for this task:\n{skills_context}"

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content.strip()


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
        ["claude", "-p", full_prompt],
        capture_output=True,
        text=True,
    )


def run_codex(prompt: str) -> subprocess.CompletedProcess:
    full_prompt = f"{CLAUDE_JSON_INSTRUCTION}\n\n{prompt}"
    return subprocess.run(
        ["codex", "-q", full_prompt],
        capture_output=True,
        text=True,
    )


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
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content.strip()


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
            "[dim]Multi-Provider AI Router — openai_mini / codex / claude_code[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _show_menu() -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Opt", style="bold yellow", no_wrap=True)
    t.add_column("Action", style="white")
    t.add_row("1", "Ask Alfred")
    t.add_row("2", "View Memory")
    t.add_row("3", "View Skills")
    t.add_row("4", "View Recent Logs")
    t.add_row("5", "Show Dispatch Rules")
    t.add_row("6", "Run Claude Directly")
    t.add_row("7", "Exit")
    console.print(t)


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


def _action_ask_alfred() -> None:
    console.print(
        "\n[dim][bold]clip[/bold] = analyze clipboard  |  [bold]back[/bold] = menu[/dim]"
    )

    while True:
        try:
            user_input = console.input("\n[bold yellow]Alfred > [/bold yellow]")
        except EOFError:
            return

        stripped = user_input.strip()
        if not stripped:
            continue

        if stripped.lower() in {"back", "menu", "exit"}:
            console.print("[dim]Returning to main menu.[/dim]")
            return

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

        # Learning / Creator Mode: discuss first, then confirm before routing to Codex/Claude
        if is_learning_mode_task(stripped):
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

    for fname in files:
        skill_path = os.path.join(skills_dir, fname)
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        console.print(
            Panel(
                Markdown(content),
                title=f"[bold yellow]{fname}[/bold yellow]",
                border_style="dim",
                padding=(0, 1),
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
    "2": _action_view_memory,
    "3": _action_view_skills,
    "4": _action_view_logs,
    "5": _action_show_dispatch_rules,
    "6": _action_run_claude_directly,
}


def main():
    _show_header()
    _ensure_memory_files()
    reload_memory()
    check_github_updates()

    while True:
        console.print()
        _show_menu()

        try:
            raw = console.input("[bold yellow]Select > [/bold yellow]")
            choice = "".join(ch for ch in raw if ch.isdigit())
        except EOFError:
            break

        if choice == "7":
            console.print("\n[bold cyan]Alfred Console signing off. Goodbye.[/bold cyan]")
            break

        action = _ACTIONS.get(choice)
        if action:
            action()
        else:
            console.print("[dim]Invalid option. Enter 1-7.[/dim]")

    save_session_exit_summary()
    check_and_offer_git_commit()


if __name__ == "__main__":
    main()
