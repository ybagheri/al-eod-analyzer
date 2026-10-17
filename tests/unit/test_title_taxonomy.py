"""Unit tests for filename-title to taxonomy mapping (ADR-010)."""

import pytest

from brooks_lab.domain.labels import DayType, EventKind
from brooks_lab.domain.title_taxonomy import map_title, parse_filename


@pytest.mark.parametrize(
    "filename",
    [
        "SP500-Emini-M5-Bull-Trend-From-The-Open_2023_06_15.jpg",
        "SP500-E-mini-Bear-Channel-and-Trend-Continuation_2026_03_13.png",
        "SP500-Emini-M5-nested-wedge-and-double-top-in-trading-range.png",
    ],
)
def test_parse_filename_layouts(filename: str) -> None:
    title, date = parse_filename(filename)
    assert title
    assert date is None or len(date) == 10


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bull-Trend-From-The-Open", DayType.BULL_TREND_FROM_OPEN),
        ("Bear-Trend-from-open", DayType.BEAR_TREND_FROM_OPEN),
        ("Small-PB-Bull-Trend", DayType.SMALL_PULLBACK_BULL_TREND),
        ("Small-pullback-bear-trend", DayType.SMALL_PULLBACK_BEAR_TREND),
        ("Spike-and-Channel-Bull-Trend", DayType.SPIKE_AND_CHANNEL_BULL),
        ("Spike-Channel-Bear-Trend-Day", DayType.SPIKE_AND_CHANNEL_BEAR),
        ("Broad-Bear-Channel", DayType.BROAD_BEAR_CHANNEL),
        ("bear-channel-and-then-trading-range", DayType.BROAD_BEAR_CHANNEL),
        ("Trending-Trading-Range-Day", DayType.TRENDING_TRADING_RANGE),
        ("Trading-Range-Day", DayType.TRADING_RANGE),
        ("doji-trading-range-day", DayType.TRADING_RANGE),
        ("Bull-Trend-Resumption-50PC-Pullback", DayType.BULL_TREND_RESUMPTION),
        ("bear-trend-resumption", DayType.BEAR_TREND_FROM_OPEN),
        ("reversal-up-from-sell-climax", DayType.TREND_REVERSAL_TO_BULL),
        ("outside-down-sell-climax-day", DayType.TREND_REVERSAL_TO_BEAR),
        ("Chart-Bull-Trend-From-Open-and-Then-Late-Reversal", DayType.BULL_TREND_FROM_OPEN),
        ("Bull-Trap-Then-Breakout-and-Channel-Bear-Trend-Day", DayType.BEAR_TREND_FROM_OPEN),
        ("Bear-Spike-and-Channel-to-Midday-Reversal", DayType.SPIKE_AND_CHANNEL_BEAR),
        ("Bull-Spike-from-Open-Bull-Channel", DayType.BROAD_BULL_CHANNEL),
    ],
)
def test_map_title_day_types(title: str, expected: DayType) -> None:
    assert map_title(title).day_type == expected


@pytest.mark.parametrize(
    ("title", "expected_member"),
    [
        ("Buy-Climax-Double-Top", EventKind.CLIMAX),
        ("Sell-Climax-and-Then-Bear-Channel", EventKind.CLIMAX),
        ("wedge-top-and-then-wedge-bottom", EventKind.WEDGE),
        ("HL-DB-Then-Parabolic-Wedge-Top", EventKind.HIGHER_LOW_DOUBLE_BOTTOM),
        ("LL-DB-Then-Bull-Trend", EventKind.LOWER_LOW_DOUBLE_BOTTOM),
        ("LH-DT-MTR-in-Trending-TR-Day", EventKind.LOWER_HIGH_DOUBLE_TOP),
        ("High-2-Then-Bull-Trend-From-Open", EventKind.H2),
        ("Low-2-Top-Then-Wedge-Bottom", EventKind.L2),
        ("trending-trading-range-day-with-Low-4-top", EventKind.LOW_4),
        ("Bull-Trend-Resumption-50PC-Pullback", EventKind.PULLBACK_50PCT),
        ("Gap-Down-Sell-Climax-Then-TR", EventKind.CLIMAX),
    ],
)
def test_map_title_events(title: str, expected_member: EventKind) -> None:
    assert expected_member in map_title(title).events


def test_map_title_events_are_deduplicated_in_order() -> None:
    match = map_title("Buy-Climax-Bear-Channel-Then-Midday-Reversal")
    assert match.events == (EventKind.CLIMAX, EventKind.MIDDAY_REVERSAL)


def test_map_title_keeps_title_verbatim() -> None:
    match = map_title("Wedge-Top-Then-Big-Round-Number")
    assert match.title == "Wedge-Top-Then-Big-Round-Number"
