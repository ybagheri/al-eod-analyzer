"""ADR-013 dry-run: replay the migration rules on 12 stored label charts.

Deliverable per user decision (2026-10-20):
- rows per chart,
- remapped count by rule_id,
- needs_review count by reason,
- attributes lost (must be 0),
- rows whose direction or outcome would change (must be empty).

Read-only replay (no extractor/reviewer calls). Writes
``artifacts/migration_dryrun.json`` and prints a summary; exit code 1 when the
"must be 0 / must be empty" guarantees are violated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from brooks_lab.domain.labels import DayLabel
from brooks_lab.infrastructure.label_store import load_migrations

REPO = Path(__file__).resolve().parents[1]
PROTECTED = (
    "direction",
    "outcome",
    "start_time",
    "end_time",
    "bar_index_hint",
    "price_hint",
    "confidence",
    "label_explicit",
    "placement",
    "x_px",
    "evidence",
    "source",
    "role",
)
AFFECTED_DAY = {
    "bull_channel",
    "trending_trading_range",
    "reversal_day",
    "small_pullback_bull_trend_from_open",
    "small_pullback_bear_trend_from_open",
    "trend_reversal_to_bear_attempt",
}
AFFECTED_EVENT = {
    "low_2_top",
    "wedge_bull_channel",
    "triple_top",
    "parabolic_wedge",
    "spike_and_channel",
    "high_2",
    "ii",
    "ooo",
    "expanding_triangle",
    "gap_up",
    "gap_down",
    "bull_gap",
    "low_2",
    "mm",
    "traps",
    "trap",
    "trading_range",
    "small_pullback_bull_trend",
    "small_pullback_bear_trend",
    "bull_trending_trading_range",
    "trend_reversal_to_bull",
    "bear_trend_resumption",
}


def _affected(raw: dict[str, Any]) -> bool:
    if raw.get("day_type") in AFFECTED_DAY:
        return True
    for event in raw.get("events") or []:
        if isinstance(event, dict) and event.get("label") in AFFECTED_EVENT:
            return True
    return False


def _match_source(
    migrated_row: dict[str, Any], available: list[dict[str, Any]], used: list[bool]
) -> dict[str, Any] | None:
    raw_label = str(migrated_row.get("raw_label") or "")
    for idx, source in enumerate(available):
        if used[idx]:
            continue
        if str(source.get("raw_label") or "") == raw_label:
            used[idx] = True
            return source
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-dir", type=Path, default=REPO / "artifacts" / "extraction_queue")
    parser.add_argument(
        "--migrations", type=Path, default=REPO / "config" / "taxonomy_migrations.yaml"
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--out", type=Path, default=REPO / "artifacts" / "migration_dryrun.json")
    args = parser.parse_args()

    migrations = load_migrations(args.migrations)
    charts: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(args.labels_dir.glob("*.response.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw.get("day_type"), str):
            continue  # not a v1 day-label response (request files etc.)
        if _affected(raw):
            charts.append((path.name.replace(".response.json", ""), raw))
    charts = charts[: args.limit]

    attributes_lost = 0
    direction_outcome_changes: list[dict[str, Any]] = []
    remap_totals: dict[str, int] = {}
    review_totals: dict[str, int] = {}
    charts_out: list[dict[str, Any]] = []
    for image_id, raw in charts:
        before = [event for event in (raw.get("events") or []) if isinstance(event, dict)]
        used: list[bool] = [False] * len(before)
        migrated = migrations.apply_to_label(dict(raw))
        DayLabel.model_validate(migrated)  # validate shape through the domain model
        events_out = migrated.get("events") or []
        remapped: dict[str, int] = {}
        reviews: dict[str, int] = {}
        for row in events_out:
            if not isinstance(row, dict):
                continue
            rule = row.get("rule_id")
            if rule:
                remapped[rule] = remapped.get(rule, 0) + 1
                remap_totals[rule] = remap_totals.get(rule, 0) + 1
            reason = row.get("needs_review_reason")
            if row.get("needs_review") and reason:
                reviews[reason] = reviews.get(reason, 0) + 1
                review_totals[reason] = review_totals.get(reason, 0) + 1
            source = _match_source(row, before, used) if row.get("mapped_from") else None
            if source is not None:
                for attr in PROTECTED:
                    if attr in source and row.get(attr) != source.get(attr):
                        attributes_lost += 1
                        direction_outcome_changes.append(
                            {
                                "image_id": image_id,
                                "rule_id": rule,
                                "attr": attr,
                                "before": source.get(attr),
                                "after": row.get(attr),
                                "raw_label": row.get("raw_label"),
                            }
                        )
        if migrated.get("needs_review") and migrated.get("needs_review_reason"):
            reason = migrated["needs_review_reason"]
            reviews[reason] = reviews.get(reason, 0) + 1
            review_totals[reason] = review_totals.get(reason, 0) + 1
        charts_out.append(
            {
                "image_id": image_id,
                "day_type_before": raw.get("day_type"),
                "day_type_after": migrated.get("day_type"),
                "rows": 1 + len(events_out),
                "remapped": remapped,
                "needs_review_by_reason": reviews,
            }
        )
    report: dict[str, Any] = {
        "schema_version": 1,
        "limit": args.limit,
        "charts": charts_out,
        "totals": {
            "remapped_by_rule": remap_totals,
            "needs_review_by_reason": review_totals,
            "attributes_lost": attributes_lost,
            "direction_outcome_changes": direction_outcome_changes,
        },
        "guarantees": {
            "attributes_lost": attributes_lost,
            "direction_outcome_changes": len(direction_outcome_changes),
        },
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"charts: {len(charts_out)} -> {args.out}")
    print(f"remapped by rule: {remap_totals}")
    print(f"needs_review by reason: {review_totals}")
    print(
        f"guarantees: attributes_lost={attributes_lost} "
        f"direction_outcome_changes={len(direction_outcome_changes)}"
    )
    return 1 if (attributes_lost or direction_outcome_changes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
