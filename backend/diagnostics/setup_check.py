"""Non-interactive setup issue scanning."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field

from context import ROOT
from config.env import get_github_token, get_tavily_api_key
from diagnostics.mcp_status import load_mcp_servers
from diagnostics.repair import claude_auth_ready, codex_auth_ready


@dataclass
class SetupScanResult:
    required_issues: list[tuple[str, str | None]] = field(default_factory=list)
    optional_issues: list[tuple[str, str | None]] = field(default_factory=list)
    mcp_ready: list[str] = field(default_factory=list)

    @property
    def all_clear(self) -> bool:
        return not self.required_issues


def scan_setup_issues(root: str | None = None) -> SetupScanResult:
    """Scan for setup issues without interactive prompts."""
    repo = root or ROOT
    result = SetupScanResult()

    claude_installed = bool(shutil.which("claude.cmd") or shutil.which("claude"))
    if not claude_installed:
        result.required_issues.append(("Claude Code CLI not installed", "install_claude"))
    elif not claude_auth_ready():
        result.required_issues.append(("Claude not logged in", "claude_login"))

    codex_installed = bool(shutil.which("codex.cmd") or shutil.which("codex"))
    if not codex_installed:
        result.required_issues.append(("Codex CLI not installed", "install_codex"))
    elif not codex_auth_ready():
        result.required_issues.append(("Codex not logged in", "codex_login"))

    if not get_tavily_api_key(repo):
        result.optional_issues.append(
            ("Tavily key missing — web research unavailable", "tavily_key")
        )
    if not get_github_token(repo):
        result.optional_issues.append(
            ("GitHub token missing — GitHub operations unavailable", "github_token")
        )

    if not shutil.which("uvx"):
        mcp_servers = load_mcp_servers(repo)
        if any(svc.get("command") == "uvx" for svc in mcp_servers.values()):
            result.optional_issues.append(
                ("uvx not installed — fetch and time MCPs need it", "install_uv")
            )

    settings_path = os.path.join(repo, ".claude", "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                mcp_cfg = json.load(f)
            for svc_name, svc in mcp_cfg.get("mcpServers", {}).items():
                if svc_name == "powerbi-modeling-mcp":
                    cmd = svc.get("command", "")
                    if cmd and not os.path.isfile(cmd):
                        result.required_issues.append(
                            (f"Power BI MCP: server not found at {cmd}", None)
                        )
                    else:
                        result.mcp_ready.append("Power BI")
                elif svc_name == "excel":
                    try:
                        import excellm  # noqa: F401
                        result.mcp_ready.append("Excel")
                    except ImportError:
                        result.required_issues.append(
                            ("Excel MCP: excellm not installed", "excel_mcp")
                        )
                elif svc_name == "playwright":
                    result.mcp_ready.append("Browser")
        except Exception:
            pass

    return result
