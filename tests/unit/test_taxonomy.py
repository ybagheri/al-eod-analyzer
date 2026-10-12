"""Unit tests: taxonomy loading, synonym mapping, unknown routing, review queue."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from brooks_lab.application.review_queue import build_review_queue, suggest_canonical
from brooks_lab.domain.labels import (
    DayLabel,
    DayType,
    EventKind,
    EventLabel,
    ExtractionMeta,
)
from brooks_lab.infrastructure.taxonomy import Taxonomy, load_taxonomy


def _repo_taxonomy() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "taxonomy.yaml"


def test_repo_taxonomy_loads_v1() -> None:
    taxonomy = load_taxonomy(_repo_taxonomy())
    assert taxonomy.schema_version == 1
    assert len(taxonomy.day_types) == 14
    assert len(taxonomy.events) == 38
    assert "other" in taxonomy.day_types


def test_taxonomy_rejects_version_mismatch(tmp_path: Path) -> None:
    bad = tmp_path / "taxonomy.yaml"
    bad.write_text("schema_version: 99\nday_types: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_taxonomy(bad)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("spike_and_channel_bull", DayType.SPIKE_AND_CHANNEL_BULL),
        ("Spike and Channel Bull Trend", DayType.SPIKE_AND_CHANNEL_BULL),
        ("  BULL TREND FROM THE OPEN ", DayType.BULL_TREND_FROM_OPEN),
        ("trading-range-day", DayType.TRADING_RANGE),
    ],
)
def test_day_type_mapping(raw: str, expected: DayType) -> None:
    assert load_taxonomy(_repo_taxonomy()).normalise_day_type(raw) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("h2", EventKind.H2),
        ("H2", EventKind.H2),
        ("Buy The Close", EventKind.BUY_THE_CLOSE),
        ("buy-the-close", EventKind.BUY_THE_CLOSE),
        ("LH DT", EventKind.LOWER_HIGH_DOUBLE_TOP),
        ("HL DB", EventKind.HIGHER_LOW_DOUBLE_BOTTOM),
        ("50% Pullback", EventKind.PULLBACK_50PCT),
        ("Second Entry", None),
        ("", None),
    ],
)
def test_event_mapping_and_unknowns(raw: str, expected: EventKind | None) -> None:
    assert load_taxonomy(_repo_taxonomy()).normalise_event(raw) is expected


def test_empty_taxonomy_maps_nothing() -> None:
    assert Taxonomy().normalise_event("H2") is None
    assert Taxonomy().normalise_day_type("Trading Range") is None


def _day_with(image_id: str, *raw_labels: str) -> DayLabel:
    meta = ExtractionMeta(provider="file", model_id="m", prompt_version="v")
    return DayLabel(
        image_id=image_id,
        date=datetime.date(2022, 7, 29),
        extraction_meta=meta,
        events=[EventLabel(label=None, raw_label=raw) for raw in raw_labels],
    )


def test_review_queue_counts_and_suggests() -> None:
    queue = build_review_queue(
        [
            _day_with("id-1", "Second Entry", "buy-the-cloze"),
            _day_with("id-2", "Second Entry"),
        ],
        canonical_ids=["second_entry", "buy_the_close"],
    )
    assert [item.raw_label for item in queue.items] == ["Second Entry", "buy-the-cloze"]
    second = queue.items[0]
    assert second.count == 2
    assert second.image_ids == ["id-1", "id-2"]
    assert second.suggestion == "second_entry"
    assert queue.items[1].suggestion == "buy_the_close"


def test_review_queue_empty_and_no_suggestion() -> None:
    assert build_review_queue([]).items == []
    assert suggest_canonical("zzz-no-match", ["h1", "h2"]) is None
