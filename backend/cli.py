"""Non-interactive command runner for Alfred install/update/provision/validate/diagnose/status.

This is NOT a chat assistant — only a minimal task runner for scripts and shortcuts.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Ensure flat imports (context, diagnostics, …) work when invoked as `python -m backend.cli`.
_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from context import ROOT
from diagnostics.report import format_diagnose_report, format_status_summary


def _run_ps1(script_name: str, *extra_args: str) -> int:
    script = os.path.join(ROOT, script_name)
    if not os.path.isfile(script):
        print(f"[FAIL] Script not found: {script}")
        return 1
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        script,
        *extra_args,
    ]
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def _log_cli_run(command: str, result: str, exit_code: int) -> None:
    memory_dir = os.path.join(ROOT, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    payload = {
        "command": command,
        "result": result,
        "exit_code": exit_code,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    path = os.path.join(memory_dir, "cli-last-run.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        pass


def _finish(command: str, ok: bool, message: str) -> int:
    tag = "OK" if ok else "FAIL"
    print(f"[{tag}] {message}")
    code = 0 if ok else 1
    _log_cli_run(command, tag, code)
    return code


def cmd_update(_args: argparse.Namespace) -> int:
    """Check for updates, re-run setup if pulled, then provision."""
    print("Alfred update")
    print("=============")

    if not os.path.isfile(os.path.join(ROOT, ".venv", "Scripts", "python.exe")):
        return _finish("update", False, ".venv not found — run Install-Alfred.bat first")

    update_exit = 0
    if os.path.isdir(os.path.join(ROOT, ".git")):
        print("\nChecking for updates...")
        update_exit = _run_ps1("check-updates.ps1")
        if update_exit not in (0, 10):
            return _finish("update", False, f"Update check failed (exit {update_exit})")
        if update_exit == 10:
            print("\nApplying updated requirements...")
            setup_exit = _run_ps1("setup.ps1")
            if setup_exit != 0:
                return _finish("update", False, f"setup.ps1 failed (exit {setup_exit})")
    else:
        print("(Skipping git update — not a git repository)")

    print("\nProvisioning Cursor / Claude / Codex...")
    prov_exit = _run_ps1("Provision-Cursor.ps1", "-ProjectPath", ROOT)
    if prov_exit != 0:
        return _finish("update", False, f"Provision-Cursor.ps1 failed (exit {prov_exit})")

    if update_exit == 10:
        return _finish("update", True, "Updated, setup applied, and provisioning complete")
    return _finish("update", True, "Up to date and provisioning complete")


def cmd_provision(_args: argparse.Namespace) -> int:
    print("Alfred provision")
    print("================")
    prov_exit = _run_ps1("Provision-Cursor.ps1", "-ProjectPath", ROOT)
    if prov_exit != 0:
        return _finish("provision", False, f"Provision-Cursor.ps1 failed (exit {prov_exit})")
    return _finish("provision", True, "Provisioning complete")


def _ps_parse_check(script_rel: str) -> tuple[bool, str]:
    path = os.path.join(ROOT, script_rel)
    if not os.path.isfile(path):
        return False, f"missing: {script_rel}"
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"$null = [System.Management.Automation.Language.Parser]::ParseFile('{path.replace(chr(92), '/')}',$null,[ref]$null); if ($?) {{ exit 0 }} else {{ exit 1 }}",
    ]
    # Use -File with a tiny inline script for Windows path safety
    ps = f"$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('{path}', [ref]$null, [ref]$e); if ($e) {{ $e | ForEach-Object {{ Write-Error $_ }}; exit 1 }} else {{ exit 0 }}"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        msg = detail[0] if detail else "parse error"
        return False, f"{script_rel}: {msg}"
    return True, script_rel


def cmd_validate(_args: argparse.Namespace) -> int:
    print("Alfred validate")
    print("===============")
    failures: list[str] = []

    print("\n[1/5] Catalog validation...")
    catalog_script = os.path.join(ROOT, ".github", "scripts", "validate_catalog.py")
    py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(py):
        py = sys.executable
    r = subprocess.run([py, catalog_script], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        failures.append("validate_catalog.py failed")
        if r.stdout.strip():
            print(r.stdout.strip())
        if r.stderr.strip():
            print(r.stderr.strip())
    else:
        print("  OK")

    print("\n[2/5] Provision template validation...")
    prov_test = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         os.path.join(ROOT, "scripts", "Test-ProvisionTemplate.ps1")],
        cwd=ROOT,
    )
    if prov_test.returncode != 0:
        failures.append("Test-ProvisionTemplate.ps1 failed")
    else:
        print("  OK")

    print("\n[3/5] Cursor rules sync test...")
    rules_test = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         os.path.join(ROOT, "scripts", "Test-CursorRulesSync.ps1")],
        cwd=ROOT,
    )
    if rules_test.returncode != 0:
        failures.append("Test-CursorRulesSync.ps1 failed")
    else:
        print("  OK")

    print("\n[4/5] Python unit tests...")
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(_BACKEND, "tests"))
    runner = unittest.TextTestRunner(verbosity=0)
    test_result = runner.run(suite)
    if not test_result.wasSuccessful():
        failures.append(f"unit tests: {len(test_result.failures)} failure(s), {len(test_result.errors)} error(s)")
    else:
        print(f"  OK ({test_result.testsRun} tests)")

    print("\n[5/5] PowerShell parse checks...")
    ps_only = ["check-updates.ps1", "Provision-Cursor.ps1", "setup.ps1", "build-installer.ps1"]
    for rel in ps_only:
        ok, msg = _ps_parse_check(rel)
        if ok:
            print(f"  OK: {rel}")
        else:
            failures.append(msg)

    if failures:
        print("\nValidation failures:")
        for f in failures:
            print(f"  - {f}")
        return _finish("validate", False, f"{len(failures)} check(s) failed")

    return _finish("validate", True, "All validation checks passed")


def cmd_diagnose(_args: argparse.Namespace) -> int:
    print(format_diagnose_report())
    return _finish("diagnose", True, "Diagnostics complete")


def cmd_status(_args: argparse.Namespace) -> int:
    print(format_status_summary())
    return _finish("status", True, "Status displayed")


def cmd_legacy_chat(_args: argparse.Namespace) -> int:
    print(
        "The Alfred chat/menu interface is deprecated.\n"
        "Use Cursor, Claude Code, or Codex for AI tasks.\n"
        "\n"
        "Available Alfred commands:\n"
        "  python -m backend.cli update\n"
        "  python -m backend.cli provision\n"
        "  python -m backend.cli validate\n"
        "  python -m backend.cli diagnose\n"
        "  python -m backend.cli status\n"
        "\n"
        "To run update + provision (normal startup), use run-alfred.bat."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alfred",
        description="Alfred — lightweight install/update/provision/diagnostics runner (non-interactive).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("update", help="Check for updates, run setup if needed, provision")
    sub.add_parser("provision", help="Run Provision-Cursor.ps1")
    sub.add_parser("validate", help="Run catalog, template, rules, and test validation")
    sub.add_parser("diagnose", help="Developer health report (MCP, skills, registry, git)")
    sub.add_parser("status", help="Short installed/provisioned status summary")
    sub.add_parser("chat", help="Deprecated — shows migration message")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "update": cmd_update,
        "provision": cmd_provision,
        "validate": cmd_validate,
        "diagnose": cmd_diagnose,
        "status": cmd_status,
        "chat": cmd_legacy_chat,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
