"""Unit tests for weekly digest parsers (no email/git network)."""

import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alfred_weekly_digest as digest


class TestWeeklyDigest(unittest.TestCase):
    def test_parse_learning_log_em_dash_and_hyphen(self):
        content = """# Log

## 2026-06-08 (Iteration #1) — Routing audit

**Change summary:**
- Fixed routing keywords

## 2026-06-07 - CLI update

**Change summary:**
- Added uvx path
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "memory")
            os.makedirs(path)
            log = os.path.join(path, "learning-log.md")
            with open(log, "w", encoding="utf-8") as f:
                f.write(content)
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                entries = digest._parse_learning_log(date(2026, 6, 7))
            finally:
                os.chdir(old_cwd)
        titles = {e["title"] for e in entries}
        self.assertIn("Routing audit", titles)
        self.assertIn("CLI update", titles)

    def test_parse_discovered_tools_undated_shipped(self):
        content = """<!-- loop appends below this line -->

### sharepoint-mcp
- **Category:** MCP
- **What it does:** List SharePoint files
- **Try asking:** "Find last week's payroll xlsx"
- **Status:** shipped
"""
        with tempfile.TemporaryDirectory() as tmp:
            req = os.path.join(tmp, "requirements")
            os.makedirs(req)
            cat = os.path.join(req, "discovered-tools.md")
            with open(cat, "w", encoding="utf-8") as f:
                f.write(content)
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                entries = digest._parse_discovered_tools(date(2026, 6, 1))
            finally:
                os.chdir(old_cwd)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "sharepoint-mcp")
        self.assertEqual(entries[0]["status"], "shipped")


if __name__ == "__main__":
    unittest.main()
