"""Dirty-tree guard for the extraction queue (plan step S2.4).

``brooks extract`` refuses to run with uncommitted changes under
``artifacts/extraction_queue`` so a conversion pass can always be traced back
to a committed queue state (override: ``--allow-dirty``).
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

RunFn = Callable[..., subprocess.CompletedProcess[str]]


def queue_dirty(queue_dir: Path, runner: RunFn = subprocess.run) -> bool:
    """True when ``git status`` shows uncommitted changes under ``queue_dir``.

    Outside a git work tree there is nothing to guard (no uncommitted changes
    are even possible), so ``git rev-parse`` failure opens the guard. Inside a
    real repo any git failure is treated as dirty to stay fail-closed.
    """
    if not queue_dir.is_dir():
        return False
    cwd = str(queue_dir)
    try:
        proc = runner(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
    except OSError as exc:
        logger.warning("git rev-parse failed (%s); treating queue as dirty.", exc)
        return True
    if proc.returncode != 0 or not proc.stdout.strip():
        return False  # not inside a git work tree: no tracked state to protect
    try:
        status = runner(
            ["git", "status", "--porcelain", "--", "."],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
    except OSError as exc:
        logger.warning("git status failed (%s); treating queue as dirty.", exc)
        return True
    if status.returncode != 0:
        logger.warning("git status exited %d; treating queue as dirty.", status.returncode)
        return True
    return bool(status.stdout.strip())
