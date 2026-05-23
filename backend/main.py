from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from rich.console import Console
import os

load_dotenv()

console = Console()

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

CLAUDE_SCOPE_PROMPT = """
You are an AI orchestration planner.

Your job:
Generate a SAFE and TOKEN-EFFICIENT Claude Code prompt.

Rules:
- minimize MCP usage
- avoid broad scans
- inspect minimum scope
- stop after diagnosis unless user asked for fixes
- prefer targeted inspection
- for Power Query column errors, inspect query steps before source file contents
- prefer Transform Sample File, Transform File function, Changed Type, Removed Columns, Expanded Table Column steps
- only inspect source files after query steps confirm the issue cannot be diagnosed
- always include a hard stop condition
- never tell Claude to scan all source files

Return:
1. likely issue
2. first inspection target
3. forbidden scope
4. optimized Claude prompt
"""

def classify_task(user_input: str):

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    return response.choices[0].message.content.strip()

def generate_claude_scope(user_input: str):

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": CLAUDE_SCOPE_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    return response.choices[0].message.content.strip()

def main():

    console.print("[bold cyan]AI Orchestrator online.[/bold cyan]")

    while True:

        user_input = console.input(
            "\n[bold yellow]Ask Alfred > [/bold yellow]"
        )

        if user_input.lower() == "exit":
            break

        category = classify_task(user_input)

        console.print(
            f"\n[bold green]Task Type:[/bold green] {category}"
        )

        if category in ["POWERBI", "CLAUDE_EXECUTION"]:

            console.print(
                "\n[bold cyan]Generating Claude scope...[/bold cyan]"
            )

            scope = generate_claude_scope(user_input)

            console.print(
                f"\n[bold magenta]Claude Plan:[/bold magenta]\n{scope}"
            )

if __name__ == "__main__":
    main()