"""Quality-gate and task runner for Windows (no `make` required).

Canonical gate (mirrors `make check`)::

    python -m tasks check

which runs the lint/format/typecheck/test pipeline
(see :func:`check` for the exact commands).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd)
    return proc.returncode


def check() -> int:
    """Run the full quality gate. Returns the process exit code."""
    steps: list[list[str]] = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "mypy", "--strict", "src"],
        [sys.executable, "-m", "pytest", "-q", "--cov=src", "--cov-fail-under=85"],
        [sys.executable, "scripts/plan_compliance.py"],
    ]
    for cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(f"GATE FAILED at: {' '.join(cmd)} (exit {code})", flush=True)
            return code
    print("GATE PASSED", flush=True)
    return 0


def backup() -> int:
    """Zip artifacts/ outside the repo (P5; plan v2.6 S0 item 4)."""
    code = _run([sys.executable, str(REPO / "scripts" / "backup.py")])
    print("BACKUP FAILED" if code else "BACKUP DONE")
    return code


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for `python -m tasks <command>`."""
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help", "help"}:
        print("Usage: python -m tasks check|backup")
        raise SystemExit(0)
    if args[0] == "check":
        raise SystemExit(check())
    if args[0] == "backup":
        raise SystemExit(backup())
    print(f"Unknown task: {args[0]!r}. Available: check, backup")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
