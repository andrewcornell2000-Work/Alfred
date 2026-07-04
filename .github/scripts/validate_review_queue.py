#!/usr/bin/env python3
"""Validate review-queue.json structure and candidate safety."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "requirements" / "review-queue.json"
MAX_ITEMS = 50


def main() -> int:
    if not QUEUE.exists():
        print("validate_review_queue.py OK (no queue file)")
        return 0

    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    errors: list[str] = []

    if len(items) > MAX_ITEMS:
        errors.append(f"review queue exceeds {MAX_ITEMS} items — prune stale entries")

    slugs: set[str] = set()
    for i, item in enumerate(items):
        slug = item.get("slug", "")
        if not slug:
            errors.append(f"item[{i}] missing slug")
            continue
        if slug in slugs:
            errors.append(f"duplicate slug in queue: {slug}")
        slugs.add(slug)

        if item.get("requires_admin"):
            errors.append(f"{slug}: requires_admin not allowed")

        if item.get("status") == "approved" and item.get("trust_level") == "untrusted":
            errors.append(f"{slug}: untrusted source cannot be approved")

    if errors:
        print("validate_review_queue.py FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"validate_review_queue.py OK ({len(items)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
