"""Market-bars repository: CSV adapter over MT5-exported M5 bars (S3, Phase 5b).

The engine works on M5 bars with zero look-ahead. This layer is intentionally
stdlib-only (``csv``) so the MQL5 parity story stays honest: pandas/numpy live
only in the optional ``data`` extra and are never imported here.

All timestamps are the broker **server time** as exported from MT5
(``time_server``). Conversion to exchange time (ET/PT) happens later, once the
broker offset rule is derived empirically in ``config/broker_time.yaml``
(CHECKPOINT B).
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol, runtime_checkable

RATES_PATTERN = re.compile(r"^rates_(?P<symbol>.+)_M5\.csv$")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Bar:
    """One M5 bar, broker server time."""

    symbol: str
    timestamp_server: datetime  # naive, as exported
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    real_volume: int
    spread: int


@dataclass(frozen=True)
class SymbolCoverage:
    """Per-symbol coverage summary built from raw CSVs."""

    symbol: str
    file: str
    sha256: str
    n_rows: int
    first_ts: datetime | None
    last_ts: datetime | None
    n_days: int
    n_complete_sessions: int
    missing_weekdays: list[str]
    gaps_over_3_days: list[dict]


@runtime_checkable
class MarketBarsRepository(Protocol):
    """Read-only access to M5 market bars."""

    def symbols(self) -> list[str]: ...
    def bars_for_day(self, symbol: str, day: date) -> list[Bar]: ...
    def first_bar(self, symbol: str) -> Bar | None: ...
    def last_bar(self, symbol: str) -> Bar | None: ...
    def coverage(self, symbol: str) -> SymbolCoverage | None: ...


class CsvMarketBarsRepository:
    """Filesystem-backed repository reading ``data/market/raw/rates_<SYMBOL>_M5.csv``."""

    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self._by_symbol: dict[str, list[Bar]] = {}
        self._loaded = False

    # -- loading -----------------------------------------------------------

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.raw_dir.exists():
            return
        for path in sorted(self.raw_dir.glob("rates_*_M5.csv")):
            match = RATES_PATTERN.match(path.name)
            symbol = match.group("symbol") if match else path.stem
            bars = self._parse_file(path, symbol)
            self._by_symbol[symbol] = bars

    def _parse_file(self, path: Path, symbol: str) -> list[Bar]:
        bars: list[Bar] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    bars.append(
                        Bar(
                            symbol=symbol,
                            timestamp_server=datetime.strptime(
                                row["time_server"].strip(), TIME_FORMAT
                            ),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            tick_volume=int(row["tick_volume"]),
                            real_volume=int(row["real_volume"]),
                            spread=int(row["spread"]),
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue
        return bars

    # -- repository API ----------------------------------------------------

    def symbols(self) -> list[str]:
        self._load()
        return sorted(self._by_symbol.keys())

    def bars_for_day(self, symbol: str, day: date) -> list[Bar]:
        self._load()
        return [b for b in self._by_symbol.get(symbol, []) if b.timestamp_server.date() == day]

    def first_bar(self, symbol: str) -> Bar | None:
        self._load()
        bars = self._by_symbol.get(symbol)
        return bars[0] if bars else None

    def last_bar(self, symbol: str) -> Bar | None:
        self._load()
        bars = self._by_symbol.get(symbol)
        return bars[-1] if bars else None

    def coverage(self, symbol: str) -> SymbolCoverage | None:
        self._load()
        bars = self._by_symbol.get(symbol)
        if not bars:
            return None
        sha = hashlib.sha256()
        for path in self.raw_dir.glob(f"rates_{symbol}_M5.csv"):
            sha.update(path.read_bytes())
        days: dict[date, list[Bar]] = {}
        for bar in bars:
            days.setdefault(bar.timestamp_server.date(), []).append(bar)
        missing: list[str] = []
        gaps: list[dict] = []
        sorted_days = sorted(days)
        for i in range(1, len(sorted_days)):
            prev, curr = sorted_days[i - 1], sorted_days[i]
            delta = (curr - prev).days
            if delta > 1:
                missing.extend((prev + timedelta(days=k)).isoformat() for k in range(1, delta))
            if delta > 3:
                gaps.append(
                    {
                        "from": prev.isoformat(),
                        "to": curr.isoformat(),
                        "calendar_days": delta,
                    }
                )
        return SymbolCoverage(
            symbol=symbol,
            file=f"rates_{symbol}_M5.csv",
            sha256=sha.hexdigest(),
            n_rows=len(bars),
            first_ts=bars[0].timestamp_server,
            last_ts=bars[-1].timestamp_server,
            n_days=len(days),
            n_complete_sessions=0,  # filled by coverage-probe once offset known
            missing_weekdays=missing,
            gaps_over_3_days=gaps,
        )

    def to_manifest_entry(self, symbol: str) -> dict | None:
        cov = self.coverage(symbol)
        if cov is None:
            return None
        return {
            "symbol": cov.symbol,
            "file": cov.file,
            "sha256": cov.sha256,
            "n_rows": cov.n_rows,
            "first_ts": cov.first_ts.isoformat(sep=" ") if cov.first_ts else None,
            "last_ts": cov.last_ts.isoformat(sep=" ") if cov.last_ts else None,
            "n_days": cov.n_days,
            "missing_weekdays": cov.missing_weekdays,
            "gaps_over_3_days": cov.gaps_over_3_days,
        }
