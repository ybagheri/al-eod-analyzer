"""Tests for src/brooks_lab/infrastructure/market_bars.py (S3, Phase 5b)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from brooks_lab.infrastructure.market_bars import (
    Bar,
    CsvMarketBarsRepository,
)

HEADER = "time_server,open,high,low,close,tick_volume,real_volume,spread"


def write_csv(raw_dir: Path, symbol: str, rows: list[str]) -> None:
    (raw_dir / f"rates_{symbol}_M5.csv").write_text(
        HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8"
    )


def test_loads_bars_per_symbol(tmp_path: Path) -> None:
    write_csv(
        tmp_path,
        "US500",
        [
            "2026-10-19 09:30:00,6700.00,6702.00,6699.00,6701.25,1200,5000,30",
            "2026-10-19 09:35:00,6701.25,6703.50,6700.50,6703.00,900,3000,25",
        ],
    )
    repo = CsvMarketBarsRepository(tmp_path)
    assert repo.symbols() == ["US500"]
    bars = repo.bars_for_day("US500", date(2026, 10, 19))
    assert len(bars) == 2
    assert bars[0] == Bar(
        symbol="US500",
        timestamp_server=datetime(2026, 10, 19, 9, 30),
        open=6700.0,
        high=6702.0,
        low=6699.0,
        close=6701.25,
        tick_volume=1200,
        real_volume=5000,
        spread=30,
    )


def test_missing_symbol_returns_empty(tmp_path: Path) -> None:
    repo = CsvMarketBarsRepository(tmp_path)
    assert repo.symbols() == []
    assert repo.bars_for_day("NOPE", date(2026, 10, 19)) == []
    assert repo.first_bar("NOPE") is None
    assert repo.last_bar("NOPE") is None
    assert repo.coverage("NOPE") is None


def test_coverage_gaps_and_missing(tmp_path: Path) -> None:
    write_csv(
        tmp_path,
        "DEMO",
        [
            "2026-10-19 09:30:00,1.0,1.1,0.9,1.0,10,0,1",
            "2026-10-20 09:30:00,1.0,1.1,0.9,1.0,10,0,1",
            "2026-10-26 09:30:00,1.0,1.1,0.9,1.0,10,0,1",
        ],
    )
    repo = CsvMarketBarsRepository(tmp_path)
    cov = repo.coverage("DEMO")
    assert cov is not None
    assert cov.n_rows == 3
    assert cov.n_days == 3
    assert cov.first_ts == datetime(2026, 10, 19, 9, 30)
    assert cov.last_ts == datetime(2026, 10, 26, 9, 30)
    assert cov.missing_weekdays == [
        "2026-10-21",
        "2026-10-22",
        "2026-10-23",
        "2026-10-24",
        "2026-10-25",
    ]
    assert cov.gaps_over_3_days == [{"from": "2026-10-20", "to": "2026-10-26", "calendar_days": 6}]


def test_ignores_malformed_rows(tmp_path: Path) -> None:
    write_csv(
        tmp_path,
        "DEMO",
        [
            "2026-10-19 09:30:00,1.0,1.1,0.9,1.0,10,0,1",
            "not-a-timestamp,1.0,1.1,0.9,1.0,10,0,1",
            "2026-10-19 09:35:00,1.0,1.1,0.9,1.0,10,0,1",
        ],
    )
    repo = CsvMarketBarsRepository(tmp_path)
    bars = repo.bars_for_day("DEMO", date(2026, 10, 19))
    assert len(bars) == 2


def test_sha256_is_deterministic(tmp_path: Path) -> None:
    write_csv(tmp_path, "DEMO", ["2026-10-19 09:30:00,1.0,1.1,0.9,1.0,10,0,1"])
    repo = CsvMarketBarsRepository(tmp_path)
    entry = repo.to_manifest_entry("DEMO")
    assert entry is not None
    assert entry["sha256"] == entry["sha256"]
    assert len(entry["sha256"]) == 64
