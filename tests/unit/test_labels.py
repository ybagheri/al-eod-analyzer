"""Unit tests: label schema validation, migration stub, JSON round-trip."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from brooks_lab.domain.labels import (
    ChartTime,
    DayLabel,
    DayType,
    Direction,
    EventKind,
    EventLabel,
    ExtractionMeta,
    LabelSource,
    Outcome,
    migrate_day_label,
)


def _meta() -> ExtractionMeta:
    return ExtractionMeta(provider="file", model_id="manual", prompt_version="extract_v1")


def _event() -> EventLabel:
    return EventLabel(
        label=EventKind.BUY_THE_CLOSE,
        raw_label="Buy The Close",
        direction=Direction.BULL,
        start_time=ChartTime(time="12:55"),
        outcome=Outcome.SUCCESS,
        confidence=0.8,
        evidence="title bar",
        source=LabelSource.VISION,
    )


def _day() -> DayLabel:
    return DayLabel(
        image_id="2e92a62eecc3",
        date=datetime.date(2022, 7, 29),
        day_type=DayType.SPIKE_AND_CHANNEL_BULL,
        day_type_confidence=0.85,
        session_summary="Spike and channel bull trend.",
        events=[_event()],
        extraction_meta=_meta(),
    )


def test_chart_time_valid_and_default_tz() -> None:
    assert ChartTime(time="06:30").tz == "America/Los_Angeles"
    assert ChartTime(time="13:00", tz="UTC").time == "13:00"


@pytest.mark.parametrize("bad", ["6:30", "24:00", "12:60", "noon", "", "12:5"])
def test_chart_time_rejects_bad_format(bad: str) -> None:
    with pytest.raises(ValidationError):
        ChartTime(time=bad)


def test_event_unmapped_requires_raw_label() -> None:
    assert EventLabel(label=None, raw_label="Second Entry").label is None
    with pytest.raises(ValidationError):
        EventLabel(label=None, raw_label="   ")


def test_event_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        EventLabel(label=EventKind.SPIKE, confidence=1.5)
    with pytest.raises(ValidationError):
        EventLabel(label=EventKind.SPIKE, confidence=-0.1)


def test_day_label_round_trip() -> None:
    restored = DayLabel.model_validate_json(_day().model_dump_json())
    assert restored == _day()


def test_day_label_rejects_too_many_events() -> None:
    with pytest.raises(ValidationError):
        DayLabel(
            image_id="x",
            date=datetime.date(2022, 7, 29),
            extraction_meta=_meta(),
            events=[_event() for _ in range(201)],
        )


def test_migrate_passthrough_and_legacy() -> None:
    current = _day().model_dump(mode="json")
    assert migrate_day_label(current) == current
    legacy = {
        "imageId": "abc",
        "dayType": "trading_range",
        "dayTypeConfidence": 0.6,
        "sessionSummary": "chop",
        "extractionMeta": {"provider": "file", "model_id": "m", "prompt_version": "v"},
    }
    migrated = migrate_day_label(legacy)
    assert migrated["schema_version"] == 1
    assert migrated["day_type"] == "trading_range"
    validated = DayLabel(
        image_id=migrated["image_id"],
        date=datetime.date(2022, 8, 2),
        day_type=migrated["day_type"],
        extraction_meta=migrated["extraction_meta"],
    )
    assert validated.day_type is DayType.TRADING_RANGE


def test_migrate_rejects_future_version() -> None:
    with pytest.raises(ValueError):
        migrate_day_label({"schema_version": 99})
