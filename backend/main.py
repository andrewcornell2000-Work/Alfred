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

Keep responses to 2–4 sentences unless the question genuinely demands more. When asked what you can do, mention: task classification (GENERAL / POWERBI / CLAUDE_EXECUTION), optimized Claude Code prompt generation, skill-based context injection, memory consolidation, and auto-dispatch to Claude.
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


def read_memory_summary() -> str:
    path = os.path.join(_ROOT, "memory", "session-summary.md")
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def append_interaction_log(user_input: str, category: str, scope: str = "") -> None:
    logs_dir = os.path.join(_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    path = os.path.join(logs_dir, "interactions.md")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## {timestamp}\n"
        f"**Category:** {category}\n"
        f"**Input:** {user_input}\n"
        f"**Scope:** {scope[:500]}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


CONSOLIDATION_PROMPT = """You are a memory consolidation assistant for Alfred, an AI orchestrator.

Given the existing session summary and recent interaction logs, produce an updated cumulative summary.

Preserve all useful history from the existing summary. Incorporate any new architectural changes, implemented features, design decisions, or planned work found in the interactions. Keep the summary concise — use bullet points, not prose.

Maintain these sections (omit empty ones):
- Current Architecture
- Current Features
- Current Skills
- Important Design Rules
- Next Planned Features

Return only the updated markdown. Do not wrap in code blocks.
"""

CONSOLIDATION_THRESHOLD = 10
INTERACTIONS_TO_KEEP = 5


def consolidate_memory_if_needed() -> None:
    logs_path = os.path.join(_ROOT, "logs", "interactions.md")
    if not os.path.isfile(logs_path):
        return

    with open(logs_path, "r", encoding="utf-8") as f:
        content = f.read()

    count = len(re.findall(r"^## \d{4}-\d{2}-\d{2}", content, re.MULTILINE))
    if count < CONSOLIDATION_THRESHOLD:
        return

    existing_summary = read_memory_summary()
    user_content = (
        f"Existing summary:\n{existing_summary}\n\nRecent interactions:\n{content}"
    )

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": CONSOLIDATION_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    new_summary = response.choices[0].message.content.strip()

    summary_path = os.path.join(_ROOT, "memory", "session-summary.md")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(new_summary)

    entries = re.split(r"(?=^## \d{4}-\d{2}-\d{2})", content, flags=re.MULTILINE)
    entries = [e for e in entries if e.strip()]
    recent = entries[-INTERACTIONS_TO_KEEP:]
    with open(logs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(recent).lstrip("\n") + "\n")

    console.print("[dim]Memory consolidated.[/dim]")


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
    memory = read_memory_summary()
    system = GENERAL_RESPONSE_PROMPT
    if memory:
        system += f"\n\n## Project context\n{memory}"
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
    memory = read_memory_summary()
    if memory:
        system_prompt += f"\n\n## Current project memory\n{memory}"
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


DANGEROUS_KEYWORDS = [
    "delete", "remove", "overwrite", "credentials", "password",
    "entire onedrive", "all folders", "whole workspace",
]

ACTION_KEYWORDS = ["inspect", "run", "edit", "use mcp", "use claude"]


def should_send_to_claude(user_input: str, category: str) -> bool:
    lowered = user_input.lower()
    if any(kw in lowered for kw in DANGEROUS_KEYWORDS):
        return False
    if category == "CLAUDE_EXECUTION":
        return True
    if category == "POWERBI" and any(kw in lowered for kw in ACTION_KEYWORDS):
        return True
    return False


# ── Display helpers ────────────────────────────────────────────────────────────

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
            "[bold cyan]Alfred Console[/bold cyan]  [dim]v1[/dim]\n"
            "[dim]AI Task Routing & Prompt Optimization Orchestrator[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _show_menu() -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Opt", style="bold yellow", no_wrap=True)
    t.add_column("Action", style="white")
    t.add_row("1", "Ask Alfred")
    t.add_row("2", "View Memory Summary")
    t.add_row("3", "View Skills")
    t.add_row("4", "View Recent Logs")
    t.add_row("5", "Show Dispatch Rules")
    t.add_row("6", "Run Claude Directly")
    t.add_row("7", "Exit")
    console.print(t)


# ── Menu actions ───────────────────────────────────────────────────────────────

def _action_ask_alfred() -> None:
    console.print("\n[dim]You're now in Alfred mode. Type 'back', 'menu', or 'exit' to return to the main menu.[/dim]")

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

        category = classify_task(stripped)
        console.print(f"\n[bold green]Task Type:[/bold green] {category}")

        scope = ""

        if category == "GENERAL":
            response = generate_general_response(stripped)
            _render_general_response(response)

        elif category in ["POWERBI", "CLAUDE_EXECUTION"]:
            console.print("\n[bold cyan]Generating Claude scope...[/bold cyan]")
            skills_context = load_relevant_skills(stripped)
            scope = generate_claude_scope(stripped, skills_context)
            console.print(f"\n[bold magenta]Claude Plan:[/bold magenta]\n{scope}")

            if should_send_to_claude(stripped, category):
                console.print("\n[bold cyan]Auto-dispatching to Claude...[/bold cyan]")
                _render_claude_result(run_claude(scope))
            else:
                console.print(
                    "\n[bold yellow]Plan ready. Send to Claude manually if needed.[/bold yellow]"
                )

        append_interaction_log(stripped, category, scope)
        consolidate_memory_if_needed()


def _action_view_memory() -> None:
    console.print(Rule("[bold cyan]Memory Summary[/bold cyan]"))
    content = read_memory_summary()
    if not content:
        console.print("[dim]No memory summary found.[/dim]")
    else:
        console.print(Markdown(content))


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

    t = Table(title="Auto-Dispatch Logic", box=box.ROUNDED, border_style="dim", padding=(0, 1))
    t.add_column("Condition", style="bold cyan")
    t.add_column("Outcome", style="white")
    t.add_row("Category = CLAUDE_EXECUTION", "[green]Auto-dispatch to Claude[/green]")
    t.add_row("Category = POWERBI + action keyword", "[green]Auto-dispatch to Claude[/green]")
    t.add_row("Category = GENERAL", "[yellow]Plan only — no dispatch[/yellow]")
    t.add_row("Dangerous keyword detected", "[red]Blocked — no dispatch[/red]")
    console.print(t)

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


if __name__ == "__main__":
    main()
