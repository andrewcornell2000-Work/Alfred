"""MCP manifest loading and runtime status checks."""

from __future__ import annotations

import json
import os
import shutil

from context import ROOT
from config.env import get_github_token, get_tavily_api_key
from diagnostics.repair import claude_auth_ready, codex_auth_ready


def load_tool_manifest(root: str | None = None) -> dict:
    repo = root or ROOT
    manifest_path = os.path.join(repo, "requirements", "alfred-tools.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_mcp_servers(root: str | None = None) -> dict:
    repo = root or ROOT
    settings_path = os.path.join(repo, ".claude", "settings.json")
    if not os.path.isfile(settings_path):
        return {}
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f).get("mcpServers", {})
    except Exception:
        return {}


def mcp_runtime_status(name: str, configured_servers: dict) -> tuple[str, str]:
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

    if name == "sequential-thinking":
        return "ready", "Structured multi-step reasoning"

    if name == "memory":
        storage = svc.get("env", {}).get("MEMORY_FILE_PATH", "")
        if storage and not os.path.isdir(os.path.dirname(storage)):
            return "attention", f"Storage directory missing: {os.path.dirname(storage)}"
        return "ready", "Persistent knowledge graph across sessions"

    if name == "filesystem":
        dirs = [
            a for a in svc.get("args", [])
            if not a.startswith("-") and a not in {"-y", "@modelcontextprotocol/server-filesystem"}
        ]
        accessible = [d for d in dirs if os.path.isdir(d)]
        if not accessible:
            return "attention", "No accessible directories configured"
        return "ready", f"{len(accessible)} path(s) accessible"

    if name in {"fetch", "time", "sqlite", "duckdb"}:
        ok = bool(shutil.which("uvx"))
        labels = {
            "fetch": "Web page fetching",
            "time": "Time and timezone conversion",
            "sqlite": "Local SQLite database",
            "duckdb": "Fast SQL on CSV, Excel exports, Parquet",
        }
        label = labels[name]
        if name == "sqlite":
            db = next((a for a in svc.get("args", []) if a.endswith(".db")), "")
            if db:
                label += f" — {db}"
        if ok:
            return "ready", label
        return "attention", "uvx not installed — run: pip install uv"

    return "ready", "Configured in Claude MCP settings"


def capability_status(cap: dict, root: str | None = None) -> tuple[str, str]:
    """Return (status, note) for a capability based on what's installed/configured."""
    req = cap.get("requires", "")
    if req == "claude_cli":
        installed = bool(shutil.which("claude.cmd") or shutil.which("claude"))
        if not installed:
            return "attention", "claude not installed"
        return ("ready", "") if claude_auth_ready() else ("attention", "Claude login required")
    if req == "codex_cli":
        installed = bool(shutil.which("codex.cmd") or shutil.which("codex"))
        if not installed:
            return "attention", "codex not installed"
        return ("ready", "") if codex_auth_ready() else ("attention", "Codex login required")
    if req == "tavily_key":
        ok = bool(get_tavily_api_key(root))
        return ("ready", "") if ok else ("attention", "TAVILY_API_KEY missing")
    if req == "mcp_excel":
        mcp = load_mcp_servers(root)
        return ("ready", "") if "excel" in mcp else ("planned", "Excel MCP not configured")
    if req == "mcp_powerbi":
        mcp = load_mcp_servers(root)
        return ("ready", "") if "powerbi-modeling-mcp" in mcp else ("planned", "Power BI MCP not configured")
    if req == "mcp_playwright":
        mcp = load_mcp_servers(root)
        return ("ready", "") if "playwright" in mcp else ("planned", "Playwright MCP not configured")
    if req == "mcp_github":
        mcp = load_mcp_servers(root)
        return ("ready", "") if "github" in mcp else ("planned", "GitHub MCP not configured")
    return ("ready", "")


def tool_registry_status(tool: dict, root: str | None = None) -> tuple[str, str]:
    """Return (status, note) for a tool based on what's installed."""
    dummy_cap = {"requires": tool.get("requires", "")}
    return capability_status(dummy_cap, root)


def status_style(status: str, *, rich: bool = False) -> str:
    if rich:
        return {
            "ready": "[green]ready[/green]",
            "attention": "[yellow]attention[/yellow]",
            "planned": "[dim]planned[/dim]",
        }.get(status, status)
    return status
