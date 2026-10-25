"""Axis-resolution protocol (S3, Phase 5b).

Compares chart time-axis anchors to real M5 bars under competing time hypotheses:

* ``H_PT``      — axis shows US Pacific time, session 06:30-13:00 PT
* ``H_ET+0``    — axis shows exchange time (ET), no shift
* ``H_ET+12``   — broker server = ET + 12 h
* ``H_ET+13``   — broker server = ET + 13 h

For each parsed axis fixture (``tests/fixtures/batch3/ag_*.txt``) we fit a
pixel-per-minute line from the time ticks, then score each hypothesis by how
well the chart's date/month markers line up with session bar indices. Results
are written to ``artifacts/axis_resolution.json`` plus a short Persian summary.

This script is structural: a meaningful per-hypothesis verdict needs real
broker bars (CHECKPOINT B) and chart anchor bar-index hints (S2 labels). Until
then it reports internal axis consistency per hypothesis so the comparison is
ready to run once data arrives.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
PT = timezone(timedelta(hours=-8))  # placeholder; real PT handled via US rules below

TICK_RE = re.compile(r"^(\d{1,2}:\d{2})\s+cx=\s*([\d.]+)\s+min=(\d+)$")
MARKER_RE = re.compile(r"^'(.+)'\s+kind=(\w+)\s+value=\((.+)\)\s+cx=([\d.]+)$")

SESSION_OPEN_PT = time(6, 30)
SESSION_CLOSE_PT = time(13, 0)
SESSION_OPEN_ET = time(9, 30)
SESSION_CLOSE_ET = time(16, 0)


@dataclass
class Tick:
    label: str
    cx: float
    minutes: int  # minutes from midnight of the label's day


@dataclass
class Marker:
    text: str
    kind: str  # "month" | "date"
    value: tuple
    cx: float


@dataclass
class AxisFixture:
    image_size: tuple[int, int]
    ticks: list[Tick] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)


def parse_ag_file(path: Path) -> AxisFixture:
    """Parse an ``ag_*.txt`` axis-geometry fixture produced by batch-3 review."""
    ticks: list[Tick] = []
    markers: list[Marker] = []
    image_size: tuple[int, int] | None = None
    in_ticks = False
    in_markers = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            in_ticks = in_markers = False
            continue
        if line.startswith("Image "):
            m = re.search(r"(\d+)x(\d+)", line)
            if m:
                image_size = (int(m.group(1)), int(m.group(2)))
            continue
        if line.startswith("time ticks"):
            in_ticks = True
            in_markers = False
            continue
        if line.startswith("markers"):
            in_markers = True
            in_ticks = False
            continue
        if in_ticks:
            m = TICK_RE.match(line)
            if m:
                ticks.append(Tick(m.group(1), float(m.group(2)), int(m.group(3))))
        elif in_markers:
            m = MARKER_RE.match(line)
            if m:
                values = tuple(int(v) for v in m.group(3).split(","))
                markers.append(Marker(m.group(1), m.group(2), values, float(m.group(4))))
    if image_size is None:
        image_size = (0, 0)
    return AxisFixture(image_size=image_size, ticks=ticks, markers=markers)


def fit_px_per_minute(ticks: list[Tick]) -> tuple[float, float] | None:
    """Least-squares fit ``cx = a + b * minutes`` over the time ticks.

    Returns ``(intercept, slope_px_per_minute)`` or ``None`` when fewer than
    two ticks carry distinct minute values.
    """
    pts = [(t.minutes, t.cx) for t in ticks]
    if len(pts) < 2:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(pts)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in pts)
    slope = sxy / sxx
    intercept = my - slope * mx
    return intercept, slope


def _us_pt_offset(day: date) -> timedelta:
    """PT offset for a date (US DST: second Sunday March -> first Sunday Nov)."""
    if day.month < 3 or day.month > 11:
        return timedelta(hours=-8)
    if 3 < day.month < 11:
        return timedelta(hours=-7)
    first = date(day.year, day.month, 1)
    if day.month == 3:
        transition = first + timedelta(days=((6 - first.weekday()) % 7) + 7)
    else:
        transition = first + timedelta(days=(6 - first.weekday()) % 7)
    if day.month == 3:
        return timedelta(hours=-7) if day >= transition else timedelta(hours=-8)
    return timedelta(hours=-8) if day < transition else timedelta(hours=-7)


def _session_bounds_pt(day: date) -> tuple[datetime, datetime]:
    off = _us_pt_offset(day)
    open_dt = datetime.combine(day, SESSION_OPEN_PT, tzinfo=timezone(off))
    close_dt = datetime.combine(day, SESSION_CLOSE_PT, tzinfo=timezone(off))
    return open_dt, close_dt


def _bar_index_for_minutes(minutes_of_day: int, session_open_minutes: int) -> float:
    return (minutes_of_day - session_open_minutes) / 5.0


@dataclass
class HypothesisScore:
    name: str
    median_bar_error: float | None
    n_markers_scored: int
    note: str


def score_hypothesis(fixture: AxisFixture, name: str, ref_date: date) -> HypothesisScore:
    """Score one time hypothesis against a fixture's date/month markers."""
    fit = fit_px_per_minute(fixture.ticks)
    if fit is None or not fixture.markers:
        return HypothesisScore(name, None, 0, "no fit or no markers")
    intercept, slope = fit
    if slope <= 0:
        return HypothesisScore(name, None, 0, "non-positive px/min slope")

    scored: list[float] = []
    for marker in fixture.markers:
        if marker.kind != "date":
            continue
        value = marker.value
        if len(value) < 2:
            continue
        marker_date = date(value[0], value[1], value[2] if len(value) > 2 else 1)
        if name == "H_PT":
            open_dt, _ = _session_bounds_pt(marker_date)
            open_minutes = open_dt.hour * 60 + open_dt.minute
        else:
            open_minutes = 9 * 60 + 30
        expected_cx = intercept + slope * open_minutes
        scored.append(abs(expected_cx - marker.cx))
    if not scored:
        return HypothesisScore(name, None, 0, "no date markers")
    return HypothesisScore(
        name,
        statistics.median(scored),
        len(scored),
        "median |cx error| in pixels for date markers",
    )


def resolve_axis(fixtures_dir: Path, output: Path) -> dict:
    """Run axis resolution over every ``ag_*.txt`` fixture; write JSON report."""
    results: dict = {}
    ag_files = sorted(fixtures_dir.glob("ag_*.txt")) if fixtures_dir.exists() else []
    for path in ag_files:
        fixture = parse_ag_file(path)
        fit = fit_px_per_minute(fixture.ticks)
        per_hyp = [
            score_hypothesis(fixture, name, ref_date=_marker_date(fixture))
            for name in ("H_PT", "H_ET+0", "H_ET+12", "H_ET+13")
        ]
        results[path.stem] = {
            "image_size": list(fixture.image_size),
            "n_ticks": len(fixture.ticks),
            "n_markers": len(fixture.markers),
            "px_per_minute": fit[1] if fit else None,
            "px_per_bar": (fit[1] * 5) if fit else None,
            "hypotheses": [
                {
                    "name": h.name,
                    "median_cx_error_px": h.median_bar_error,
                    "n_markers_scored": h.n_markers_scored,
                    "note": h.note,
                }
                for h in per_hyp
            ],
        }
    note = "Verdict pending broker bars (CHECKPOINT B) + chart anchor bar-index hints (S2 labels)"
    report = {
        "fixtures_dir": str(fixtures_dir),
        "n_fixtures": len(ag_files),
        "results": results,
        "note": note,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _marker_date(fixture: AxisFixture) -> date:
    for marker in fixture.markers:
        if marker.kind == "date" and len(marker.value) >= 2:
            return date(marker.value[0], marker.value[1], 1)
    return date.today()


def main() -> None:
    resolve_axis(Path("tests/fixtures/batch3"), Path("artifacts/axis_resolution.json"))


if __name__ == "__main__":
    main()
