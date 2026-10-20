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

# Separators collapsed by normalise_wording (v1.1 also strips dots/parens).
_WHITESPACE_RE = re.compile(r"[\s\-_.,()]+")


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
    # v1.3 (ADR-011): trending TR split by direction (user review decision).
    BULL_TRENDING_TRADING_RANGE = "bull_trending_trading_range"
    BEAR_TRENDING_TRADING_RANGE = "bear_trending_trading_range"
    TRADING_RANGE = "trading_range"
    # v1.3 (ADR-011): compound days - range that resolves via a breakout.
    TRADING_RANGE_BULL_BREAKOUT = "trading_range_bull_breakout"
    TRADING_RANGE_BEAR_BREAKOUT = "trading_range_bear_breakout"
    BROAD_BULL_CHANNEL = "broad_bull_channel"
    BROAD_BEAR_CHANNEL = "broad_bear_channel"
    # ADR-013 (R-FINISH 8b): bare bull_channel re-admitted as its own day type;
    # width (broad/tight/unspecified) is resolved by on-chart qualifier, else a
    # width_unspecified modifier + review.
    BULL_CHANNEL = "bull_channel"
    # v1.3 (ADR-011): reversal_day REMOVED - use direction-specific ids below.
    TREND_REVERSAL_TO_BULL = "trend_reversal_to_bull"
    TREND_REVERSAL_TO_BEAR = "trend_reversal_to_bear"
    OTHER = "other"
    # Round-3 review addition (ADR-009): TR open -> breakout -> resumption regime.
    BULL_TREND_RESUMPTION = "bull_trend_resumption"


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
    # Taxonomy v1.1 additions (user-approved Brooks patterns, see ADR-006).
    OUTSIDE_OUTSIDE = "outside_outside"
    INSIDE_INSIDE = "inside_inside"
    TRIANGLE = "triangle"
    TIGHT_TRADING_RANGE = "tight_trading_range"
    HEAD_AND_SHOULDERS_TOP = "head_and_shoulders_top"
    MAJOR_TREND_REVERSAL = "major_trend_reversal"
    LOWER_LOW_DOUBLE_BOTTOM = "lower_low_double_bottom"
    MIDDAY_REVERSAL = "midday_reversal"
    # Round-2 review additions (ADR-008): bare surprise (no "major" on chart)
    # and bare trend lines are their own canonical ids.
    BEAR_SURPRISE = "bear_surprise"
    TREND_LINE = "trend_line"
    # Round-3 review additions (ADR-009): fourth-entry signal and the
    # measuring gap (breakout gap projecting the next leg).
    LOW_4 = "low_4"
    MEASURING_GAP = "measuring_gap"


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


class SessionStartSource(StrEnum):
    """Evidence source for ``starts_at_session_open`` (ADR-013)."""

    TITLE = "title"
    NOTE = "note"
    MARKER = "marker"
    NONE = "none"


class NeedsReviewReason(StrEnum):
    """Enumerated reason a migrated/unmapped row needs human review (ADR-013)."""

    LOSSY_MIGRATION = "lossy_migration"
    UNKNOWN_ID = "unknown_id"
    MISSING_EVIDENCE = "missing_evidence"
    AMBIGUOUS_BOUNDARY = "ambiguous_boundary"
    AMBIGUOUS_DIRECTION = "ambiguous_direction"
    DIRECTION_MISSING = "direction_missing"
    REGIME_DIRECTION_MISSING = "regime_direction_missing"
    DAY_TYPE_USED_AS_EVENT = "day_type_used_as_event"
    WIDTH_UNSPECIFIED = "width_unspecified"
    ALTERNATIVE_MAPPING = "alternative_mapping"


class EventRole(StrEnum):
    """What the event row IS (reviewer `kind` axis, see ADR-007/ADR-008)."""

    PATTERN = "pattern"
    ENTRY_SIGNAL = "entry_signal"
    EXPECTATION = "expectation"
    DAY_PART = "day_part"
    STRUCTURE = "structure"
    EXIT_SIGNAL = "exit_signal"
    DAY_PHASE = "day_phase"
    CONTEXT = "context"
    ADVICE = "advice"
    BAR_PATTERN = "bar_pattern"


class ChartTime(BaseModel):
    """A clock time as read from the chart axis (HH:MM plus timezone)."""

    model_config = ConfigDict(frozen=True)

    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    tz: str = Field(default=AXIS_TIMEZONE, min_length=1)


class AxisStyle(StrEnum):
    """Chart x-axis style (schema v3; see docs/LABEL_SCHEMA.md)."""

    PT_0630_1300 = "pt_0630_1300"
    ET_STYLE_0900_1500 = "et_style_0900_1500"
    OTHER = "other"
    NONE = "none"


class OpenDir(StrEnum):
    """Direction of the first hour (anchor, schema v3)."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class CloseVsOpen(StrEnum):
    """Day close versus open (anchor, schema v3)."""

    ABOVE = "above"
    BELOW = "below"
    NEAR = "near"


class AxisInfo(BaseModel):
    """What the x-axis shows (schema v3, optional on legacy labels)."""

    model_config = ConfigDict(frozen=True)

    style: AxisStyle = AxisStyle.OTHER
    first_label: str = ""
    last_label: str = ""


class Anchors(BaseModel):
    """Cheap objective anchors used to validate date/time against real bars."""

    model_config = ConfigDict(frozen=True)

    open_dir_first_hour: OpenDir = OpenDir.FLAT
    day_close_vs_open: CloseVsOpen = CloseVsOpen.NEAR
    high_of_day_bar_index_hint: int | None = Field(default=None, ge=0)
    low_of_day_bar_index_hint: int | None = Field(default=None, ge=0)
    n_bars_visible: int | None = Field(default=None, ge=0)


class ExtractionMeta(BaseModel):
    """Provenance of one extraction (which provider/model/prompt produced it)."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    taxonomy_version: str = Field(
        default="", description="Vocabulary version (e.g. 1.3); empty = legacy unstamped."
    )
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
    label_explicit: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reviewer axis 1: is the pattern named by on-chart text? Null = not scored.",
    )
    placement: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reviewer axis 2: how certain is the position (lines/boxes/bars)?",
    )
    modifiers: list[str] = Field(
        default_factory=list,
        description="Reviewer modifier system: HH/LH/HL/LL, minor, at_ema, 2nd_leg, ...",
    )
    role: EventRole = Field(
        default=EventRole.PATTERN, description="Reviewer `kind` axis (default pattern)."
    )
    x_px: list[int] | None = Field(
        default=None,
        description="Pixel span [start, end] for axis-less images; null when unused.",
    )
    end_bar_index_hint: int | None = Field(
        default=None,
        ge=0,
        description="Optional end bar index (schema v3 compound events).",
    )
    needs_review: bool = Field(
        default=False,
        description="True when a lossy migration or unmapped id requires human review.",
    )
    mapped_from: str | None = Field(
        default=None,
        description="Legacy id this row was read from during migration (ADR-013).",
    )
    rule_id: str | None = Field(
        default=None,
        description="Migration-table rule id applied to this row (ADR-013).",
    )
    linked_to: str | None = Field(
        default=None,
        description="Opaque id of a linked counterpart row (e.g. spike<->channel split).",
    )
    needs_review_reason: NeedsReviewReason | None = Field(
        default=None,
        description="Enumerated review reason; null when needs_review is False.",
    )
    evidence: str = Field(
        default="", description="What text/graphic on THIS image supports this event."
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
    date: datetime.date | None = Field(
        default=None,
        description="Trading date; null when the image shows no verifiable date.",
    )
    day_type: DayType = DayType.OTHER
    day_type_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    session_summary: str = ""
    scope_ok: bool | None = Field(
        default=None,
        description="P11 scope filter: True/False from v3 responses; None = legacy label.",
    )
    scope_note: str = ""
    axis: AxisInfo | None = None
    anchors: Anchors | None = None
    needs_review: bool = Field(
        default=False,
        description="True when a lossy day_type migration requires human review.",
    )
    mapped_from: str | None = Field(
        default=None,
        description="Legacy id this day-type was read from during migration (ADR-013).",
    )
    rule_id: str | None = Field(
        default=None,
        description="Migration-table rule id applied to this day (ADR-013).",
    )
    needs_review_reason: NeedsReviewReason | None = Field(
        default=None,
        description="Enumerated review reason; null when needs_review is False.",
    )
    starts_at_session_open: bool | None = Field(
        default=None,
        description="True/False from title/note/marker evidence; None = unknown (ADR-013).",
    )
    starts_at_session_open_source: SessionStartSource | None = Field(
        default=None,
        description="Evidence source for starts_at_session_open (title|note|marker|none).",
    )
    modifiers: list[str] = Field(
        default_factory=list,
        description="Day-level modifiers (e.g. width qualifiers); see ADR-013.",
    )
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
