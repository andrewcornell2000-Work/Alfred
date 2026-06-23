#!/usr/bin/env python3
"""
PreToolUse hook (Edit | Write | MultiEdit): config protection.

Blocks modifications to linter/formatter config files. Agents frequently weaken
these to make checks pass instead of fixing the actual code; this steers the
agent back to fixing the source. First-time creation of a config in a repo that
has none is allowed (legitimate bootstrap).

Ported from ECC scripts/hooks/config-protection.js — Python, stdlib only.

Exit codes:
  0  allow
  2  block (existing protected config modification)
"""
import json
import os
import sys

PROTECTED = {
    # ESLint (legacy + flat)
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
    ".eslintrc.yml", ".eslintrc.yaml",
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.ts", "eslint.config.mts", "eslint.config.cts",
    # Prettier
    ".prettierrc", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.json",
    ".prettierrc.yml", ".prettierrc.yaml",
    "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs",
    # Biome
    "biome.json", "biome.jsonc",
    # Ruff (Python). pyproject.toml deliberately excluded (mixed metadata).
    ".ruff.toml", "ruff.toml",
    # Shell / style / markdown
    ".shellcheckrc", ".stylelintrc", ".stylelintrc.json", ".stylelintrc.yml",
    ".markdownlint.json", ".markdownlint.yaml", ".markdownlintrc",
}


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # never block on malformed input

    ti = data.get("tool_input") or {}
    file_path = ti.get("file_path") or ti.get("file") or ""
    if not file_path:
        return 0

    basename = os.path.basename(file_path)
    if basename not in PROTECTED:
        return 0

    # Allow first-time creation (no existing config to weaken).
    if not os.path.lexists(file_path):
        return 0

    sys.stderr.write(
        f"BLOCKED: modifying {basename} is not allowed. Fix the source code to "
        f"satisfy the linter/formatter instead of weakening its config. If this "
        f"is a deliberate config change, temporarily disable the "
        f"config-protection hook in .claude/settings.json.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
