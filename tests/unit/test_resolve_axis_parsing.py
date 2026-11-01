"""Regression tests for scripts/resolve_axis.py marker parsing.

Covers both whitespace (`cx= 210.0`) and no-whitespace (`cx=210.0`) variants
found in batch-3 axis-geometry fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from resolve_axis import MARKER_RE, TICK_RE, parse_ag_file

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "batch3"


def test_marker_re_whitespace_variant() -> None:
    """cx= with a space after '=' (as in real fixtures)."""
    line = "'Sep' kind=month value=(9,) cx= 210.0"
    m = MARKER_RE.match(line)
    assert m is not None, f"MARKER_RE failed on whitespace variant: {line!r}"
    assert m.group(1) == "Sep"
    assert m.group(2) == "month"
    # group(3) is the raw inside of value=(...), which includes trailing comma
    assert m.group(3) == "9,"
    assert m.group(4) == "210.0"


def test_marker_re_no_whitespace_variant() -> None:
    """cx= with no space after '='."""
    line = "'9/2' kind=date value=(9, 2) cx=1550.0"
    m = MARKER_RE.match(line)
    assert m is not None, f"MARKER_RE failed on no-whitespace variant: {line!r}"
    assert m.group(1) == "9/2"
    assert m.group(2) == "date"
    assert m.group(3) == "9, 2"
    assert m.group(4) == "1550.0"


def test_marker_re_multiple_dates() -> None:
    """cx= with space, multi-value tuple (e.g. (3, 30))."""
    line = "'3/30' kind=date value=(3, 30) cx= 291.5"
    m = MARKER_RE.match(line)
    assert m is not None
    assert m.group(1) == "3/30"
    assert m.group(2) == "date"
    assert m.group(3) == "3, 30"
    assert m.group(4) == "291.5"


def test_tick_re_whitespace_variant() -> None:
    """TICK_RE should already handle cx= with space (regression guard)."""
    line = "07:00 cx= 292.5 min=420"
    m = TICK_RE.match(line)
    assert m is not None
    assert m.group(1) == "07:00"
    assert m.group(2) == "292.5"
    assert m.group(3) == "420"


def test_parse_ag_file_recognizes_markers() -> None:
    """End-to-end: real fixtures must produce non-empty marker lists."""
    for ag_file in sorted(FIXTURES_DIR.glob("ag_*.txt")):
        fixture = parse_ag_file(ag_file)
        assert fixture.markers, f"{ag_file.name}: no markers parsed (MARKER_RE bug?)"
        # Every marker must have a non-empty cx value
        for marker in fixture.markers:
            assert marker.cx > 0, f"{ag_file.name}: marker cx missing: {marker}"


if __name__ == "__main__":
    test_marker_re_whitespace_variant()
    test_marker_re_no_whitespace_variant()
    test_marker_re_multiple_dates()
    test_tick_re_whitespace_variant()
    test_parse_ag_file_recognizes_markers()
    print("All resolve_axis parsing regression tests passed.")
