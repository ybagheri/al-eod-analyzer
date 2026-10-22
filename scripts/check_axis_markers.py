"""Automatic axis-marker vs pipeline-date check (S2 closure, user step 0).

Mechanism: dated charts show the session month/day as the FIRST axis marker
(and often the next session as the last marker). If the pipeline date disagrees
with the first marker, the date is wrong (same error class as bb12359b02fb and
3fe93407e2d4: a duplicate-row/date-typo override).

Run: python scripts/check_axis_markers.py [--labels ...]
Reads reviewers' recorded markers from artifacts/axis_marker_registry.json and
dates from artifacts/manifest_batch1.json; reports mismatches and charts still
missing a recorded marker.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "artifacts" / "axis_marker_registry.json"
MANIFEST = REPO / "artifacts" / "manifest_batch1.json"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    watched = set(args) if args else None
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["markers"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id: dict[str, dict] = {}
    for record in manifest["records"]:
        if record.get("status") == "ok":
            by_id.setdefault(record["image_id"], record)
    mismatches: list[str] = []
    missing: list[str] = []
    uncheckable: list[str] = []
    checked = 0
    for image_id, record in by_id.items():
        if watched is not None and image_id not in watched:
            continue
        entry = registry.get(image_id)
        if entry is None:
            missing.append(image_id)
            continue
        marker = entry.get("first_marker")
        if marker is None:
            uncheckable.append(f"{image_id}: no date marker on chart")
            continue
        marker = str(marker)
        date = _dt.date.fromisoformat(record["date"])
        if entry.get("semantics") == "next_session":
            date = date + _dt.timedelta(days=1)
        parts = marker.split("/")
        if len(parts) == 2:
            ok = (int(parts[0]), int(parts[1])) == (date.month, date.day)
        else:
            ok = int(parts[0]) == date.day
        checked += 1
        flag = "OK" if ok else "MISMATCH"
        if not ok:
            mismatches.append(f"{image_id}: marker {marker} vs date {date}")
        print(f"{flag:9} {image_id} marker={marker} session_date={record['date']}")
    print(
        f"\nchecked={checked} mismatches={len(mismatches)} "
        f"no-marker-recorded={len(missing)} no-marker-on-chart={len(uncheckable)}"
    )
    for row in uncheckable:
        print("  uncheckable", row)
    if mismatches:
        print("MISMATCHES:")
        for row in mismatches:
            print("  ", row)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
