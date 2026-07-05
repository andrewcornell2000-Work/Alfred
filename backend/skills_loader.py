"""Skill inventory helpers for diagnostics and validation."""

from __future__ import annotations

import os
from typing import Iterator

from context import ROOT

SKIP_SKILL_FILES = frozenset({"mcp-routing.md", "lean-ctx.md"})


def iter_skill_files(root: str | None = None) -> Iterator[tuple[str, str]]:
    """Yield (display_name, path) for skills/*.md and skills/_packs/**/SKILL.md."""
    repo = root or ROOT
    skills_dir = os.path.join(repo, "skills")
    if not os.path.isdir(skills_dir):
        return

    for fname in sorted(os.listdir(skills_dir)):
        if not fname.endswith(".md") or fname in SKIP_SKILL_FILES:
            continue
        yield fname, os.path.join(skills_dir, fname)

    packs_dir = os.path.join(skills_dir, "_packs")
    if not os.path.isdir(packs_dir):
        return

    for pack in sorted(os.listdir(packs_dir)):
        pack_path = os.path.join(packs_dir, pack)
        if not os.path.isdir(pack_path):
            continue
        for skill in sorted(os.listdir(pack_path)):
            skill_md = os.path.join(pack_path, skill, "SKILL.md")
            if os.path.isfile(skill_md):
                yield f"_packs/{pack}/{skill}/SKILL.md", skill_md


def count_skills(root: str | None = None) -> dict:
    """Return skill inventory counts and any unreadable files."""
    flat = 0
    packs = 0
    unreadable: list[str] = []

    for display_name, skill_path in iter_skill_files(root):
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                if not f.read(1):
                    unreadable.append(f"{display_name}: empty file")
                    continue
        except OSError as exc:
            unreadable.append(f"{display_name}: {exc}")
            continue

        if display_name.startswith("_packs/"):
            packs += 1
        else:
            flat += 1

    return {
        "flat": flat,
        "packs": packs,
        "total": flat + packs,
        "unreadable": unreadable,
    }
