"""Tests for src/brooks_lab/domain/session_calendar.py (S3, Phase 5b)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from brooks_lab.domain.session_calendar import (
    REGULAR_CLOSE,
    REGULAR_OPEN,
    UTC,
    SessionBar,
    SessionCalendar,
    SessionDay,
    _utcoffset_for,
)


def regular_calendar() -> SessionCalendar:
    return SessionCalendar(
        holidays_full={
            date(2026, 1, 1),  # New Year's Day
            date(2026, 1, 19),  # MLK Day
            date(2026, 5, 25),  # Memorial Day
            date(2026, 7, 3),  # Independence Day observed
            date(2026, 9, 7),  # Labor Day
            date(2026, 11, 26),  # Thanksgiving
            date(2026, 12, 25),  # Christmas
        },
        holidays_half={date(2026, 11, 27)},  # day after Thanksgiving
    )


def test_regular_session_bar_count_and_bounds() -> None:
    cal = regular_calendar()
    day = date(2026, 10, 19)  # Monday, in DST (UTC-4)
    session = cal.session_bars(day)
    assert session.kind == "regular"
    assert session.n_bars == 78
    assert session.bars[0].bar_index == 0
    assert session.bars[0].timestamp_et == datetime(
        2026, 10, 19, 9, 30, tzinfo=timezone(timedelta(hours=-4))
    )
    assert session.bars[0].timestamp_utc == datetime(2026, 10, 19, 13, 30, tzinfo=UTC)
    assert session.bars[77].bar_index == 77
    assert session.bars[77].timestamp_et == datetime(
        2026, 10, 19, 15, 55, tzinfo=timezone(timedelta(hours=-4))
    )
    assert session.open_et.hour == REGULAR_OPEN.hour
    assert session.open_et.minute == REGULAR_OPEN.minute
    assert session.close_et.hour == REGULAR_CLOSE.hour
    assert session.close_et.minute == REGULAR_CLOSE.minute


def test_half_day() -> None:
    cal = regular_calendar()
    day = date(2026, 11, 27)  # Friday after Thanksgiving -> half day
    session = cal.session_bars(day)
    assert session.kind == "half"
    assert session.n_bars == 42  # 09:30 -> 13:00 exclusive => 42 M5 bars
    assert session.bars[0].timestamp_et.hour == 9 and session.bars[0].timestamp_et.minute == 30
    assert session.bars[41].timestamp_et.hour == 12 and session.bars[41].timestamp_et.minute == 55
    assert session.close_et.hour == 13 and session.close_et.minute == 0


def test_weekend_closed() -> None:
    cal = regular_calendar()
    for day in (date(2026, 10, 24), date(2026, 10, 25)):  # Sat, Sun
        session = cal.session_bars(day)
        assert session.kind == "closed"
        assert session.n_bars == 0
        assert session.bars == ()


def test_holiday_closed() -> None:
    cal = regular_calendar()
    session = cal.session_bars(date(2026, 11, 26))  # Thanksgiving
    assert session.kind == "closed"
    assert session.n_bars == 0


def test_dst_spring_forward() -> None:
    cal = regular_calendar()
    # 2026-03-08 is second Sunday -> DST starts; March 2 is before (EST, -5)
    before = cal.session_bars(date(2026, 3, 2))
    assert before.bars[0].timestamp_utc == datetime(2026, 3, 2, 14, 30, tzinfo=UTC)
    assert _utcoffset_for(date(2026, 3, 2)) == timedelta(hours=-5)
    # March 9 is after transition (EDT, -4)
    after = cal.session_bars(date(2026, 3, 9))
    assert after.bars[0].timestamp_utc == datetime(2026, 3, 9, 13, 30, tzinfo=UTC)
    assert _utcoffset_for(date(2026, 3, 9)) == timedelta(hours=-4)


def test_dst_fall_back() -> None:
    cal = regular_calendar()
    # 2026-11-01 is first Sunday -> DST ends; Nov 2 is after (EST, -5)
    after = cal.session_bars(date(2026, 11, 2))
    assert after.bars[0].timestamp_utc == datetime(2026, 11, 2, 14, 30, tzinfo=UTC)
    assert _utcoffset_for(date(2026, 11, 2)) == timedelta(hours=-5)
    # October 19 is still in DST (EDT, -4)
    before = cal.session_bars(date(2026, 10, 19))
    assert before.bars[0].timestamp_utc == datetime(2026, 10, 19, 13, 30, tzinfo=UTC)


def test_bar_index_roundtrip() -> None:
    cal = regular_calendar()
    day = date(2026, 10, 19)
    stamp = cal.timestamp_for_bar_index(day, 10)
    assert stamp == datetime(2026, 10, 19, 10, 20, tzinfo=timezone(timedelta(hours=-4)))
    assert cal.bar_index_for_timestamp(day, stamp) == 10
    assert cal.timestamp_for_bar_index(day, 78) is None
    late_open = datetime(2026, 10, 19, 9, 32, tzinfo=timezone(timedelta(hours=-4)))
    assert cal.bar_index_for_timestamp(day, late_open) is None


def test_next_trading_day_skips_weekend_and_holiday() -> None:
    cal = regular_calendar()
    assert cal.next_trading_day(date(2026, 7, 2)) == date(2026, 7, 6)  # Thu -> Mon (Fri holiday)
    # Friday Jul 3 itself is closed; next trading day after it:
    assert cal.next_trading_day(date(2026, 7, 3)) == date(2026, 7, 6)


def test_session_day_immutability() -> None:
    cal = regular_calendar()
    session = cal.session_bars(date(2026, 10, 19))
    assert isinstance(session, SessionDay)
    assert isinstance(session.bars[0], SessionBar)
