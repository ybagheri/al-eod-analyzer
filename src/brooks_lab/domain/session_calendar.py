"""US cash-session calendar for M5 bars (S3, Phase 5b).

Regular session: 09:30-16:00 America/New_York (brooks EOD charts show the
Pacific-time equivalent 06:30-13:00 PT). Half days close at 13:00 ET.
DST transitions use the US rule (second Sunday in March -> first Sunday in
November, 02:00 local) so the calendar stays deterministic without relying on
the system tzdata package.

All public timestamps are returned as aware ``datetime`` in ET (America/New_York)
plus a UTC companion, so the layer never mixes server time with exchange time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = UTC

REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
HALF_DAY_CLOSE = time(13, 0)
BAR_INTERVAL_MINUTES = 5

# US DST rule: second Sunday in March at 02:00 local -> first Sunday in
# November at 02:00 local.
DST_START_MONTH = 3
DST_END_MONTH = 11


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Date of the n-th occurrence of ``weekday`` (Mon=0..Sun=6) in ``month``."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _dst_transition(year: int, month: int) -> date:
    """Local date of the DST transition in ``month`` (2:00 local time)."""
    if month == DST_START_MONTH:
        return _nth_weekday(year, month, 6, 2)  # second Sunday
    return _nth_weekday(year, month, 6, 1)  # first Sunday


def _is_dst(day: date) -> bool:
    if day.month < DST_START_MONTH or day.month > DST_END_MONTH:
        return False
    if DST_START_MONTH < day.month < DST_END_MONTH:
        return True
    transition = _dst_transition(day.year, day.month)
    if day.month == DST_START_MONTH:
        return day >= transition
    return day < transition


def _utcoffset_for(day: date) -> timedelta:
    return timedelta(hours=-4) if _is_dst(day) else timedelta(hours=-5)


@dataclass(frozen=True)
class SessionBar:
    """One M5 bar inside a session.

    ``bar_index`` is 0-based from the session open.
    """

    bar_index: int
    timestamp_et: datetime  # aware, America/New_York
    timestamp_utc: datetime  # aware, UTC


@dataclass(frozen=True)
class SessionDay:
    """Describes one session day."""

    date: date
    kind: str  # "regular" | "half" | "closed"
    open_et: datetime
    close_et: datetime
    bars: tuple[SessionBar, ...]

    @property
    def n_bars(self) -> int:
        return len(self.bars)


class SessionCalendar:
    """US cash-session calendar with DST and holiday handling."""

    def __init__(
        self,
        holidays_full: set[date] | None = None,
        holidays_half: set[date] | None = None,
    ) -> None:
        self.holidays_full = set(holidays_full or set())
        self.holidays_half = set(holidays_half or set())

    # -- holiday helpers -------------------------------------------------

    def is_trading_day(self, day: date) -> bool:
        if day.weekday() >= 5:
            return False
        return day not in self.holidays_full

    def is_half_day(self, day: date) -> bool:
        return day in self.holidays_half

    def session_kind(self, day: date) -> str:
        if not self.is_trading_day(day):
            return "closed"
        return "half" if self.is_half_day(day) else "regular"

    # -- session bounds --------------------------------------------------

    def session_open_et(self, day: date) -> datetime:
        return datetime.combine(day, REGULAR_OPEN, tzinfo=timezone(_utcoffset_for(day)))

    def session_close_et(self, day: date) -> datetime:
        close = HALF_DAY_CLOSE if self.is_half_day(day) else REGULAR_CLOSE
        return datetime.combine(day, close, tzinfo=timezone(_utcoffset_for(day)))

    # -- bar indexing ----------------------------------------------------

    def bar_count(self, day: date) -> int:
        kind = self.session_kind(day)
        if kind == "closed":
            return 0
        close = HALF_DAY_CLOSE if kind == "half" else REGULAR_CLOSE
        minutes = int((close.hour - REGULAR_OPEN.hour) * 60 + (close.minute - REGULAR_OPEN.minute))
        return minutes // BAR_INTERVAL_MINUTES

    def session_bars(self, day: date) -> SessionDay:
        """Return all M5 bars for ``day`` with 0-based ``bar_index`` from open."""
        kind = self.session_kind(day)
        if kind == "closed":
            return SessionDay(day, kind, self.session_open_et(day), self.session_close_et(day), ())
        close_et = self.session_close_et(day)
        open_et = self.session_open_et(day)
        bars: list[SessionBar] = []
        bar = open_et
        index = 0
        while bar < close_et:
            bars.append(
                SessionBar(
                    bar_index=index,
                    timestamp_et=bar,
                    timestamp_utc=bar.astimezone(UTC),
                )
            )
            bar += timedelta(minutes=BAR_INTERVAL_MINUTES)
            index += 1
        return SessionDay(day, kind, open_et, self.session_close_et(day), tuple(bars))

    def timestamp_for_bar_index(self, day: date, bar_index: int) -> datetime | None:
        """ET timestamp of the bar with 0-based ``bar_index`` (or None)."""
        session = self.session_bars(day)
        if 0 <= bar_index < len(session.bars):
            return session.bars[bar_index].timestamp_et
        return None

    def bar_index_for_timestamp(self, day: date, stamp_et: datetime) -> int | None:
        """0-based bar index for an ET timestamp falling exactly on a bar boundary."""
        session = self.session_bars(day)
        for bar in session.bars:
            if bar.timestamp_et == stamp_et:
                return bar.bar_index
        return None

    def next_trading_day(self, day: date) -> date:
        candidate = day + timedelta(days=1)
        while not self.is_trading_day(candidate):
            candidate += timedelta(days=1)
        return candidate
