"""Git fetch, update checks, and non-interactive update helpers."""

from __future__ import annotations

import subprocess
from typing import Callable

from context import ROOT, console


def is_git_repo(root: str | None = None) -> bool:
    repo = root or ROOT
    try:
        result = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception:
        return False


def get_git_head(root: str | None = None) -> str:
    repo = root or ROOT
    try:
        result = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def count_commits_behind(root: str | None = None, *, fetch: bool = False) -> int | None:
    """Return commits behind origin/main, or None if check failed."""
    repo = root or ROOT
    if not is_git_repo(repo):
        return None
    try:
        if fetch:
            subprocess.run(
                ["git", "-C", repo, "fetch", "origin", "main", "--quiet"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        result = subprocess.run(
            ["git", "-C", repo, "rev-list", "HEAD..origin/main", "--count"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return int(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return None


def check_github_updates(reload_memory_fn: Callable[[], None] | None = None) -> bool:
    """Fetch origin/main, show any new commits, and ask before pulling.

    Re-runs setup.ps1 and reloads memory after a successful pull.
    Returns True if the repo was updated.
    """
    repo = ROOT
    try:
        subprocess.run(
            ["git", "-C", repo, "fetch", "origin", "main", "--quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return False

    behind_count = count_commits_behind(repo)
    if behind_count is None or behind_count == 0:
        return False

    console.print(
        f"\n[bold yellow]Update available:[/bold yellow] "
        f"{behind_count} new commit(s) on origin/main."
    )
    log_result = subprocess.run(
        ["git", "-C", repo, "log", "HEAD..origin/main", "--oneline"],
        capture_output=True,
        text=True,
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
        ["git", "-C", repo, "pull", "origin", "main"],
        capture_output=True,
        text=True,
    )
    if pull_result.returncode != 0:
        console.print(f"[bold red]Pull failed:[/bold red] {pull_result.stderr.strip()}")
        return False

    console.print("[bold green]Updated.[/bold green]")
    import os

    setup_path = os.path.join(repo, "setup.ps1")
    if os.path.isfile(setup_path):
        console.print("[dim]Re-running setup.ps1 to apply new packages...[/dim]")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", setup_path]
        )
    if reload_memory_fn:
        reload_memory_fn()
    return True
