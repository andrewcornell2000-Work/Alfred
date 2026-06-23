#!/usr/bin/env python3
"""
SessionStart hook: surface learned instincts into the new session's context.

This is the payoff of the continuous-learning loop — at the start of every
session Alfred prints its active/strong instincts (project + global) so they
are injected as context and actually influence the work, instead of sitting
inert in a memory file.

Cheap, runs once per session, never blocks. Output on stdout is added to the
agent's context by Claude Code.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLI = REPO_ROOT / "scripts" / "instinct-cli.py"
GLOBAL_FILE = REPO_ROOT / "memory" / "instincts" / "global.json"
PROJECTS_DIR = REPO_ROOT / "memory" / "instincts" / "projects"

ACTIVE_THRESHOLD = 0.50
MAX_SHOWN = 12


def _load(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def main() -> int:
    try:
        # drain stdin so the hook doesn't stall
        sys.stdin.read()
    except Exception:
        pass

    instincts = {}
    for ins in _load(GLOBAL_FILE):
        instincts[ins.get("id")] = ins
    if PROJECTS_DIR.exists():
        for pf in PROJECTS_DIR.glob("*.json"):
            for ins in _load(pf):
                instincts[ins.get("id")] = ins

    active = [i for i in instincts.values()
              if float(i.get("confidence", 0)) >= ACTIVE_THRESHOLD]
    if not active:
        return 0

    active.sort(key=lambda i: -float(i.get("confidence", 0)))
    lines = ["Alfred learned instincts (apply when relevant):"]
    for ins in active[:MAX_SHOWN]:
        conf = float(ins.get("confidence", 0))
        lines.append(f"- ({conf:.2f}) when {ins.get('trigger','')} -> {ins.get('guidance','')}")
    if len(active) > MAX_SHOWN:
        lines.append(f"- (+{len(active) - MAX_SHOWN} more — run `python scripts/instinct-cli.py status`)")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never break session start
