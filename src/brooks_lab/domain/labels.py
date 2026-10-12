"""Domain models for Phase 2: validated chart labels.

A ``DayLabel`` is the structured reading of one EOD chart image; ``EventLabel``
is a single annotated pattern/event on that day. Unknown annotator wording is
never dropped: it lands in ``raw_label`` with ``label=None`` for the review queue.
"""

from __future__ import annotations

import datetime
import re
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LABEL_SCHEMA_VERSION = 1

#: Timezone of the chart axis on Brooks EOD charts (US Pacific; see ADR-004).
AXIS_TIMEZONE = "America/Los_Angeles"

_WHITESPACE_RE = re.compile(r"[\s\-_]+")


def normalise_wording(raw: str) -> str:
    """Normalise annotator wording for lookup (lowercase, single spaces)."""
    return _WHITESPACE_RE.sub(" ", raw.strip().lower()).strip()


class DayType(StrEnum):
    """Canonical day-type vocabulary (taxonomy v1)."""

    BULL_TREND_FROM_OPEN = "bull_trend_from_open"
    BEAR_TREND_FROM_OPEN = "bear_trend_from_open"
    SPIKE_AND_CHANNEL_BULL = "spike_and_channel_bull"
    SPIKE_AND_CHANNEL_BEAR = "spike_and_channel_bear"
    SMALL_PULLBACK_BULL_TREND = "small_pullback_bull_trend"
    SMALL_PULLBACK_BEAR_TREND = "small_pullback_bear_trend"
    TRENDING_TRADING_RANGE = "trending_trading_range"
    TRADING_RANGE = "trading_range"
    BROAD_BULL_CHANNEL = "broad_bull_channel"
    BROAD_BEAR_CHANNEL = "broad_bear_channel"
    REVERSAL_DAY = "reversal_day"
    TREND_REVERSAL_TO_BULL = "trend_reversal_to_bull"
    TREND_REVERSAL_TO_BEAR = "trend_reversal_to_bear"
    OTHER = "other"


class EventKind(StrEnum):
    """Canonical event/pattern vocabulary (taxonomy v1)."""

    SPIKE = "spike"
    CHANNEL = "channel"
    BUY_THE_CLOSE = "buy_the_close"
    SELL_THE_CLOSE = "sell_the_close"
    BREAKOUT = "breakout"
    FAILED_BREAKOUT = "failed_breakout"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    WEDGE = "wedge"
    TRUNCATED_WEDGE = "truncated_wedge"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    LOWER_HIGH_DOUBLE_TOP = "lower_high_double_top"
    HIGHER_LOW_DOUBLE_BOTTOM = "higher_low_double_bottom"
    MICRO_DOUBLE_TOP = "micro_double_top"
    MICRO_DOUBLE_BOTTOM = "micro_double_bottom"
    MEASURED_MOVE = "measured_move"
    PULLBACK_50PCT = "pullback_50pct"
    H1 = "h1"
    H2 = "h2"
    L1 = "l1"
    L2 = "l2"
    MAJOR_BULL_SURPRISE = "major_bull_surprise"
    MAJOR_BEAR_SURPRISE = "major_bear_surprise"
    TREND_LINE_BREAK = "trend_line_break"
    CHANNEL_LINE_OVERSHOOT = "channel_line_overshoot"
    BODY_GAP = "body_gap"
    GAP = "gap"
    EMA_GAP_BAR = "ema_gap_bar"
    CLIMAX = "climax"
    EXHAUSTIVE_CLIMAX = "exhaustive_climax"
    FINAL_FLAG = "final_flag"
    OPENING_REVERSAL = "opening_reversal"
    TRADING_RANGE_BEGIN = "trading_range_begin"
    TRADING_RANGE_END = "trading_range_end"
    SIGNAL_BAR = "signal_bar"
    ENTRY_BAR = "entry_bar"
    FAILED_SIGNAL = "failed_signal"


class Outcome(StrEnum):
    """What happened after the event (hindsight, from the annotation)."""

    SUCCESS = "success"
    FAIL = "fail"
    PARTIAL = "partial"
    UNCLEAR = "unclear"


class Direction(StrEnum):
    """Direction of the event."""

    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class LabelSource(StrEnum):
    """Who produced the label."""

    VISION = "vision"
    HUMAN = "human"
    ENGINE = "engine"


class ChartTime(BaseModel):
    """A clock time as read from the chart axis (HH:MM plus timezone)."""

    model_config = ConfigDict(frozen=True)

    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    tz: str = Field(default=AXIS_TIMEZONE, min_length=1)


class ExtractionMeta(BaseModel):
    """Provenance of one extraction (which provider/model/prompt produced it)."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    extracted_at: datetime.datetime | None = None


class EventLabel(BaseModel):
    """One annotated pattern/event on a chart."""

    model_config = ConfigDict(frozen=True)

    label: EventKind | None = Field(
        default=None,
        description="Canonical label; None means unmapped (see raw_label + review queue).",
    )
    raw_label: str = Field(default="", description="Verbatim annotator wording; never dropped.")
    direction: Direction = Direction.NEUTRAL
    start_time: ChartTime | None = None
    end_time: ChartTime | None = None
    bar_index_hint: int | None = Field(default=None, ge=0)
    price_hint: float | None = None
    outcome: Outcome = Outcome.UNCLEAR
    outcome_reason: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str = Field(
        default="", description="What text/graphic on the image supports this event."
    )
    source: LabelSource = LabelSource.VISION

    @model_validator(mode="after")
    def _unmapped_needs_raw_label(self) -> Self:
        if self.label is None and not self.raw_label.strip():
            raise ValueError("unmapped events (label=None) must keep a raw_label")
        return self


class DayLabel(BaseModel):
    """Structured, validated reading of one full trading-day chart image."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=LABEL_SCHEMA_VERSION, ge=1)
    image_id: str = Field(min_length=1)
    date: datetime.date
    day_type: DayType = DayType.OTHER
    day_type_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    session_summary: str = ""
    events: list[EventLabel] = Field(default_factory=list)
    extraction_meta: ExtractionMeta

    @field_validator("events")
    @classmethod
    def _events_bounded(cls, events: list[EventLabel]) -> list[EventLabel]:
        if len(events) > 200:
            raise ValueError("day labels carry at most 200 events")
        return events


def migrate_day_label(payload: dict[str, Any]) -> dict[str, Any]:
    """Migrate a raw label dict toward the current schema (stub, v0 -> v1).

    Handles the documented pre-v1 shape (camelCase keys, no schema_version);
    passes v1 payloads through untouched; raises on newer unknown versions.
    """
    version = payload.get("schema_version", 0)
    if version == LABEL_SCHEMA_VERSION:
        return dict(payload)
    if isinstance(version, int) and version > LABEL_SCHEMA_VERSION:
        raise ValueError(f"unsupported label schema_version: {version}")
    renamed = {
        "dayType": "day_type",
        "dayTypeConfidence": "day_type_confidence",
        "sessionSummary": "session_summary",
        "extractionMeta": "extraction_meta",
        "imageId": "image_id",
        "rawLabel": "raw_label",
        "startTime": "start_time",
        "endTime": "end_time",
    }
    migrated: dict[str, Any] = {"schema_version": LABEL_SCHEMA_VERSION}
    for key, value in payload.items():
        if key == "schema_version":
            continue
        migrated[renamed.get(key, key)] = value
    return migrated
