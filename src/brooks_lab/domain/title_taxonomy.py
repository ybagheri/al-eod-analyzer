"""Map batch image-file titles (part of the filename) to taxonomy ids.

Batch-1 filenames follow ``SP500-Emini-M5-<Title>_YYYY_MM_DD.jpg`` where
``<Title>`` is the source author's hand-written day reading. The title is a
provisional ``human`` signal: ``map_title`` returns the closest canonical
DayType plus all recognised EventKinds so review can compare extraction
against a free coverage hint (ADR-010).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from brooks_lab.domain.labels import DayType, EventKind

_FILENAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:SP500-Emini-M5-|SP500-E-mini-M5-|SP500-E-mini-)"
    r"(?P<title>.+?)(?:_(?P<date>\d{4}_\d{2}_\d{2}))?\.(?:jpg|jpeg|png)$",
    re.IGNORECASE,
)

_DAY_RULES: Final[tuple[tuple[str, DayType], ...]] = (
    (r"bull-trend-resumption|resumption-up-(after|toward)", DayType.BULL_TREND_RESUMPTION),
    (r"(?:bear-trend|trend)-resumption", DayType.BEAR_TREND_FROM_OPEN),
    (
        r"spike-?and-?channel-bull|bull-spike-and-channel|spike-channel-bull",
        DayType.SPIKE_AND_CHANNEL_BULL,
    ),
    (
        r"spike-?and-?channel-bear|bear-spike-and-channel|spike-channel-bear",
        DayType.SPIKE_AND_CHANNEL_BEAR,
    ),
    (
        r"small-?-?p?b?-?-?bull-trend|small-pullback-bull-trend",
        DayType.SMALL_PULLBACK_BULL_TREND,
    ),
    (
        r"small-?-?p?b?-?-?bear-trend|small-pullback-bear-trend",
        DayType.SMALL_PULLBACK_BEAR_TREND,
    ),
    (r"bull-trend-from-?(?:the-)?open", DayType.BULL_TREND_FROM_OPEN),
    (r"bear-trend-from-?(?:the-)?open", DayType.BEAR_TREND_FROM_OPEN),
    (r"broad-bull-channel", DayType.BROAD_BULL_CHANNEL),
    (r"broad-bear-channel", DayType.BROAD_BEAR_CHANNEL),
    (r"bull-channel", DayType.BROAD_BULL_CHANNEL),
    (r"bear-channel|bear-channnel|baer-channel", DayType.BROAD_BEAR_CHANNEL),
    (r"trending-trading-range", DayType.TRENDING_TRADING_RANGE),
    (r"bull-trend(?:-day)?$", DayType.BULL_TREND_FROM_OPEN),
    (r"bull-trend(?:-day)?-|-and-bull-trend", DayType.BULL_TREND_FROM_OPEN),
    (
        r"bear-trend(?:-day)?$|-in-bear-trend$|-into-bear-trend$",
        DayType.BEAR_TREND_FROM_OPEN,
    ),
    (
        r"trading-range-day|trading-range-open|trading-range$|trading-range-"
        r"|tr-?-day|tight-trading-range|trading-range-?-?-?-?-?-?-?-",
        DayType.TRADING_RANGE,
    ),
    (r"reversal-up", DayType.TREND_REVERSAL_TO_BULL),
    (r"reversal-down", DayType.TREND_REVERSAL_TO_BEAR),
    (r"outside-up", DayType.TREND_REVERSAL_TO_BULL),
    (r"outside-down", DayType.TREND_REVERSAL_TO_BEAR),
    (r"doji", DayType.TRADING_RANGE),
    (r"inside-day", DayType.TRADING_RANGE),
    (r"reversal$", DayType.REVERSAL_DAY),
)

_EVENT_RULES: Final[tuple[tuple[str, EventKind], ...]] = (
    (r"buy-climax", EventKind.CLIMAX),
    (r"sell-climax", EventKind.CLIMAX),
    (r"exhaustive", EventKind.EXHAUSTIVE_CLIMAX),
    (r"buy-the-close", EventKind.BUY_THE_CLOSE),
    (r"sell-the-close", EventKind.SELL_THE_CLOSE),
    (r"breakout-(?:mode|above|below)", EventKind.BREAKOUT),
    (r"failed-breakout|failed-bull-breakout|failed-bear-breakout", EventKind.FAILED_BREAKOUT),
    (r"breakout$", EventKind.BREAKOUT),
    (r"wedge-top|wedge-bottom|nested-wedge|parabolic-wedge", EventKind.WEDGE),
    (r"truncated-wedge", EventKind.TRUNCATED_WEDGE),
    (r"double-top|hh-?-dt|-dt-", EventKind.DOUBLE_TOP),
    (r"lower-high-?-double-top|lh-?-dt", EventKind.LOWER_HIGH_DOUBLE_TOP),
    (r"higher-low-?-double-bottom|hl-?-db", EventKind.HIGHER_LOW_DOUBLE_BOTTOM),
    (r"lower-low-?-double-bottom|ll-?-db", EventKind.LOWER_LOW_DOUBLE_BOTTOM),
    (r"-db-|-2nd-?-db-|-2nd-?-db$|double-bottom", EventKind.DOUBLE_BOTTOM),
    (r"micro-double-top", EventKind.MICRO_DOUBLE_TOP),
    (r"micro-double-bottom", EventKind.MICRO_DOUBLE_BOTTOM),
    (r"micro-wedge", EventKind.WEDGE),
    (r"measured-move|-mm-|-mm$|-mm-", EventKind.MEASURED_MOVE),
    (r"50-?pc-|50-percent-pullback|50-?-pullback", EventKind.PULLBACK_50PCT),
    (r"gap-up|gap-down|-gap-", EventKind.GAP),
    (r"ema-gap-bar|body-gap", EventKind.BODY_GAP),
    (r"ema-gap-bar", EventKind.EMA_GAP_BAR),
    (r"high-2-", EventKind.H2),
    (r"high-1-", EventKind.H1),
    (r"low-2-", EventKind.L2),
    (r"low-1-", EventKind.L1),
    (r"low-4-", EventKind.LOW_4),
    (r"opening-reversal", EventKind.OPENING_REVERSAL),
    (r"midday-reversal|middle-bull-trend-reversal", EventKind.MIDDAY_REVERSAL),
    (r"bull-flag|final-bull-flag|wedge-bull-flag", EventKind.BULL_FLAG),
    (r"bear-flag|wedge-bear-flag|final-bear-flag", EventKind.BEAR_FLAG),
    (r"final-flag|-ii-|-ii$|inside-inside", EventKind.INSIDE_INSIDE),
    (r"-oo-|-oo$|outside-up-day-after-?-outside-down", EventKind.OUTSIDE_OUTSIDE),
    (r"triangle", EventKind.TRIANGLE),
    (r"major-bull-surprise", EventKind.MAJOR_BULL_SURPRISE),
    (r"major-bear-surprise|bear-surprise", EventKind.MAJOR_BEAR_SURPRISE),
    (r"major-trend-reversal|--MTR-|-MTR-|-MTR$|-MTR-?-|-LH-?-MTR", EventKind.MAJOR_TREND_REVERSAL),
    (r"trend-line-break", EventKind.TREND_LINE_BREAK),
    (r"head-and-shoulders-top", EventKind.HEAD_AND_SHOULDERS_TOP),
    (r"vacuum", EventKind.BREAKOUT),
)


@dataclass(frozen=True, slots=True)
class TitleMatch:
    """Canonical mapping result for one image filename title."""

    title: str
    date: str | None
    day_type: DayType | None
    events: tuple[EventKind, ...]


def parse_filename(filename: str) -> tuple[str, str | None]:
    """Return ``(title, date)`` parsed from a batch-1 filename.

    Raises ``ValueError`` when the filename does not follow the batch layout.
    """
    match = _FILENAME_RE.match(filename)
    if match is None:
        raise ValueError(f"unrecognised batch filename layout: {filename}")
    return match.group("title"), match.group("date")


def map_title(title: str) -> TitleMatch:
    """Map a raw title to the closest canonical day type plus event ids."""
    lowered = title.lower().replace("_", "-")
    if lowered.startswith("chart-"):
        lowered = lowered[len("chart-") :]
    day_type: DayType | None = None
    matched_events: list[EventKind] = []
    for pattern, kind in _EVENT_RULES:
        if re.search(pattern, lowered) and kind not in matched_events:
            matched_events.append(kind)
    for pattern, candidate in _DAY_RULES:
        if re.search(pattern, lowered):
            day_type = candidate
            break
    return TitleMatch(
        title=title,
        date=None,
        day_type=day_type,
        events=tuple(matched_events),
    )
