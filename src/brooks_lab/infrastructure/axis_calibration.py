"""Axis-calibration hook (Phase 1: honest best-effort placeholder).

Pixel-to-time/price mapping needs OCR of axis tick labels (Tesseract, optional).
This module exposes the result contract and a non-blocking attempt function so the
pipeline never fails when calibration is unavailable. Real detection lands later.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AxisCalibrationAttempt:
    """Outcome of one calibration attempt. ``mapper`` arrives in a later phase."""

    ok: bool
    reason: str


def attempt_axis_calibration(image_path: Path) -> AxisCalibrationAttempt:
    """Try to calibrate ``image_path``; return a reasoned miss when impossible.

    Never raises and never blocks ingestion: without Tesseract there is nothing
    to detect ticks with, so the attempt is recorded as unavailable.
    """
    _ = image_path
    if shutil.which("tesseract") is None:
        return AxisCalibrationAttempt(
            ok=False,
            reason="axis calibration unavailable: Tesseract OCR is not installed",
        )
    return AxisCalibrationAttempt(
        ok=False,
        reason="axis calibration not implemented yet (tick detection lands later)",
    )
