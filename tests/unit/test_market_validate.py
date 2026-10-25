"""Unit tests for scripts/market_validate.py (S3 CSV contract and coverage checks)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import market_validate as mv

HEADER = ",".join(mv.EXPECTED_COLUMNS) + "\n"


def make_csv(rows: list[str]) -> str:
    return HEADER + "\n".join(rows) + "\n"


def rates(symbol: str, rows: list[str], raw_dir: Path, info: str | None = None) -> Path:
    path = raw_dir / f"rates_{symbol}_M5.csv"
    path.write_text(make_csv(rows), encoding="utf-8")
    if info is not None:
        (raw_dir / f"{symbol}_export_info.txt").write_text(info, encoding="utf-8")
    return path


def test_parse_and_validate_clean_rows(tmp_path: Path) -> None:
    text = make_csv(
        [
            "2026-10-19 09:30:00,6700.00,6702.00,6699.00,6701.25,1200,5000,30",
            "2026-10-19 09:35:00,6701.25,6703.50,6700.50,6703.00,900,3000,25",
        ]
    )
    tmp = tmp_path / "_tmp_rates.csv"
    tmp.write_text(text, encoding="utf-8")
    parsed = mv.parse_rates_csv(tmp)
    assert parsed["errors"] == []
    assert len(parsed["rows"]) == 2
    assert mv.validate_rows(parsed["rows"]) == []
    row = parsed["rows"][0]
    assert row["time"] == datetime(2026, 10, 19, 9, 30)
    assert row["close"] == 6701.25


def test_bad_header_and_unparseable_line(tmp_path: Path) -> None:
    text = "timestamp,open\n2026-10-19,6700.00\n"
    path = tmp_path / "_tmp_bad.csv"
    path.write_text(text, encoding="utf-8")
    parsed = mv.parse_rates_csv(path)
    path.unlink()
    assert any(error.startswith("bad_header") for error in parsed["errors"])
    assert all(
        "unparseable" in error or "bad_field_count" in error for error in parsed["errors"][1:]
    )


def test_row_anomalies_flagged() -> None:
    rows = [
        {
            "time": datetime(2026, 10, 19, 9, 30),
            "open": 6700.0,
            "high": 6698.0,  # below low
            "low": 6699.0,
            "close": 6697.0,  # outside [low, high]
            "tick_volume": 100,
            "real_volume": 10,
            "spread": 5,
        },
        {
            "time": datetime(2026, 10, 19, 9, 25),  # regression + duplicate
            "open": 6700.0,
            "high": 6701.0,
            "low": 6699.0,
            "close": 6700.5,
            "tick_volume": -1,
            "real_volume": 0,
            "spread": 0,
        },
        {
            "time": datetime(2026, 10, 19, 9, 25),  # duplicate time
            "open": 6700.0,
            "high": 6701.0,
            "low": 6699.0,
            "close": 6700.5,
            "tick_volume": 10,
            "real_volume": 0,
            "spread": 0,
        },
    ]
    issues = mv.validate_rows(rows)
    assert "line2:high_below_low" in issues
    assert "line2:ohlc_out_of_range" in issues
    assert "line3:time_regression" in issues
    assert "line3:negative_value" in issues
    assert "line4:duplicate_time" in issues


def test_suspicious_range_flagged() -> None:
    rows = [
        {
            "time": datetime(2026, 10, 19, 9, 30),
            "open": 100.0,
            "high": 500.0,  # 400% range
            "low": 100.0,
            "close": 100.0,
            "tick_volume": 10,
            "real_volume": 0,
            "spread": 0,
        }
    ]
    issues = mv.validate_rows(rows)
    assert issues == ["line2:suspicious_range"]


def test_missing_weekday_and_large_gap(tmp_path: Path) -> None:
    rows = []
    # Mon 2026-10-19, Tue 2026-10-20, Mon 2026-10-26; two bars per day.
    for stamp in (
        "2026-10-19 21:30:00",
        "2026-10-19 21:35:00",
        "2026-10-20 21:30:00",
        "2026-10-20 21:35:00",
        "2026-10-26 21:30:00",
        "2026-10-26 21:35:00",
    ):
        rows.append(f"{stamp},1.0,1.1,0.9,1.0,10,0,1")
    rates("DEMO", rows, tmp_path)
    parsed = mv.parse_rates_csv(tmp_path / "rates_DEMO_M5.csv")
    summary = mv.coverage_summary(parsed["rows"])
    # Wed 10-21, Thu 10-22, Fri 10-23 missing in the inner span.
    assert summary["missing_weekdays"] == ["2026-10-21", "2026-10-22", "2026-10-23"]
    assert summary["gaps_over_3_days"] == [
        {"from": "2026-10-20", "to": "2026-10-26", "calendar_days": 6}
    ]
    assert summary["n_days"] == 3
    assert summary["bars_per_day_median"] == 2


def test_build_manifest_with_info_and_mismatch(tmp_path: Path) -> None:
    rows = ["2026-10-19 21:30:00,1.0,1.1,0.9,1.0,10,0,1"]
    rates(
        "DEMO", rows, tmp_path, info="symbol: DEMO\nbar_count: 7\nfirst_bar: 2026-10-19 21:30:00\n"
    )
    (tmp_path / "symbols_sp500.csv").write_text(
        "name,description\nUS500,S&P 500\n", encoding="utf-8"
    )
    out = tmp_path / "artifacts" / "market_manifest.json"
    manifest = mv.build_manifest(tmp_path, out)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved == manifest
    entry = manifest["files"][0]
    assert entry["symbol"] == "DEMO"
    assert entry["export_info"]["bar_count"] == "7"
    assert entry["bar_count_matches_info"] is False  # 7 declared vs 1 row
    assert manifest["ok"] is False
    assert manifest["symbols_scan_present"] is True
    assert entry["sha256"] != ""
