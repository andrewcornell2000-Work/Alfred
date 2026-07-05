"""Backward-compatible entry point for Alfred.

The interactive chat/menu CLI was removed. Use ``backend.cli`` for
non-interactive update, provision, validate, diagnose, and status tasks.

Alfred-Install.exe and run-alfred.bat already call the new path.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
_ROOT = _BACKEND.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main(argv: list[str] | None = None) -> int:
    """Deprecated entry: runs ``backend.cli update`` (check updates + provision)."""
    from cli import main as cli_main

    args = list(argv) if argv is not None else sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        return cli_main(["--help"])

    if args and args[0] in {"status", "diagnose", "validate", "provision", "update", "chat"}:
        return cli_main(args)

    print(
        "Alfred chat/menu has been removed.\n"
        "Running update + provision instead.\n"
        "Commands: python -m backend.cli update|provision|validate|diagnose|status\n"
        "Or use Alfred.lnk / run-alfred.bat."
    )
    return cli_main(["update"])


if __name__ == "__main__":
    raise SystemExit(main())
