"""Environment variable and secret helpers."""

from __future__ import annotations

import json
import os
import re

from context import ROOT


def write_env_var(env_path: str, key: str, value: str) -> None:
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


def get_tavily_api_key(root: str | None = None) -> str:
    """Read Tavily API key from env or .claude/settings.json."""
    key = os.getenv("TAVILY_API_KEY", "")
    if key:
        return key
    repo = root or ROOT
    settings_path = os.path.join(repo, ".claude", "settings.json")
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


def get_github_token(root: str | None = None) -> str:
    """Find a GitHub PAT from .env or Claude MCP settings."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        return token
    repo = root or ROOT
    settings_path = os.path.join(repo, ".claude", "settings.json")
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
