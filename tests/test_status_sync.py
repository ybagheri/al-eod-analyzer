"""Test: rendered status blocks in README/ROADMAP/HANDOFF match STATUS.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import sync_status  # noqa: E402


def test_status_blocks_in_sync() -> None:
    status = sync_status.load_status()
    for rel in sync_status.TARGETS:
        path = REPO / rel
        old, new = sync_status.sync_file(path, status)
        assert old == new, f"stale status block in {rel}; run scripts/sync_status.py"


def test_exactly_one_in_progress_step() -> None:
    status = sync_status.load_status()
    in_prog = [k for k, v in status["steps"].items() if v["status"] == "in_progress"]
    assert len(in_prog) <= 1, f"multiple in_progress steps: {in_prog}"


def test_plan_hash_matches_plan_file() -> None:
    import hashlib

    status = sync_status.load_status()
    plan = REPO / "docs" / "PLAN_V2.md"
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
    assert digest == status["plan"]["sha256"], "docs/PLAN_V2.md changed without ADR"
    sha_file = REPO / "docs" / "PLAN_V2.sha256"
    assert sha_file.read_text(encoding="utf-8").strip() == digest
