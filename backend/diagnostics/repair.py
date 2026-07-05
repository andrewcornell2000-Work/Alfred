"""Executable resolution, auth checks, and repair helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import webbrowser
from typing import Callable

from context import ROOT
from config.env import write_env_var

EmitFn = Callable[[str], None]


def _default_emit(msg: str) -> None:
    print(msg)


def resolve_claude_executable() -> str:
    return (
        os.getenv("CLAUDE_BIN")
        or shutil.which("claude.cmd")
        or shutil.which("claude")
        or "claude.cmd"
    )


def resolve_codex_executable() -> str:
    return (
        os.getenv("CODEX_BIN")
        or shutil.which("codex.cmd")
        or shutil.which("codex")
        or "codex.cmd"
    )


def resolve_npm_executable() -> str:
    return (
        os.getenv("NPM_BIN")
        or shutil.which("npm.cmd")
        or shutil.which("npm")
        or "npm.cmd"
    )


def resolve_pip_executable(root: str | None = None) -> str:
    repo = root or ROOT
    venv_pip = os.path.join(repo, ".venv", "Scripts", "pip.exe")
    if os.path.isfile(venv_pip):
        return venv_pip
    return shutil.which("pip.exe") or shutil.which("pip") or "pip"


def claude_auth_ready() -> bool:
    exe = resolve_claude_executable()
    try:
        result = subprocess.run(
            [exe, "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=8,
        )
    except Exception:
        return False
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
        return bool(data.get("loggedIn"))
    except json.JSONDecodeError:
        return "logged in" in result.stdout.lower()


def codex_auth_ready() -> bool:
    exe = resolve_codex_executable()
    try:
        result = subprocess.run(
            [exe, "login", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=8,
        )
    except Exception:
        return False
    text = (result.stdout + "\n" + result.stderr).lower()
    return result.returncode == 0 and "logged in" in text


def repair_install_claude(emit: EmitFn = _default_emit) -> None:
    emit("Running: npm install -g @anthropic-ai/claude-code")
    r = subprocess.run(
        [resolve_npm_executable(), "install", "-g", "@anthropic-ai/claude-code"],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        emit("Installed. Restart Alfred, then authenticate with: claude auth login")
    else:
        emit(f"Install failed: {r.stderr.strip()[:200]}")


def repair_claude_login(emit: EmitFn = _default_emit) -> None:
    exe = resolve_claude_executable()
    try:
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe, "auth", "login"])
        emit("Terminal opened — sign in, then restart Alfred.")
    except Exception as e:
        emit(f"Could not open terminal: {e}")


def repair_install_codex(emit: EmitFn = _default_emit) -> None:
    emit("Running: npm install -g @openai/codex")
    r = subprocess.run(
        [resolve_npm_executable(), "install", "-g", "@openai/codex"],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        emit("Installed. Restart Alfred, then authenticate with: codex login")
    else:
        emit(f"Install failed: {r.stderr.strip()[:200]}")


def repair_codex_login(emit: EmitFn = _default_emit) -> None:
    exe = resolve_codex_executable()
    try:
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", exe])
        emit("Terminal opened — sign in, then restart Alfred.")
    except Exception as e:
        emit(f"Could not open terminal: {e}")


def repair_tavily_key(
    emit: EmitFn = _default_emit,
    input_fn: Callable[[str], str] | None = None,
    root: str | None = None,
) -> None:
    repo = root or ROOT
    if input_fn is None:
        emit("Tavily key repair requires interactive input.")
        return
    ans = input_fn("Open app.tavily.com in browser? (y/n) > ").strip()
    if ans.lower() in {"y", "yes"}:
        webbrowser.open("https://app.tavily.com")
    key = input_fn("Paste Tavily API key (tvly-...): ").strip()
    if not key.startswith("tvly-"):
        emit("Invalid key — must start with tvly-")
        return
    write_env_var(os.path.join(repo, ".env"), "TAVILY_API_KEY", key)
    os.environ["TAVILY_API_KEY"] = key
    emit("Tavily key saved — web research now active.")


def repair_github_token(
    emit: EmitFn = _default_emit,
    input_fn: Callable[[str], str] | None = None,
    root: str | None = None,
) -> None:
    repo = root or ROOT
    if input_fn is None:
        emit("GitHub token repair requires interactive input.")
        return
    ans = input_fn("Open github.com/settings/tokens in browser? (y/n) > ").strip()
    if ans.lower() in {"y", "yes"}:
        webbrowser.open("https://github.com/settings/tokens/new")
    key = input_fn("Paste GitHub Personal Access Token (ghp_...): ").strip()
    if not key:
        return
    write_env_var(os.path.join(repo, ".env"), "GITHUB_TOKEN", key)
    os.environ["GITHUB_TOKEN"] = key
    emit("GitHub token saved.")


def repair_install_uv(emit: EmitFn = _default_emit, root: str | None = None) -> None:
    emit("Running: pip install uv")
    pip = resolve_pip_executable(root)
    r = subprocess.run([pip, "install", "uv"], capture_output=True, text=True)
    if r.returncode == 0:
        emit("uv installed — restart Alfred to activate fetch and time MCPs.")
    else:
        emit(f"Install failed: {r.stderr.strip()[:200]}")
        emit("Try manually: pip install uv")


def repair_excel_mcp(emit: EmitFn = _default_emit, root: str | None = None) -> None:
    pip = resolve_pip_executable(root)
    emit("Running: pip install excellm")
    r = subprocess.run([pip, "install", "excellm"], capture_output=True, text=True)
    if r.returncode == 0:
        emit("Excel MCP installed — restart Alfred to activate.")
    else:
        emit(f"Install failed: {r.stderr.strip()[:200]}")


REPAIR_BY_KEY = {
    "install_claude": repair_install_claude,
    "claude_login": repair_claude_login,
    "install_codex": repair_install_codex,
    "codex_login": repair_codex_login,
    "tavily_key": repair_tavily_key,
    "github_token": repair_github_token,
    "install_uv": repair_install_uv,
    "excel_mcp": repair_excel_mcp,
}
