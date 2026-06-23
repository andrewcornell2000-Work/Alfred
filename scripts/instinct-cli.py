#!/usr/bin/env python3
"""
Alfred Instinct CLI — Continuous-learning "instincts" for the Alfred harness.

An *instinct* is a confidence-scored, reusable lesson ("when X, do Y") that
Alfred learns from sessions and surfaces automatically at the start of future
sessions. Ported (lean, stdlib-only) from ECC's continuous-learning-v2 engine
and adapted to Alfred's repo-local memory/ store.

Scopes:
  - global   : applies to every project (memory/instincts/global.json)
  - project  : applies to one repo, keyed by git-remote/cwd hash
               (memory/instincts/projects/<hash>.json)

Confidence model (0.0 - 1.0):
  - new instinct starts at 0.30 (status: pending)
  - each reinforcement moves confidence asymptotically toward 1.0
  - `decay` lowers confidence for instincts not reinforced recently
  - status:  <0.50 pending  |  0.50-0.80 active  |  >=0.80 strong

Commands:
  status     Show instincts (project + global) grouped by domain
  record     Add a new instinct OR reinforce a matching one (used by /learn + loop)
  add        Add a new instinct
  reinforce  Reinforce an instinct by id
  decay      Apply time-decay to stale instincts
  prune      Delete pending instincts past their TTL (default 30 days)
  list       Machine-readable JSON dump
  export     Write merged instincts to a file
  import     Merge instincts from a file

Stdlib only. Safe to run anywhere; never raises on a missing store.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─────────────────────────── config ───────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTINCTS_DIR = REPO_ROOT / "memory" / "instincts"
GLOBAL_FILE = INSTINCTS_DIR / "global.json"
PROJECTS_DIR = INSTINCTS_DIR / "projects"
OBSERVATIONS_FILE = INSTINCTS_DIR / "observations.jsonl"

NEW_CONFIDENCE = 0.30
REINFORCE_GAIN = 0.25          # fraction of remaining headroom added per reinforcement
DECAY_FACTOR = 0.90            # multiplier applied to stale instincts on `decay`
DECAY_AFTER_DAYS = 14         # only decay instincts untouched for this long
PENDING_TTL_DAYS = 30         # prune pending instincts older than this
ACTIVE_THRESHOLD = 0.50
STRONG_THRESHOLD = 0.80


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_since(iso: str) -> float:
    try:
        then = datetime.fromisoformat(iso)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).total_seconds() / 86400.0
    except Exception:
        return 0.0


def _status(conf: float) -> str:
    if conf >= STRONG_THRESHOLD:
        return "strong"
    if conf >= ACTIVE_THRESHOLD:
        return "active"
    return "pending"


def _bar(conf: float) -> str:
    filled = max(0, min(10, int(round(conf * 10))))
    full, empty = ("█", "░")
    try:
        "█░".encode(sys.stdout.encoding or "utf-8")
    except (LookupError, UnicodeEncodeError):
        full, empty = ("#", ".")
    return full * filled + empty * (10 - filled)


def _project_id(cwd: Path | None = None) -> str:
    """Stable id for the current project: git remote if available, else path."""
    cwd = cwd or Path.cwd()
    key = ""
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            key = out.stdout.strip()
    except Exception:
        key = ""
    if not key:
        try:
            top = subprocess.run(
                ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            )
            key = top.stdout.strip() if top.returncode == 0 else str(cwd)
        except Exception:
            key = str(cwd)
    key = re.sub(r"://[^@]+@", "://", key)          # strip credentials
    key = re.sub(r"\.git/?$", "", key.strip()).lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "instinct"


def _make_id(domain: str, trigger: str) -> str:
    h = hashlib.sha256(f"{domain}|{trigger}".encode("utf-8")).hexdigest()[:6]
    return f"{_slug(domain)}-{_slug(trigger)[:24]}-{h}"


# ─────────────────────────── store ───────────────────────────

def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("instincts", [])
    except Exception:
        return []


def _save(path: Path, instincts: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(instincts, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _store_path(scope: str, project_id: str | None) -> Path:
    if scope == "global":
        return GLOBAL_FILE
    return PROJECTS_DIR / f"{project_id}.json"


def _upsert(scope: str, project_id: str | None, domain: str, trigger: str,
            guidance: str, source: str = "manual", confidence: float | None = None) -> tuple[dict, bool]:
    path = _store_path(scope, project_id)
    instincts = _load(path)
    iid = _make_id(domain, trigger)
    for ins in instincts:
        if ins.get("id") == iid:
            # reinforce existing
            c = float(ins.get("confidence", NEW_CONFIDENCE))
            ins["confidence"] = round(min(1.0, c + (1.0 - c) * REINFORCE_GAIN), 4)
            ins["observations"] = int(ins.get("observations", 1)) + 1
            ins["last_reinforced"] = _now()
            if guidance and guidance not in (ins.get("guidance") or ""):
                ins["guidance"] = guidance
            ins["status"] = _status(ins["confidence"])
            _save(path, instincts)
            return ins, False
    ins = {
        "id": iid,
        "domain": domain,
        "trigger": trigger,
        "guidance": guidance,
        "confidence": round(confidence if confidence is not None else NEW_CONFIDENCE, 4),
        "observations": 1,
        "scope": scope,
        "source": source,
        "created": _now(),
        "last_reinforced": _now(),
    }
    ins["status"] = _status(ins["confidence"])
    instincts.append(ins)
    _save(path, instincts)
    return ins, True


def _all_for_project(project_id: str) -> list[dict]:
    merged = {}
    for ins in _load(GLOBAL_FILE):
        ins["scope"] = "global"
        merged[ins["id"]] = ins
    for ins in _load(_store_path("project", project_id)):
        ins["scope"] = "project"
        merged[ins["id"]] = ins   # project overrides global on id collision
    return list(merged.values())


# ─────────────────────────── commands ───────────────────────────

def cmd_status(args) -> int:
    pid = _project_id()
    instincts = _all_for_project(pid)
    if not instincts:
        print("No instincts learned yet. Alfred will accrue them via /instinct-learn "
              "and the autonomous loop.")
        return 0
    instincts.sort(key=lambda i: (-float(i.get("confidence", 0)), i.get("domain", "")))
    by_domain: dict[str, list[dict]] = {}
    for ins in instincts:
        by_domain.setdefault(ins.get("domain", "general"), []).append(ins)

    print(f"Alfred instincts  (project {pid} + global)")
    print(f"{'─' * 64}")
    for domain in sorted(by_domain):
        print(f"\n## {domain}")
        for ins in by_domain[domain]:
            conf = float(ins.get("confidence", 0))
            scope = "G" if ins.get("scope") == "global" else "P"
            print(f"  [{scope}] {_bar(conf)} {conf:0.2f} {ins.get('status','?'):<7} "
                  f"obs={ins.get('observations',1):<3} {ins.get('id')}")
            print(f"        when: {ins.get('trigger','')}")
            print(f"        do:   {ins.get('guidance','')}")
    counts = {"pending": 0, "active": 0, "strong": 0}
    for ins in instincts:
        counts[_status(float(ins.get('confidence', 0)))] += 1
    print(f"\n{'─' * 64}")
    print(f"Total {len(instincts)}  |  strong {counts['strong']}  "
          f"active {counts['active']}  pending {counts['pending']}")
    return 0


def cmd_record(args) -> int:
    scope = "global" if args.scope == "global" else "project"
    pid = None if scope == "global" else _project_id()
    ins, created = _upsert(scope, pid, args.domain, args.trigger, args.guidance,
                           source=args.source, confidence=getattr(args, "confidence", None))
    verb = "Added" if created else "Reinforced"
    print(f"{verb} [{scope}] {ins['id']}  conf={ins['confidence']:.2f} "
          f"({ins['status']}, obs={ins['observations']})")
    # log observation
    try:
        OBSERVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OBSERVATIONS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "id": ins["id"], "scope": scope,
                                "created": created, "source": args.source}) + "\n")
    except Exception:
        pass
    return 0


def cmd_reinforce(args) -> int:
    for scope, path in (("global", GLOBAL_FILE),
                        ("project", _store_path("project", _project_id()))):
        instincts = _load(path)
        for ins in instincts:
            if ins.get("id") == args.id:
                c = float(ins.get("confidence", NEW_CONFIDENCE))
                ins["confidence"] = round(min(1.0, c + (1.0 - c) * REINFORCE_GAIN), 4)
                ins["observations"] = int(ins.get("observations", 1)) + 1
                ins["last_reinforced"] = _now()
                ins["status"] = _status(ins["confidence"])
                _save(path, instincts)
                print(f"Reinforced {args.id} -> conf={ins['confidence']:.2f} ({ins['status']})")
                return 0
    print(f"Instinct '{args.id}' not found.", file=sys.stderr)
    return 1


def cmd_decay(args) -> int:
    changed = 0
    for path in (GLOBAL_FILE, _store_path("project", _project_id())):
        instincts = _load(path)
        for ins in instincts:
            if _days_since(ins.get("last_reinforced", ins.get("created", _now()))) >= DECAY_AFTER_DAYS:
                ins["confidence"] = round(float(ins.get("confidence", 0)) * DECAY_FACTOR, 4)
                ins["status"] = _status(ins["confidence"])
                changed += 1
        if instincts:
            _save(path, instincts)
    print(f"Decayed {changed} stale instinct(s).")
    return 0


def cmd_prune(args) -> int:
    removed = 0
    for path in (GLOBAL_FILE, _store_path("project", _project_id())):
        instincts = _load(path)
        keep = []
        for ins in instincts:
            stale = _days_since(ins.get("last_reinforced", ins.get("created", _now()))) >= PENDING_TTL_DAYS
            if _status(float(ins.get("confidence", 0))) == "pending" and stale:
                removed += 1
                continue
            keep.append(ins)
        if len(keep) != len(instincts):
            _save(path, keep)
    print(f"Pruned {removed} stale pending instinct(s).")
    return 0


def cmd_list(args) -> int:
    print(json.dumps(_all_for_project(_project_id()), indent=2, ensure_ascii=False))
    return 0


def cmd_export(args) -> int:
    data = _all_for_project(_project_id())
    out = Path(args.file)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(data)} instinct(s) -> {out}")
    return 0


def cmd_import(args) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        return 1
    try:
        incoming = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Could not parse {src}: {e}", file=sys.stderr)
        return 1
    n = 0
    for ins in incoming if isinstance(incoming, list) else []:
        scope = ins.get("scope", "global")
        pid = None if scope == "global" else _project_id()
        _upsert(scope, pid, ins.get("domain", "general"), ins.get("trigger", ""),
                ins.get("guidance", ""), source="import")
        n += 1
    print(f"Imported/merged {n} instinct(s).")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Alfred instinct engine")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("decay").set_defaults(func=cmd_decay)
    sub.add_parser("prune").set_defaults(func=cmd_prune)

    rec = sub.add_parser("record", help="add or reinforce an instinct")
    rec.add_argument("--domain", required=True)
    rec.add_argument("--trigger", required=True)
    rec.add_argument("--guidance", required=True)
    rec.add_argument("--scope", choices=["global", "project"], default="project")
    rec.add_argument("--source", default="learn")
    rec.set_defaults(func=cmd_record)

    add = sub.add_parser("add", help="add a new instinct")
    add.add_argument("--domain", required=True)
    add.add_argument("--trigger", required=True)
    add.add_argument("--guidance", required=True)
    add.add_argument("--scope", choices=["global", "project"], default="project")
    add.add_argument("--source", default="manual")
    add.add_argument("--confidence", type=float, default=None,
                     help="seed confidence 0.0-1.0 (only used on first creation)")
    add.set_defaults(func=cmd_record)

    rf = sub.add_parser("reinforce")
    rf.add_argument("id")
    rf.set_defaults(func=cmd_reinforce)

    ex = sub.add_parser("export")
    ex.add_argument("file")
    ex.set_defaults(func=cmd_export)

    im = sub.add_parser("import")
    im.add_argument("file")
    im.set_defaults(func=cmd_import)

    args = p.parse_args()
    if not getattr(args, "cmd", None):
        return cmd_status(args)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
