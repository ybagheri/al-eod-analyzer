"""One-off taxonomy v1.1 remap (ADR-006): apply user-approved canonical assignments.

Matches events by verbatim raw_label and migrates them via ReviewService
(history archived, touched events marked human with the approval reviewer).
Re-run safe: already-mapped events are skipped unless include_mapped is set.

Usage: python scripts/remap_taxonomy_v11.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from brooks_lab.application.ingestion import ImageIngestionService  # noqa: E402
from brooks_lab.application.review import (  # noqa: E402
    EventRemap,
    ReviewService,
    load_labels_for_manifest,
)
from brooks_lab.domain.labels import Direction, EventKind  # noqa: E402

REVIEWER = "ybagheri (taxonomy v1.1 approvals 2026-10-12, applied by agent)"

# raw_label -> (canonical kind | None for demotion, direction | None to set).
REMAPS: dict[str, tuple[EventKind | None, Direction | None, bool]] = {
    "Minor OO": (EventKind.OUTSIDE_OUTSIDE, Direction.NEUTRAL, False),
    "OO": (EventKind.OUTSIDE_OUTSIDE, Direction.NEUTRAL, False),
    "ii": (EventKind.INSIDE_INSIDE, Direction.NEUTRAL, False),
    "Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "Possible Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "Expanding Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "Nested Expanding Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "Exp. Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "Ext. Triangle": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "triangle lines": (EventKind.TRIANGLE, Direction.NEUTRAL, False),
    "TTR on open": (EventKind.TIGHT_TRADING_RANGE, Direction.NEUTRAL, False),
    "TTR better to stop trading": (EventKind.TIGHT_TRADING_RANGE, Direction.NEUTRAL, False),
    "TTR best to wait for BO": (EventKind.TIGHT_TRADING_RANGE, Direction.NEUTRAL, False),
    "Tight TR ahead of FOMC minutes": (
        EventKind.TIGHT_TRADING_RANGE,
        Direction.NEUTRAL,
        True,  # was trading_range_begin; the note is about tightness
    ),
    "HST": (EventKind.HEAD_AND_SHOULDERS_TOP, Direction.BEAR, False),
    "Head and Shoulders Top": (EventKind.HEAD_AND_SHOULDERS_TOP, Direction.BEAR, False),
    "LL MTR": (EventKind.MAJOR_TREND_REVERSAL, Direction.BULL, False),
    "HL MTR": (EventKind.MAJOR_TREND_REVERSAL, Direction.BULL, False),
    "LH DT MTR": (EventKind.MAJOR_TREND_REVERSAL, Direction.BEAR, False),
    "LL DB MTR": (EventKind.MAJOR_TREND_REVERSAL, Direction.BULL, False),
    "2nd entry buy DB LL MTR": (EventKind.MAJOR_TREND_REVERSAL, Direction.BULL, False),
    "LL MTR swing buy": (EventKind.MAJOR_TREND_REVERSAL, Direction.BULL, False),
    "Lower High Major Trend Reversal": (
        EventKind.MAJOR_TREND_REVERSAL,
        Direction.BEAR,
        False,
    ),
    "Bar 40 Midday Reversal": (EventKind.MIDDAY_REVERSAL, Direction.BULL, False),
    "Bar 41 Midday Trend Reversal": (EventKind.MIDDAY_REVERSAL, Direction.BEAR, False),
    "reversal up on bar 41 (Midday Reversal)": (
        EventKind.MIDDAY_REVERSAL,
        Direction.BULL,
        False,
    ),
    "LL DB": (EventKind.LOWER_LOW_DOUBLE_BOTTOM, Direction.BULL, False),
    "LL DB at EMA": (EventKind.LOWER_LOW_DOUBLE_BOTTOM, Direction.BULL, False),
    "LL DB Breakout Test": (EventKind.LOWER_LOW_DOUBLE_BOTTOM, Direction.BULL, False),
    "Bear Trap": (EventKind.FAILED_BREAKOUT, Direction.BEAR, False),
    "Bull Trap": (EventKind.FAILED_BREAKOUT, Direction.BULL, False),
    "2nd Leg Bull Trap": (EventKind.FAILED_BREAKOUT, Direction.BULL, False),
    "Trend Resumption up": (EventKind.BREAKOUT, Direction.BULL, False),
    # User-approved demotion: stays in raw_label, loses the forced canonical id.
    "Measuring Gap": (None, None, True),
    # Same concept, plural form (agent judgment, reversible; flagged in report).
    "Measuring Gaps": (None, None, True),
}


def main() -> int:
    """Run the v1.1 remap over every labeled manifest record."""
    manifest = ImageIngestionService.read_manifest(REPO / "artifacts" / "manifest.json")
    labels_dir = REPO / "artifacts" / "labels"
    service = ReviewService(
        labels_dir=labels_dir,
        history_dir=REPO / "artifacts" / "labels_history",
        gold_path=REPO / "artifacts" / "gold_set.json",
    )
    rules = [
        EventRemap(raw_label=raw, new_label=kind, direction=direction, include_mapped=inc)
        for raw, (kind, direction, inc) in REMAPS.items()
    ]
    labels = load_labels_for_manifest(manifest, labels_dir)
    touched = 0
    for label in labels:
        result = service.remap_events(label.image_id, rules, reviewer=REVIEWER)
        print(f"{label.image_id}: applied={result.applied} {result.message}")
        if result.applied:
            touched += 1
    print(f"labels touched: {touched}/{len(labels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
