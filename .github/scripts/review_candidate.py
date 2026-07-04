#!/usr/bin/env python3
"""Validate a review-queue candidate before it can move to approved/staged.

Used by cloud agents and CI — does not install anything.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "requirements" / "review-queue.json"
CATALOG = ROOT / "requirements" / "catalog-index.json"
MCP_TEMPLATE = ROOT / "cursor" / "mcp.json"

SUSPICIOUS_PATTERNS = [
    r"curl\s+.*\|\s*(bash|sh)",
    r"Invoke-Expression",
    r"eval\s*\(",
    r"rm\s+-rf\s+/",
    r"Format-Volume",
    r"Remove-Item\s+.*-Recurse\s+.*C:\\",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_duplicates(item: dict) -> list[str]:
    errors = []
    slug = item.get("slug", "").lower()
    if not slug:
        errors.append("missing slug")
        return errors

    if CATALOG.exists():
        idx = load_json(CATALOG)
        for key, meta in idx.get("skills", {}).items():
            if key == slug or slug in meta.get("aliases", []):
                errors.append(f"duplicate skill slug in catalog-index: {key}")

    if MCP_TEMPLATE.exists():
        mcp = load_json(MCP_TEMPLATE)
        if slug in mcp.get("mcpServers", {}):
            errors.append(f"duplicate MCP key in cursor/mcp.json: {slug}")

    if QUEUE.exists():
        q = load_json(QUEUE)
        for existing in q.get("items", []):
            if existing.get("slug") == slug and existing.get("status") in (
                "installed",
                "approved",
                "staged",
            ):
                errors.append(f"already in review queue as {existing.get('status')}")

    return errors


def check_security(item: dict) -> list[str]:
    errors = []
    notes = item.get("install_notes", "") + item.get("description", "")
    for pat in SUSPICIOUS_PATTERNS:
        if re.search(pat, notes, re.I):
            errors.append(f"suspicious pattern in notes: {pat}")

    trust = item.get("trust_level", "untrusted")
    if trust == "untrusted" and item.get("status") == "approved":
        errors.append("untrusted source cannot be auto-approved")

    if item.get("requires_admin"):
        errors.append("requires admin — rejected by policy")

    return errors


def validate_item(item: dict) -> tuple[bool, list[str]]:
    all_errors = []
    all_errors.extend(check_duplicates(item))
    all_errors.extend(check_security(item))

    required = ["slug", "type", "source_url", "trust_level", "status"]
    for field in required:
        if not item.get(field):
            all_errors.append(f"missing required field: {field}")

    allowed_status = {
        "discovered",
        "source_validation",
        "security_review",
        "duplication_check",
        "test_install",
        "approved",
        "staged",
        "installed",
        "rejected",
        "duplicate",
    }
    if item.get("status") not in allowed_status:
        all_errors.append(f"invalid status: {item.get('status')}")

    return (len(all_errors) == 0, all_errors)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: review_candidate.py <path-to-candidate.json>")
        return 2

    path = Path(sys.argv[1])
    item = load_json(path)
    ok, errors = validate_item(item)
    if ok:
        print("review_candidate.py OK")
        return 0
    print("review_candidate.py FAILED:")
    for e in errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
