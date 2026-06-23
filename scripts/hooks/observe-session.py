#!/usr/bin/env python3
"""
Stop hook: lightweight continuous-learning observation logger.

OPT-IN. Disabled unless ALFRED_INSTINCT_OBSERVE=1 — the Stop event fires after
every assistant response, so this stays cheap and append-only and never does
heavy transcript parsing inline. It records a one-line marker that the Alfred
autonomous loop / `/instinct-learn` later mines into instincts.

Never blocks. Always exits 0.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG = REPO_ROOT / "memory" / "instincts" / "observations.jsonl"
MAX_LINES = 2000  # keep the log bounded


def main() -> int:
    if os.environ.get("ALFRED_INSTINCT_OBSERVE") != "1":
        return 0
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "cwd": os.getcwd(),
        "transcript": data.get("transcript_path", ""),
        "stop_active": data.get("stop_hook_active", False),
    }
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        # bound the file
        if LOG.stat().st_size > 512 * 1024:
            lines = LOG.read_text(encoding="utf-8").splitlines()[-MAX_LINES:]
            LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 0)
