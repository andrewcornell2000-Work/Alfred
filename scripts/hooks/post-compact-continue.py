#!/usr/bin/env python3
"""
SessionStart (matcher: compact) hook: re-inject continue brief after compaction.

Claude Code re-starts the session context after compact; stdout from this hook
is added back into the agent context. Pair with pre-compact-handoff.py which
writes HANDOFF.md just before summarization.

Never blocks. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_HANDOFF_CHARS = 6000


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    cwd = Path(data.get("cwd") or os.getcwd()).resolve()
    handoff = cwd / "HANDOFF.md"

    lines = [
        "Alfred auto-compact complete (early threshold).",
        "STOP exploring. Continue the in-progress task immediately.",
        "Do not ask the user to restate the goal.",
        "Read HANDOFF.md if you need detail; then execute the next ordered step.",
    ]

    if handoff.is_file():
        try:
            text = handoff.read_text(encoding="utf-8")
            if len(text) > MAX_HANDOFF_CHARS:
                text = text[:MAX_HANDOFF_CHARS] + "\n\n…(HANDOFF truncated for context reinjection)…"
            lines.append("")
            lines.append("--- HANDOFF.md (present state) ---")
            lines.append(text)
        except Exception:
            lines.append(f"HANDOFF.md exists at {handoff} but could not be read — open it and continue.")
    else:
        lines.append(
            f"No HANDOFF.md at {handoff}. Infer the next step from the compact summary and continue; "
            "do not restart from scratch."
        )

    marker = cwd / ".alfred" / "last-compact.json"
    if marker.is_file():
        try:
            meta = json.loads(marker.read_text(encoding="utf-8"))
            goal = (meta.get("goal") or "").strip()
            if goal:
                lines.insert(1, f"Recovered goal: {goal}")
        except Exception:
            pass

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
