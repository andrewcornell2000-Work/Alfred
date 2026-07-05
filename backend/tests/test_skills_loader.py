"""Skill inventory tests."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from context import ROOT  # noqa: E402
from skills_loader import count_skills, iter_skill_files  # noqa: E402
import os  # noqa: E402


class SkillLoaderTests(unittest.TestCase):
    def test_iter_includes_flat_and_pack_skills(self):
        names = [n for n, _ in iter_skill_files(ROOT)]
        self.assertTrue(any(n.endswith(".md") and not n.startswith("_packs/") for n in names))
        self.assertTrue(any(n.startswith("_packs/") and n.endswith("SKILL.md") for n in names))

    def test_count_skills_matches_iter(self):
        inventory = count_skills(ROOT)
        self.assertGreater(inventory["flat"], 0)
        self.assertGreater(inventory["packs"], 0)
        self.assertEqual(inventory["total"], inventory["flat"] + inventory["packs"])

    def test_missing_skill_file_is_reported(self):
        skills_dir = os.path.join(ROOT, "skills")
        fake = ("fake-skill.md", os.path.join(skills_dir, "does-not-exist.md"))

        def _fake_iter(_root=None):
            yield fake

        with patch("skills_loader.iter_skill_files", _fake_iter):
            inventory = count_skills(ROOT)
        self.assertEqual(inventory["total"], 0)
        self.assertTrue(any("fake-skill.md" in err for err in inventory["unreadable"]))


if __name__ == "__main__":
    unittest.main()
