"""Backup P5 (plan v2.6 S0 item 4).

Writes a timestamped zip of ``artifacts/`` to a directory OUTSIDE the repo
(default ``<repo>/../_backups/al-eod-analyzer``) and keeps the last
``--keep`` (default 10) backups. Run before every bulk step
(``python -m tasks backup``).

Usage::

    python scripts/backup.py [--source artifacts] [--target PATH] [--keep N]
"""

from __future__ import annotations

import argparse
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STEM_RE = re.compile(r"artifacts_(\d{8})_(\d{6})\.zip$")


def _default_target(source_dir: Path) -> Path:
    return REPO.parent / "_backups" / (REPO.name + "/" + source_dir.name)


def zip_source(source_dir: Path, target_dir: Path) -> Path:
    if not source_dir.is_dir():
        msg = f"source dir not found: {source_dir}"
        raise SystemExit(msg)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    zip_path = target_dir / f"artifacts_{stamp}.zip"
    n_files = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir.parent))
                n_files += 1
    size = zip_path.stat().st_size
    print(f"backup written: {zip_path} ({n_files} files, {size / 1024:.0f} KB)")
    return zip_path


def prune_old(target_dir: Path, keep: int) -> list[Path]:
    existing = sorted(p for p in target_dir.iterdir() if p.is_file() and STEM_RE.search(p.name))
    excess = existing[:-keep] if keep < len(existing) else []
    for path in excess:
        path.unlink()
        print(f"pruned: {path.name}")
    return excess


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(REPO / "artifacts"))
    parser.add_argument("--target", default=None)
    parser.add_argument("--keep", type=int, default=10)
    args = parser.parse_args(argv)
    source_dir = Path(args.source)
    target_dir = Path(args.target) if args.target else _default_target(source_dir)
    zip_source(source_dir, target_dir)
    prune_old(target_dir, max(args.keep, 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
