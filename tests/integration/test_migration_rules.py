"""ADR-013 migration rules: unit behaviour + on-chart tests against stored labels.

Each rule implemented per the user's 2026-10-20 decisions is tested both in
isolation (synthetic payloads) and against the stored label file(s) of the
chart(s) it came from (invariants: raw kept, direction/outcome preserved,
mapped_from + rule_id recorded, attributes not lost).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from brooks_lab.infrastructure.label_store import load_migrations

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "artifacts" / "labels"


def _migrations():
    return load_migrations(REPO / "config" / "taxonomy_migrations.yaml")


def _payload(day_type: str = "trading_range", summary: str = "", events: list[dict] | None = None):
    return {
        "schema_version": 1,
        "image_id": "id-1",
        "date": "2022-07-29",
        "day_type": day_type,
        "day_type_confidence": 0.8,
        "session_summary": summary,
        "events": events if events is not None else [],
        "extraction_meta": {"provider": "file", "model_id": "m", "prompt_version": "extract_v2"},
    }


def _event(label: str, **kw: Any) -> dict[str, Any]:
    row = {"label": label, "raw_label": label.replace("_", " "), "confidence": 0.8}
    row.update(kw)
    return row


# --- day rules ---------------------------------------------------------------


def test_bull_channel_bare_keeps_id_with_width_unspecified() -> None:
    out = _migrations().apply_to_label(_payload(day_type="bull_channel"))
    assert out["day_type"] == "bull_channel"
    assert "width_unspecified" in out["modifiers"]
    assert out["needs_review"] and out["needs_review_reason"] == "width_unspecified"
    assert out["mapped_from"] == "bull_channel"
    assert out["rule_id"] == "1.3:bull_channel"


def test_bull_channel_broad_and_tight_resolved_by_title() -> None:
    m = _migrations()
    broad = m.apply_to_label(_payload(day_type="bull_channel", summary="broad bull channel day"))
    assert broad["day_type"] == "broad_bull_channel"
    assert not broad.get("needs_review")
    tight = m.apply_to_label(
        _payload(day_type="bull_channel", summary="tight channel small pullbacks")
    )
    assert tight["day_type"] == "small_pullback_bull_trend"


def test_from_open_keeps_info_and_flags_missing_evidence() -> None:
    m = _migrations()
    out = m.apply_to_label(_payload(day_type="small_pullback_bull_trend_from_open"))
    assert out["day_type"] == "small_pullback_bull_trend"
    assert out["starts_at_session_open"] is None
    assert out["starts_at_session_open_source"] == "none"
    assert out["needs_review_reason"] == "missing_evidence"
    seen = m.apply_to_label(
        _payload(
            day_type="small_pullback_bear_trend_from_open",
            summary="Bear trend from the open; ...",
        )
    )
    assert seen["day_type"] == "small_pullback_bear_trend"
    assert seen["starts_at_session_open"] is True
    assert seen["starts_at_session_open_source"] == "title"


def test_trending_trading_range_and_reversal_day_direction_reasons() -> None:
    m = _migrations()
    tr = m.apply_to_label(_payload(day_type="trending_trading_range"))
    assert tr["day_type"] == "other" and tr["needs_review_reason"] == "direction_missing"
    rd = m.apply_to_label(_payload(day_type="reversal_day"))
    assert rd["day_type"] == "other" and rd["needs_review_reason"] == "regime_direction_missing"


# --- event rules -------------------------------------------------------------


def test_low_2_top_maps_to_l2_at_top() -> None:
    out = _migrations().apply_to_label(
        _payload(events=[_event("low_2_top", direction="bear", outcome="fail")])
    )
    row = out["events"][0]
    assert row["label"] == "l2" and "at_top" in row["modifiers"]
    assert row["direction"] == "bear" and row["outcome"] == "fail"  # untouched
    assert row["mapped_from"] == "low_2_top" and row["rule_id"] == "1.3:low_2_top"


def test_wedge_bull_channel_maps_to_channel_with_wedges() -> None:
    out = _migrations().apply_to_label(
        _payload(events=[_event("wedge_bull_channel", direction="bull")])
    )
    row = out["events"][0]
    assert row["label"] == "channel" and "with_wedges" in row["modifiers"]
    assert row["direction"] == "bull"


def test_triple_top_maps_to_double_top_third_touch() -> None:
    out = _migrations().apply_to_label(_payload(events=[_event("triple_top", direction="bear")]))
    row = out["events"][0]
    assert row["label"] == "double_top" and "third_touch" in row["modifiers"]
    assert row["needs_review"] and row["needs_review_reason"] == "alternative_mapping"


def test_parabolic_wedge_at_top_bottom_and_ambiguous() -> None:
    m = _migrations()
    bear = m.apply_to_label(_payload(events=[_event("parabolic_wedge", direction="bear")]))
    assert bear["events"][0]["label"] == "wedge"
    assert "parabolic" in bear["events"][0]["modifiers"]
    assert "at_top" in bear["events"][0]["modifiers"]
    bull = m.apply_to_label(_payload(events=[_event("parabolic_wedge", direction="bull")]))
    assert "at_bottom" in bull["events"][0]["modifiers"]
    neutral = m.apply_to_label(_payload(events=[_event("parabolic_wedge", direction="neutral")]))
    assert neutral["events"][0]["needs_review_reason"] == "ambiguous_direction"


def test_spike_and_channel_split_and_missing_evidence() -> None:
    m = _migrations()
    titled = m.apply_to_label(
        _payload(summary="Spike and Channel Bull Trend", events=[_event("spike_and_channel")])
    )
    labels = [row["label"] for row in titled["events"]]
    assert labels == ["spike", "channel"]
    assert titled["events"][0]["linked_to"] == "1.3:spike_and_channel:channel"
    assert titled["events"][1]["linked_to"] == "1.3:spike_and_channel:spike"
    untitled = m.apply_to_label(_payload(events=[_event("spike_and_channel")]))
    row = untitled["events"][0]
    assert row["label"] is None and row["needs_review_reason"] == "missing_evidence"
    assert row["raw_label"] == "spike and channel"


def test_day_type_used_as_event_unmaps_with_reason() -> None:
    out = _migrations().apply_to_label(
        _payload(events=[_event("bear_trend_resumption", direction="bull")])
    )
    row = out["events"][0]
    assert row["label"] is None
    assert row["raw_label"] == "bear trend resumption"  # kept verbatim
    assert row["needs_review_reason"] == "day_type_used_as_event"


# --- on-chart tests: every rule tested on the chart(s) it came from ----------


def _stored_legacy_payloads() -> list[tuple[str, dict[str, Any]]]:
    """Golden payloads carrying legacy ids.

    ADR-013: each rule gets a test on the chart it came from. Charts whose
    queue responses were replaced by the v3 calibration re-baseline keep their
    golden legacy payload frozen under ``tests/fixtures/migration/``; newly
    matching live-queue payloads are picked up as well.
    """
    legacy = {
        "bull_channel",
        "trending_trading_range",
        "reversal_day",
        "small_pullback_bull_trend_from_open",
        "small_pullback_bear_trend_from_open",
        "low_2_top",
        "wedge_bull_channel",
        "triple_top",
        "parabolic_wedge",
        "spike_and_channel",
        "trend_reversal_to_bear_attempt",
        "high_2",
        "ii",
        "ooo",
        "expanding_triangle",
        "gap_up",
        "gap_down",
        "bull_gap",
        "higher_low_major_trend_reversal",
    }

    def _matches(payload: dict[str, Any]) -> bool:
        return payload.get("day_type") in legacy or any(
            e.get("label") in legacy for e in payload.get("events") or []
        )

    found: list[tuple[str, dict[str, Any]]] = []
    roots = (
        REPO / "tests" / "fixtures" / "migration",
        REPO / "artifacts" / "extraction_queue",
    )
    seen: set[str] = set()
    for root in roots:
        for path in sorted(root.glob("*.response.json")):
            image_id = path.name.replace(".response.json", "")
            if not path.name.endswith(".response.json") or image_id in seen:
                # queue goldens always win over fixture copies would double-count
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if _matches(payload):
                found.append((image_id, payload))
                seen.add(image_id)
    return found


@pytest.mark.parametrize("image_id,payload", _stored_legacy_payloads(), ids=lambda v: str(v))
def test_stored_legacy_labels_migrate_safely(image_id: str, payload: dict[str, Any]) -> None:
    """Invariants for every stored chart carrying a legacy id (ADR-013)."""
    original_events = list(payload.get("events") or [])
    original_day = {
        "date": payload.get("date"),
        "session_summary": payload.get("session_summary"),
        "day_type_confidence": payload.get("day_type_confidence"),
    }
    migrated = _migrations().apply_to_label(dict(payload))
    # Direction/outcome never change at the event level (rows matched by order+raw).
    joined = [row for row in migrated["events"] if isinstance(row, dict)]
    assert len(original_events) == len(joined)
    for before, after in zip(original_events, joined, strict=False):
        for attr in ("direction", "outcome"):
            if attr in before:
                assert after.get(attr) == before[attr], (image_id, attr, before, after)
        # raw kept or (unmapped) marked with mapped_from provenance
        for key in ("mapped_from", "rule_id"):
            if after.get("label") != before.get("label"):
                assert key in after, (image_id, key, before, after)
    for key, value in original_day.items():
        assert migrated.get(key) == value, (image_id, key)
