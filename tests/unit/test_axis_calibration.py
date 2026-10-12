"""Unit tests: axis-calibration hook never blocks and reports honestly."""

from __future__ import annotations

from pathlib import Path

from brooks_lab.infrastructure.axis_calibration import attempt_axis_calibration


def test_axis_calibration_reports_unavailable(tmp_path: Path) -> None:
    attempt = attempt_axis_calibration(tmp_path / "chart.jpg")
    assert attempt.ok is False
    assert attempt.reason != ""
