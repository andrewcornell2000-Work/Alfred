"""Acceptance: Alfred-owned docs must not normalize device-code auth.

Corporate Conditional Access bans device-code. Education lines that say Never /
FORBIDDEN / quarantine are allowed; recommending the flow is not.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Patterns that must not appear as actionable guidance.
FORBIDDEN = (
    "az login --use-device-code",
    "MSAL device-code",
    "interactive, device-code",
)

# Whole-file allowlist (remediation / education tooling).
ALLOWLIST_FILES = {
    Path("scripts/Fix-AzureKubeAuth.ps1"),
    Path("backend/tests/test_no_device_code_auth.py"),
}

# Line is education / ban wording, not a recipe to run.
_EDU_LINE = re.compile(
    r"(?i)(\bnever\b|\bforbidden\b|quarantine|tenant-forbidden|"
    r"do\s+not\s+(run|suggest|recommend|use)|don't\s+(run|suggest|recommend|use)|"
    r"hard rules|banned|omit(?:ted)?\s+on\s+purpose)"
)

_SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "data.local-backup-20260620-130716",
    "__pycache__",
    ".cursor",
    "dist",
    "bin",
}

_TEXT_SUFFIXES = {
    ".md",
    ".ps1",
    ".py",
    ".json",
    ".txt",
    ".mdc",
    ".yml",
    ".yaml",
    ".bat",
    ".cmd",
}


def _is_allowlisted(rel: Path) -> bool:
    normalized = Path(*rel.parts)  # normalize separators
    return normalized.as_posix() in {p.as_posix() for p in ALLOWLIST_FILES}


def _iter_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        yield path


class NoDeviceCodeAuthTests(unittest.TestCase):
    def test_no_forbidden_device_code_guidance(self):
        violations: list[str] = []
        for path in _iter_text_files():
            rel = path.relative_to(ROOT)
            if _is_allowlisted(rel):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for pattern in FORBIDDEN:
                    if pattern not in line:
                        continue
                    if _EDU_LINE.search(line):
                        continue
                    violations.append(f"{rel.as_posix()}:{lineno}: {line.strip()[:160]}")

        if violations:
            detail = "\n".join(violations[:40])
            self.fail(
                "Forbidden device-code auth guidance found "
                f"({len(violations)} hit(s)). Use browser/SSO az login only; "
                "education lines must say Never/FORBIDDEN/quarantine.\n"
                f"{detail}"
            )


if __name__ == "__main__":
    unittest.main()
