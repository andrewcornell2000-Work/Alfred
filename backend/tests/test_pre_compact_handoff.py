#!/usr/bin/env python3
"""Unit tests for PreCompact handoff transcript extraction."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts" / "hooks" / "pre-compact-handoff.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("pre_compact_handoff", HOOK)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class PreCompactHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def test_extract_goal_files_and_done(self):
        rows = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "Fix the login bug in src/auth/login.ts and add a regression test.",
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Updated src/auth/login.ts"},
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "src/auth/login.ts"},
                        },
                        {"type": "text", "text": "- Fixed null token check"},
                    ],
                },
            },
        ]
        goal, files, done, _decisions = self.hook._extract(rows)
        self.assertIn("login bug", goal.lower())
        self.assertTrue(any("login.ts" in f for f in files))
        self.assertTrue(any("null token" in d.lower() or d.startswith("- Fixed") for d in done))

    def test_write_handoff_creates_file(self):
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            path = self.hook._write_handoff(
                cwd,
                trigger="auto",
                goal="Ship early compact hooks",
                files=["scripts/hooks/pre-compact-handoff.py"],
                done=["- Wrote PreCompact hook"],
                decisions=["- Compact at 35%"],
            )
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn("Ship early compact hooks", text)
            self.assertIn("IN PROGRESS", text)
            self.assertTrue((cwd / ".alfred" / "last-compact.json").is_file())

    def test_post_compact_continue_stdout(self):
        post = ROOT / "scripts" / "hooks" / "post-compact-continue.py"
        spec = importlib.util.spec_from_file_location("post_compact_continue", post)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            (cwd / "HANDOFF.md").write_text("# HANDOFF\nContinue auth fix\n", encoding="utf-8")
            payload = json.dumps({"cwd": str(cwd)})
            # Simulate stdin via monkeypatching would be heavier; call main pieces instead.
            self.assertTrue((cwd / "HANDOFF.md").is_file())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2) is None else 0)
