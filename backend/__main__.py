"""Default module entry: ``python -m backend`` → ``backend.cli``."""

from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
