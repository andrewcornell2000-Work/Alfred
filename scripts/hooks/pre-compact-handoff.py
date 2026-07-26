#!/usr/bin/env python3
"""
PreCompact hook: write HANDOFF.md before Claude Code compacts context.

Alfred triggers auto-compact early (default 35% via CLAUDE_AUTOCOMPACT_PCT_OVERRIDE).
This hook snapshots present-state task context so the SessionStart(compact) hook
can re-inject a continue brief after summarization.

Never blocks compaction. Always exits 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_TRANSCRIPT_BYTES = 2_000_000
MAX_FILE_PATHS = 12
MAX_DONE_BULLETS = 8
MAX_SNIPPET = 240

FILE_RE = re.compile(
    r"(?:[A-Za-z]:)?(?:[/\\][\w.-]+){2,}\.\w{1,8}|(?:[\w.-]+/){1,}[\w.-]+\.\w{1,8}"
)


def _drain_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
                elif block.get("type") == "tool_use":
                    name = block.get("name") or "tool"
                    inp = block.get("input") or {}
                    path = inp.get("file_path") or inp.get("path") or inp.get("file") or ""
                    cmd = inp.get("command") or ""
                    snippet = path or cmd or json.dumps(inp, ensure_ascii=False)[:120]
                    parts.append(f"[tool:{name}] {snippet}")
                elif block.get("type") == "tool_result":
                    parts.append(str(block.get("content") or "")[:180])
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return str(content.get("text") or content)
    return str(content)


def _read_transcript_tail(path: str) -> list[dict]:
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        size = p.stat().st_size
        with p.open("rb") as f:
            if size > MAX_TRANSCRIPT_BYTES:
                f.seek(size - MAX_TRANSCRIPT_BYTES)
                f.readline()  # drop partial first line
            data = f.read().decode("utf-8-sig", errors="replace")
    except Exception:
        return []

    rows: list[dict] = []
    for line in data.splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _extract(rows: list[dict]) -> tuple[str, list[str], list[str], list[str]]:
    last_user = ""
    files: list[str] = []
    done: list[str] = []
    decisions: list[str] = []
    seen_files: set[str] = set()

    for row in rows:
        msg = row.get("message") if isinstance(row.get("message"), dict) else None
        role = (msg or {}).get("role") or row.get("type") or ""
        content = _text_from_content((msg or {}).get("content") if msg else row.get("content"))
        if not content:
            continue

        for m in FILE_RE.finditer(content):
            fp = m.group(0).replace("\\", "/")
            if fp not in seen_files and not fp.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                seen_files.add(fp)
                files.append(fp)

        role_l = str(role).lower()
        if role_l in ("user",) or row.get("type") == "user":
            # Prefer human prompts over tool-result wrappers.
            if "tool_result" not in content and not content.strip().startswith("<"):
                cleaned = re.sub(r"\s+", " ", content).strip()
                if len(cleaned) > 20:
                    last_user = cleaned[:500]
        elif role_l in ("assistant",) or row.get("type") == "assistant":
            for line in content.splitlines():
                s = line.strip()
                if not s:
                    continue
                low = s.lower()
                if low.startswith(("i'll ", "i will ", "let me ", "i'm going")):
                    continue
                if any(k in low for k in ("decision", "we'll keep", "locked", "do not")):
                    decisions.append(s[:MAX_SNIPPET])
                if s.startswith(("- ", "* ", "Done", "Fixed", "Updated", "Created", "Wrote")):
                    done.append(s.lstrip("-* ").strip()[:MAX_SNIPPET])

    # De-dupe preserving order
    def uniq(items: list[str], n: int) -> list[str]:
        out, seen = [], set()
        for it in items:
            key = it.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
            if len(out) >= n:
                break
        return out

    return last_user, uniq(files, MAX_FILE_PATHS), uniq(done, MAX_DONE_BULLETS), uniq(decisions, 6)


def _git_bits(cwd: Path) -> tuple[str, str]:
    branch, sha = "unknown", "unknown"
    try:
        import subprocess

        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(cwd),
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or "unknown"
        )
        sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(cwd),
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or "unknown"
        )
    except Exception:
        pass
    return branch, sha


def _write_handoff(
    cwd: Path,
    *,
    trigger: str,
    goal: str,
    files: list[str],
    done: list[str],
    decisions: list[str],
) -> Path:
    branch, sha = _git_bits(cwd)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    goal_line = goal or (
        "(Goal not recovered from transcript - infer from recent files and continue cautiously.)"
    )
    done_block = (
        "\n".join(f"- {d}" for d in done)
        if done
        else "- (Not recovered - inspect git status / recent edits.)"
    )
    decisions_block = (
        "\n".join(f"- {d}" for d in decisions) if decisions else "- (None recovered from transcript.)"
    )
    files_block = (
        "\n".join(f"- `{f}` — recently referenced" for f in files)
        if files
        else "- (None recovered.)"
    )

    body = f"""# HANDOFF - Auto-compact ({trigger or "unknown"})
_Session compacted: {now}_
_Last worked in: Claude Code_
_Status: IN PROGRESS_
_Alfred: auto-compact at configured threshold - continue immediately_

## What we're building
{goal_line}

## Repository state
- Repo / branch: {cwd.name} / {branch}
- Base commit: {sha}
- Working tree: check with `git status --short`
- Remote state: unknown

## What's done
{done_block}

## Decisions locked
{decisions_block}

## What to do next (ordered)
1. Read this HANDOFF.md fully - expected outcome: resume without re-asking the user for context
2. Continue the in-progress task from the last incomplete step - expected outcome: forward progress
3. Prefer the key files below over broad re-exploration

## Do NOT do
- Do not restart the whole task from scratch
- Do not re-read the entire repo "to understand context"
- Do not ask the user to restate the goal unless HANDOFF is empty/contradictory

## Key files (touch these, not others)
{files_block}

## Open questions (needs human input before proceeding)
- (None captured - proceed if next steps are clear.)

## Verification and environment
- Commands run: (not captured)
- Next verification command: re-run the check you were about to run before compact
- Required environment variable names: (none recorded)
- Machine assumptions: Windows / Claude Code

## Starting prompt for next session
> Context was auto-compacted by Alfred. Read HANDOFF.md and continue the in-progress task immediately without asking for a recap.
"""
    out = cwd / "HANDOFF.md"
    out.write_text(body, encoding="utf-8")
    marker = cwd / ".alfred"
    try:
        marker.mkdir(parents=True, exist_ok=True)
        (marker / "last-compact.json").write_text(
            json.dumps(
                {
                    "ts": now,
                    "trigger": trigger,
                    "handoff": str(out),
                    "goal": goal_line[:300],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    return out


def main() -> int:
    data = _drain_stdin()
    cwd = Path(data.get("cwd") or os.getcwd()).resolve()
    trigger = str(data.get("trigger") or "auto")
    rows = _read_transcript_tail(str(data.get("transcript_path") or ""))
    goal, files, done, decisions = _extract(rows)
    try:
        path = _write_handoff(
            cwd,
            trigger=trigger,
            goal=goal,
            files=files,
            done=done,
            decisions=decisions,
        )
        sys.stderr.write(f"Alfred PreCompact: wrote {path}\n")
    except Exception as exc:
        sys.stderr.write(f"Alfred PreCompact: handoff failed ({exc}); compact continues\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
