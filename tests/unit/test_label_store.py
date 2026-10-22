"""Unit tests: taxonomy migration table and the auto-migrating label loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brooks_lab.infrastructure.label_store import (
    TaxonomyMigrations,
    load_day_label,
    load_migrations,
)


def _repo_migrations() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "taxonomy_migrations.yaml"


def _label_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "image_id": "abc",
        "date": "2025-06-02",
        "day_type": "trading_range",
        "day_type_confidence": 0.7,
        "session_summary": "",
        "events": [
            {
                "label": "low_2",
                "raw_label": "low 2",
                "direction": "bear",
                "confidence": 0.8,
            }
        ],
        "extraction_meta": {
            "provider": "file",
            "model_id": "manual",
            "prompt_version": "extract_v2",
        },
    }
    payload.update(overrides)
    return payload


def test_repo_migrations_load() -> None:
    migrations = load_migrations(_repo_migrations())
    assert migrations.taxonomy_version == "1.3"
    # Audit-known rules are present with the expected quality.
    assert migrations.events["low_2"].to == "l2"
    assert migrations.events["low_2"].quality == "exact"
    assert migrations.events["mm"].to == "measured_move"
    assert migrations.events["trading_range"].quality == "lossy"
    assert migrations.day_types["trend_reversal_to_bear_attempt"].quality == "lossy"
    assert migrations.day_types["bear_trend_resumption"].to is None
    # S2.8b R-FINISH rules: legacy ids still present in stored queue data.
    for event_id, target in [
        ("high_2", "h2"),
        ("ii", "inside_inside"),
        ("ooo", "outside_outside"),
        ("expanding_triangle", "triangle"),
        ("gap_up", "gap"),
        ("bull_gap", "gap"),
        ("higher_low_major_trend_reversal", "major_trend_reversal"),
    ]:
        rule = migrations.events[event_id]
        assert rule.to == target and rule.quality == "exact"
    # ADR-013 handler-backed compound rules.
    assert migrations.day_types["bull_channel"].handler == "day_bull_channel"
    assert (
        migrations.day_types["small_pullback_bull_trend_from_open"].to
        == "small_pullback_bull_trend"
    )
    assert migrations.day_types["small_pullback_bull_trend_from_open"].handler == "day_from_open"
    assert migrations.day_types["trending_trading_range"].handler == "day_direction_null"
    assert migrations.day_types["reversal_day"].handler == "day_regime_null"
    compound = {
        "low_2_top": ("l2", "ev_low_2_top"),
        "wedge_bull_channel": ("channel", "ev_wedge_bull_channel"),
        "triple_top": ("double_top", "ev_triple_top"),
        "parabolic_wedge": ("wedge", "ev_parabolic_wedge"),
        "spike_and_channel": (None, "ev_spike_and_channel"),
    }
    for event_id, (target, handler) in compound.items():
        rule = migrations.events[event_id]
        assert rule.to == target and rule.handler == handler
    for event_id in (
        "small_pullback_bull_trend",
        "small_pullback_bear_trend",
        "bull_trending_trading_range",
        "trend_reversal_to_bull",
        "bear_trend_resumption",
    ):
        assert migrations.events[event_id].to is None
        assert migrations.events[event_id].handler == "ev_day_type_as_event"


@pytest.mark.parametrize(
    "content",
    [
        "schema_version: 1\n",
        "schema_version: 1\nevents:\n  low_2: {to: l2}\n",  # missing quality
        "schema_version: 1\nevents:\n  low_2: {to: l2, quality: fuzzy}\n",
        "schema_version: 1\nday_types: []\n",
    ],
)
def test_migrations_reject_malformed(tmp_path: Path, content: str) -> None:
    path = tmp_path / "migrations.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_migrations(path)


def test_migration_exact_event() -> None:
    migrations = TaxonomyMigrations(taxonomy_version="1.3", events={"low_2": _rule("l2", "exact")})
    result = migrations.migrate_event("low_2")
    assert (result.value, result.quality, result.changed) == ("l2", "exact", True)


def test_migration_lossy_event() -> None:
    migrations = TaxonomyMigrations(
        taxonomy_version="1.3", events={"trading_range": _rule("tight_trading_range", "lossy")}
    )
    result = migrations.migrate_event("trading_range")
    assert (result.value, result.quality) == ("tight_trading_range", "lossy")


def test_migration_unknown_event_unmaps() -> None:
    migrations = TaxonomyMigrations(taxonomy_version="1.3")
    result = migrations.migrate_event("no_such_event")
    assert result.value is None
    assert result.quality == "lossy"


def test_migration_current_ids_unchanged() -> None:
    migrations = TaxonomyMigrations(taxonomy_version="1.3")
    for raw in ("h1", "l2", "failed_breakout"):
        assert migrations.migrate_event(raw).changed is False


def test_apply_to_label_migrates_and_flags_lossy() -> None:
    migrations = TaxonomyMigrations(
        taxonomy_version="1.4",
        day_types={"trading_range": _rule("bull_trending_trading_range", "lossy")},
        events={"low_2": _rule("l2", "exact"), "traps": _rule("failed_breakout", "lossy")},
    )
    out = migrations.apply_to_label(
        {
            "image_id": "abc",
            "day_type": "trading_range",
            "events": [
                {"label": "low_2", "raw_label": "low 2", "confidence": 0.8},
                {"label": "traps", "raw_label": "bear trap", "confidence": 0.9},
            ],
            "extraction_meta": {"provider": "file", "model_id": "manual", "prompt_version": "p"},
        }
    )
    assert out["day_type"] == "bull_trending_trading_range"
    assert out["needs_review"] is True
    assert out["events"][0]["label"] == "l2"
    assert "needs_review" not in out["events"][0]
    assert out["events"][1] == {
        "label": "failed_breakout",
        "raw_label": "bear trap",  # original wording preserved
        "confidence": 0.9,
        "needs_review": True,
        "needs_review_reason": "lossy_migration",
        "mapped_from": "traps",
        "rule_id": "1.4:traps",
    }
    assert out["extraction_meta"]["taxonomy_version"] == "1.4"


def test_apply_to_label_keeps_existing_stamp() -> None:
    migrations = TaxonomyMigrations(taxonomy_version="1.4")
    out = migrations.apply_to_label(
        {
            "image_id": "abc",
            "extraction_meta": {
                "provider": "file",
                "model_id": "manual",
                "prompt_version": "p",
                "taxonomy_version": "1.3",
            },
        }
    )
    assert out["extraction_meta"]["taxonomy_version"] == "1.3"


def test_apply_to_label_unknown_day_type_demotes() -> None:
    migrations = TaxonomyMigrations(taxonomy_version="1.4")
    out = migrations.apply_to_label({"image_id": "abc", "day_type": "reversal_day"})
    assert out["day_type"] == "other"
    assert out["needs_review"] is True


def test_load_day_label_migrates_legacy_file(tmp_path: Path) -> None:
    path = tmp_path / "abc.json"
    path.write_text(
        json.dumps(_label_payload(day_type="trend_reversal_to_bear_attempt")), encoding="utf-8"
    )
    migrations = load_migrations(_repo_migrations())
    label = load_day_label(path, migrations)
    assert str(label.day_type.value) == "trend_reversal_to_bear"
    assert label.needs_review is True
    assert label.extraction_meta.taxonomy_version == "1.3"
    # Legacy payload stays valid even without new optional fields.
    assert label.scope_ok is None
    assert label.axis is None
    assert label.anchors is None


def test_load_day_label_keeps_raw_label_on_lossy_event(tmp_path: Path) -> None:
    path = tmp_path / "abc.json"
    path.write_text(
        json.dumps(_label_payload()), encoding="utf-8"
    )  # event label low_2, raw "low 2"
    label = load_day_label(path, load_migrations(_repo_migrations()))
    event = label.events[0]
    assert event.label is not None and event.label.value == "l2"
    assert event.raw_label == "low 2"
    assert event.needs_review is False


def _rule(to: str | None, quality: str):  # type: ignore[no-untyped-def]
    from brooks_lab.infrastructure.label_store import MigrationRule

    return MigrationRule(to=to, quality=quality)
