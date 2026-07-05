"""Shared runtime context: paths, console, env loading."""

import io
import os
import sys

from dotenv import load_dotenv
from rich.console import Console

ENV_PATH = (
    os.path.join(os.path.dirname(sys.executable), ".env")
    if getattr(sys, "frozen", False)
    else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)
load_dotenv(ENV_PATH, override=True)

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

_stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_stdout_utf8, highlight=False)

ROOT = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
