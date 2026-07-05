"""Plain-text diagnostic and status reporting."""

from __future__ import annotations

import json
import os
from pathlib import Path

from context import ROOT
from diagnostics.mcp_status import (
    load_mcp_servers,
    load_tool_manifest,
    mcp_runtime_status,
    capability_status,
)
from diagnostics.setup_check import scan_setup_issues
from provision.registry import TOOL_REGISTRY, iter_control_tower_capabilities
from skills_loader import count_skills
from updater.git import count_commits_behind, get_git_head, is_git_repo


def _count_cursor_rules(root: str | None = None) -> int:
    repo = Path(root or ROOT)
    rules_dir = repo / ".cursor" / "rules"
    if not rules_dir.is_dir():
        rules_dir = repo / "cursor" / "rules"
    if not rules_dir.is_dir():
        return 0
    return len(list(rules_dir.glob("*.mdc")))


def _venv_ready(root: str | None = None) -> bool:
    repo = root or ROOT
    return os.path.isfile(os.path.join(repo, ".venv", "Scripts", "python.exe"))


def _read_last_cli_run(root: str | None = None) -> dict | None:
    path = os.path.join(root or ROOT, "memory", "cli-last-run.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def format_status_summary(root: str | None = None) -> str:
    """Short one-screen status for `alfred status`."""
    repo = root or ROOT
    lines: list[str] = ["Alfred status", "============="]

    venv_ok = _venv_ready(repo)
    lines.append(f"Installed: {'yes' if venv_ok else 'no (.venv missing)'}")

    mcp_servers = load_mcp_servers(repo)
    manifest = load_tool_manifest(repo)
    manifest_mcp = manifest.get("mcp", {}).get("tools", [])
    ready_count = sum(
        1 for t in manifest_mcp
        if mcp_runtime_status(t.get("name", ""), mcp_servers)[0] == "ready"
    )
    lines.append(f"MCP: {ready_count}/{len(manifest_mcp)} ready ({len(mcp_servers)} configured)")

    inventory = count_skills(repo)
    lines.append(f"Skills: {inventory['flat']} repo skills, {inventory['packs']} pack skills")
    lines.append(f"Rules: {_count_cursor_rules(repo)} .mdc files in repo")
    lines.append(f"Capabilities: {len(TOOL_REGISTRY)} registered")

    if is_git_repo(repo):
        head = get_git_head(repo)
        behind = count_commits_behind(repo)
        lines.append(f"Git HEAD: {head[:12] if head else 'unknown'}")
        if behind is not None:
            if behind == 0:
                lines.append("Updates: up to date with origin/main")
            else:
                lines.append(f"Updates: {behind} commit(s) behind origin/main")
    else:
        lines.append("Git: not a git repo")

    scan = scan_setup_issues(repo)
    if scan.all_clear:
        lines.append("Setup: all required checks passed")
    else:
        lines.append(f"Setup: {len(scan.required_issues)} issue(s) need attention")

    last = _read_last_cli_run(repo)
    if last:
        lines.append(
            f"Last CLI run: {last.get('command', '?')} - "
            f"{last.get('result', '?')} at {last.get('timestamp', '?')}"
        )

    return "\n".join(lines)


def format_diagnose_report(root: str | None = None) -> str:
    """Developer-focused health report for `alfred diagnose`."""
    repo = root or ROOT
    lines: list[str] = ["Alfred diagnostics", "==================", ""]

    lines.append("Environment")
    lines.append(f"  Root: {repo}")
    lines.append(f"  venv: {'ready' if _venv_ready(repo) else 'missing'}")
    lines.append("")

    lines.append("Git / updates")
    if is_git_repo(repo):
        head = get_git_head(repo)
        behind = count_commits_behind(repo)
        lines.append(f"  HEAD: {head or 'unknown'}")
        if behind is None:
            lines.append("  origin/main: unavailable (offline or no remote)")
        elif behind == 0:
            lines.append("  origin/main: up to date")
        else:
            lines.append(f"  origin/main: {behind} commit(s) behind")
    else:
        lines.append("  not a git repository")
    lines.append("")

    lines.append("Registry")
    lines.append(f"  TOOL_REGISTRY entries: {len(TOOL_REGISTRY)}")
    for cap in iter_control_tower_capabilities():
        status, note = capability_status(cap, repo)
        suffix = f" ({note})" if note else ""
        lines.append(f"  {cap['name']}: {status}{suffix}")
    lines.append("")

    manifest = load_tool_manifest(repo)
    mcp_servers = load_mcp_servers(repo)
    manifest_tools = manifest.get("mcp", {}).get("tools", [])

    lines.append(f"MCP stack ({len(manifest_tools)} in manifest, {len(mcp_servers)} configured)")
    for tool in manifest_tools:
        name = tool.get("name", "")
        status, note = mcp_runtime_status(name, mcp_servers)
        risk = "write" if tool.get("destructive") else "read"
        suffix = f" - {note}" if note else ""
        lines.append(f"  {name}: {status} [{risk}]{suffix}")
    lines.append("")

    inventory = count_skills(repo)
    lines.append("Skills / rules")
    lines.append(f"  skills/*.md: {inventory['flat']}")
    lines.append(f"  skills/_packs/**/SKILL.md: {inventory['packs']}")
    lines.append(f"  cursor rules (.mdc): {_count_cursor_rules(repo)}")
    if inventory["unreadable"]:
        lines.append("  Unreadable skill files:")
        for err in inventory["unreadable"]:
            lines.append(f"    - {err}")
    lines.append("")

    scan = scan_setup_issues(repo)
    lines.append("Setup scan")
    if scan.mcp_ready:
        lines.append(f"  MCP ready: {', '.join(scan.mcp_ready)}")
    if scan.required_issues:
        lines.append("  Required issues:")
        for desc, key in scan.required_issues:
            tag = f" [repair: {key}]" if key else " [manual]"
            lines.append(f"    - {desc}{tag}")
    else:
        lines.append("  Required: none")
    if scan.optional_issues:
        lines.append("  Optional:")
        for desc, key in scan.optional_issues:
            tag = f" [repair: {key}]" if key else ""
            lines.append(f"    - {desc}{tag}")
    lines.append("")

    gaps = []
    for tool in manifest_tools:
        status, note = mcp_runtime_status(tool.get("name", ""), mcp_servers)
        if status != "ready":
            gaps.append(f"{tool.get('name')}: {note}")
    if gaps:
        lines.append("Gaps")
        for gap in gaps:
            lines.append(f"  - {gap}")
    else:
        lines.append("Gaps: none - all registered MCP tools are ready.")

    return "\n".join(lines)
