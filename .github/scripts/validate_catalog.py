#!/usr/bin/env python3
"""Pre-commit / CI guard: no duplicate skills, MCP keys, or catalog slugs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors: list[str] = []


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_mcp() -> None:
    mcp_path = ROOT / "cursor" / "mcp.json"
    data = load_json(mcp_path)
    servers = data.get("mcpServers", {})
    retired = set(data.get("_retiredServers", []))

    keys = list(servers.keys())
    if len(keys) != len(set(keys)):
        errors.append("cursor/mcp.json: duplicate MCP server keys")

    for r in retired:
        if r in servers:
            errors.append(f"cursor/mcp.json: retired server '{r}' must not be in mcpServers")

    fingerprints: dict[str, str] = {}
    for name, cfg in servers.items():
        cmd = cfg.get("command", "")
        args = cfg.get("args", [])
        url = cfg.get("url", "")
        if url:
            fp = f"url:{url.split('?')[0]}"
        else:
            fp = f"{cmd}:{':'.join(str(a) for a in args[:3])}"
        if fp in fingerprints.values():
            dup = [k for k, v in fingerprints.items() if v == fp]
            errors.append(f"cursor/mcp.json: '{name}' duplicates fingerprint of {dup}")
        fingerprints[name] = fp


def check_discovered_tools() -> None:
    path = ROOT / "requirements" / "discovered-tools.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    slugs = re.findall(r"^###\s+([a-z0-9-]+)", text, flags=re.MULTILINE)
    seen: set[str] = set()
    for slug in slugs:
        if slug in seen:
            errors.append(f"discovered-tools.md: duplicate slug '### {slug}'")
        seen.add(slug)


def check_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.exists():
        return

    index_path = ROOT / "requirements" / "catalog-index.json"
    never_write = ["taste-"]
    if index_path.exists():
        idx = load_json(index_path)
        never_write = [p.replace("*", "") for p in idx.get("never_write_skills", [])]

    for f in skills_dir.glob("*.md"):
        if any(f.name.startswith(p) for p in never_write):
            errors.append(
                f"skills/{f.name}: vendored taste skills belong in docs/vendor/ — not skills/"
            )
        if f.stat().st_size > 20000:
            errors.append(f"skills/{f.name}: exceeds 20KB — trim or move to docs/")


def check_cursorrules() -> None:
    path = ROOT / ".cursorrules"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "CRITICAL: ALWAYS use lean-ctx" in text or "NEVER use native Read" in text:
        errors.append(
            ".cursorrules: must not mandate lean-ctx over native tools (see 00-agent-tooling.mdc)"
        )


def main() -> int:
    check_mcp()
    check_discovered_tools()
    check_skills()
    check_cursorrules()
    if errors:
        print("validate_catalog.py FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("validate_catalog.py OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
