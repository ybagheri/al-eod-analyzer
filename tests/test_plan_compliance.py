"""Tests for scripts/plan_compliance.py (§8.3 enforcement)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import plan_compliance as pc  # noqa: E402


def _status(steps: dict[list, dict] | None = None) -> dict:
    return {
        "schema_version": 1,
        "plan": {"file": "docs/PLAN_V2.md", "sha256": "x"},
        "current_step": "S0",
        "steps": steps or {"S0": {"status": "in_progress", "commit": None}},
        "last_gate": {"result": "green", "when": "2026-10-19", "details": "ok"},
        "counts": {},
        "checks": {},
        "coverage": {},
        "metrics": {},
    }


def test_status_schema_missing_keys() -> None:
    bad = {"schema_version": 1}
    assert pc.check_status_schema(bad) is not None
    assert pc.check_status_schema(_status()) is None


def test_two_in_progress_outside_parallel_pairs_fails() -> None:
    steps = {"S0": {"status": "in_progress"}, "S5": {"status": "in_progress"}}
    assert pc.check_in_progress(_status(steps)) is not None
    ok = {"S0": {"status": "in_progress"}, "S1": {"status": "in_progress"}}
    assert pc.check_in_progress(_status(ok)) is None


def test_done_step_requires_evidence_file() -> None:
    # S13 has no evidence file in this repo (S13 not done yet); use it for the
    # negative case; keep S0 as the positive case.
    steps = {"S13": {"status": "done"}}
    assert pc.check_evidence_for_done(_status(steps)) is not None


def test_plan_hash_guard_accepts_current_repo() -> None:
    assert pc.check_plan_hash() is None


def test_gold_test_hash_skipped_when_not_frozen() -> None:
    assert pc.check_gold_test_hash() is None


def test_run_all_checks_green_on_current_repo() -> None:
    assert pc.run_all_checks() == []
