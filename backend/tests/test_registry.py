"""Registry structure tests."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routing.registry import TOOL_REGISTRY, iter_control_tower_capabilities, register_tool


class RegistryTests(unittest.TestCase):
    def test_tool_registry_has_core_capabilities(self):
        for key in ("chat", "search", "code", "powerbi", "excel"):
            self.assertIn(key, TOOL_REGISTRY)

    def test_control_tower_matches_registry_count(self):
        self.assertEqual(len(iter_control_tower_capabilities()), len(TOOL_REGISTRY))

    def test_search_shows_tavily_in_control_tower(self):
        search = next(c for c in iter_control_tower_capabilities() if c["category"] == "SEARCH")
        self.assertEqual(search["provider"], "tavily")

    def test_register_tool_extends_registry(self):
        before = len(TOOL_REGISTRY)
        register_tool(
            "_test_tool", "Test", "desc", "GENERAL", "claude", "claude_cli",
        )
        self.assertEqual(len(TOOL_REGISTRY), before + 1)
        del TOOL_REGISTRY["_test_tool"]


if __name__ == "__main__":
    unittest.main()
