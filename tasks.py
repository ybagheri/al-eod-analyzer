"""Quality-gate and task runner for Windows (no `make` required).

Canonical gate (mirrors `make check`)::

    python -m tasks check

which runs the lint/format/typecheck/test pipeline
(see :func:`check` for the exact commands).
"""

from __future__ import annotations

import subprocess
import sys


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd)
    return proc.returncode


def check() -> int:
    """Run the full quality gate. Returns the process exit code."""
    steps: list[list[str]] = [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy", "--strict", "src"],
        ["pytest", "-q", "--cov=src", "--cov-fail-under=85"],
    ]
    for cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(f"GATE FAILED at: {' '.join(cmd)} (exit {code})", flush=True)
            return code
    print("GATE PASSED", flush=True)
    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for `python -m tasks <command>`."""
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help", "help"}:
        print("Usage: python -m tasks check")
        raise SystemExit(0)
    if args[0] == "check":
        raise SystemExit(check())
    print(f"Unknown task: {args[0]!r}. Available: check")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
