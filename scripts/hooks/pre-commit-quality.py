#!/usr/bin/env python3
"""
PreToolUse hook (Bash): pre-commit quality + secret scan.

Runs only on `git commit` commands. Scans staged files for hardcoded secrets,
debugger statements, and console.log. Blocks (exit 2) on hard errors
(secrets / debugger); warns (exit 0) on the rest. Skips `--amend`.

Ported from ECC scripts/hooks/pre-bash-commit-quality.js — Python, stdlib only.

Exit codes:
  0  allow (or warn)
  2  block (critical issue found)
"""
import json
import re
import subprocess
import sys

CHECK_EXT = (".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs", ".ps1", ".psm1")

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style API key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{22,}"), "GitHub fine-grained PAT"),
    (re.compile(r"AKIA[A-Z0-9]{16}"), "AWS access key"),
    (re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"), "Slack token"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][^'\"]{8,}['\"]"), "hardcoded credential"),
]


def staged_files() -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return []
        return [f for f in r.stdout.splitlines() if f.strip()]
    except Exception:
        return []


def staged_content(path: str) -> str | None:
    try:
        r = subprocess.run(["git", "show", f":{path}"], capture_output=True,
                           text=True, timeout=10)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    command = (data.get("tool_input") or {}).get("command", "") or ""
    if "git commit" not in command or "--amend" in command:
        return 0

    files = [f for f in staged_files() if f.endswith(CHECK_EXT)]
    if not files:
        return 0

    errors, warnings = [], []
    for f in files:
        content = staged_content(f)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            for pat, name in SECRET_PATTERNS:
                if pat.search(line):
                    errors.append(f"{f}:{i}  potential {name} committed")
            if re.search(r"\bdebugger\b", line) and not stripped.startswith("//"):
                errors.append(f"{f}:{i}  debugger statement")
            if "console.log" in line and not stripped.startswith(("//", "*")):
                warnings.append(f"{f}:{i}  console.log left in code")

    if warnings:
        sys.stderr.write("[alfred] commit warnings:\n  " + "\n  ".join(warnings) + "\n")
    if errors:
        sys.stderr.write(
            "[alfred] COMMIT BLOCKED — fix these before committing:\n  "
            + "\n  ".join(errors)
            + "\n  (intentional? re-run with `git commit --no-verify`)\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
