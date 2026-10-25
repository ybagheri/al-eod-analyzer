"""Validate MT5-exported M5 CSVs and build artifacts/market_manifest.json (S3, Phase 5b).

Contract: data/market/raw/rates_<SYMBOL>_M5.csv with header
time_server,open,high,low,close,tick_volume,real_volume,spread
(server time, ISO 'YYYY-MM-DD HH:MM:SS', '.' decimals), plus a companion
<SYMBOL>_export_info.txt and the optional symbol scan symbols_sp500.csv.

git-ignored and must never be committed (public repo). Only this report
(hashes, coverage, gaps, anomaly counts) is committed. Usage:
    python scripts/market_validate.py [--raw-dir data/market/raw] [--out ...]
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

EXPECTED_COLUMNS = (
    "time_server",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "real_volume",
    "spread",
)
RATES_PATTERN = re.compile(r"^rates_(?P<symbol>.+)_M5\.csv$")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_SUSPICIOUS_RANGE_FRACTION = 0.10
MAX_LISTED_ITEMS = 50


def parse_rates_csv(path: Path) -> dict:
    """Parse one rates CSV into {'rows': [...], 'errors': [...]}."""
    rows: list[dict] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = handle.readline().strip()
        columns = tuple(part.strip() for part in header.split(","))
        if columns != EXPECTED_COLUMNS:
            errors.append(f"bad_header:{header}")
        else:
            for line_no, line in enumerate(handle, start=2):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != len(EXPECTED_COLUMNS):
                    errors.append(f"line{line_no}:bad_field_count")
                    continue
                row = parse_row(parts)
                if row is None:
                    errors.append(f"line{line_no}:unparseable")
                    continue
                rows.append(row)
    return {"rows": rows, "errors": errors}


def parse_row(parts: list[str]) -> dict | None:
    try:
        timestamp = datetime.strptime(parts[0], TIME_FORMAT)
        return {
            "time": timestamp,
            "open": float(parts[1]),
            "high": float(parts[2]),
            "low": float(parts[3]),
            "close": float(parts[4]),
            "tick_volume": int(parts[5]),
            "real_volume": int(parts[6]),
            "spread": int(parts[7]),
        }
    except (ValueError, IndexError):
        return None


def validate_rows(rows: list[dict]) -> list[str]:
    """Return anomaly labels: OHLC violations, duplicates, non-monotonic time."""
    issues: list[str] = []
    previous_time: datetime | None = None
    seen_times: set[datetime] = set()
    for index, row in enumerate(rows, start=2):
        if row["high"] < row["low"]:
            issues.append(f"line{index}:high_below_low")
        if not (
            row["low"]
            <= min(row["open"], row["close"])
            <= max(row["open"], row["close"])
            <= row["high"]
        ):
            issues.append(f"line{index}:ohlc_out_of_range")
        if min(row["open"], row["close"], row["low"], row["high"]) <= 0:
            issues.append(f"line{index}:nonpositive_price")
        if row["tick_volume"] < 0 or row["real_volume"] < 0 or row["spread"] < 0:
            issues.append(f"line{index}:negative_value")
        if row["time"] in seen_times:
            issues.append(f"line{index}:duplicate_time")
        elif previous_time is not None and row["time"] < previous_time:
            issues.append(f"line{index}:time_regression")
        seen_times.add(row["time"])
        previous_time = row["time"]
    for index, row in enumerate(rows, start=2):
        span = (row["high"] - row["low"]) / row["close"] if row["close"] > 0 else 0.0
        if span > MAX_SUSPICIOUS_RANGE_FRACTION:
            issues.append(f"line{index}:suspicious_range")
    return issues


def coverage_summary(rows: list[dict]) -> dict:
    """Coverage preview in server time: span, per-day counts, missing weekdays, large gaps."""
    summary: dict = {"n_rows": len(rows)}
    if not rows:
        summary["first_ts"] = None
        summary["last_ts"] = None
        return summary
    summary["first_ts"] = rows[0]["time"].isoformat(sep=" ")
    summary["last_ts"] = rows[-1]["time"].isoformat(sep=" ")
    day_counts: dict[date, int] = {}
    for row in rows:
        day_counts[row["time"].date()] = day_counts.get(row["time"].date(), 0) + 1
    summary["n_days"] = len(day_counts)
    counts = sorted(day_counts.values())
    summary["bars_per_day_min"] = counts[0]
    summary["bars_per_day_max"] = counts[-1]
    summary["bars_per_day_median"] = counts[len(counts) // 2]
    counts_288 = sum(1 for count in counts if count == 288)
    summary["days_with_288_bars"] = counts_288
    present = set(day_counts)
    first_day, last_day = min(present), max(present)
    missing: list[str] = []
    cursor = first_day
    while cursor <= last_day and len(missing) < MAX_LISTED_ITEMS:
        if cursor.weekday() < 5 and cursor not in present:
            missing.append(cursor.isoformat())
        cursor += timedelta(days=1)
    summary["missing_weekdays"] = missing
    sorted_days = sorted(present)
    gaps: list[dict] = []
    for previous, current in itertools.pairwise(sorted_days):
        gap = (current - previous).days
        if gap > 3:
            gaps.append(
                {"from": previous.isoformat(), "to": current.isoformat(), "calendar_days": gap}
            )
        if len(gaps) >= MAX_LISTED_ITEMS:
            break
    summary["gaps_over_3_days"] = gaps
    return summary


def parse_export_info(path: Path) -> dict:
    """Parse the '<SYMBOL>_export_info.txt' key: value file written by ExportRatesM5.mq5."""
    info: dict = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        info[key.strip()] = value.strip()
    return info


def build_manifest(raw_dir: Path, out_path: Path) -> dict:
    """Validate every rates_*_M5.csv in raw_dir; write manifest with hashes and coverage."""
    files: list[dict] = []
    symbols_scan = raw_dir / "symbols_sp500.csv"
    for path in sorted(raw_dir.glob("rates_*_M5.csv")):
        match = RATES_PATTERN.match(path.name)
        symbol = match.group("symbol") if match else path.stem
        parsed = parse_rates_csv(path)
        row_issues = validate_rows(parsed["rows"])
        info_path = path.with_name(f"{symbol}_export_info.txt")
        entry = {
            "symbol": symbol,
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "n_errors": len(parsed["errors"]),
            "errors": parsed["errors"][:MAX_LISTED_ITEMS],
            "n_anomalies": len(row_issues),
            "anomalies": row_issues[:MAX_LISTED_ITEMS],
            "coverage": coverage_summary(parsed["rows"]),
        }
        if parsed["rows"]:
            entry["first_ts"] = parsed["rows"][0]["time"].isoformat(sep=" ")
            entry["last_ts"] = parsed["rows"][-1]["time"].isoformat(sep=" ")
        if info_path.exists():
            info = parse_export_info(info_path)
            declared_bars = info.get("bar_count")
            entry["export_info"] = info
            entry["bar_count_matches_info"] = declared_bars is None or declared_bars == str(
                len(parsed["rows"])
            )
        else:
            entry["export_info"] = None
            entry["bar_count_matches_info"] = None
        files.append(entry)
    manifest = {
        "raw_dir": str(raw_dir),
        "ok": all(
            entry["n_errors"] == 0
            and entry["n_anomalies"] == 0
            and entry["bar_count_matches_info"] is not False
            for entry in files
        ),
        "symbols_scan_present": symbols_scan.exists(),
        "files": files,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    repo = REPO
    raw_dir = repo / "data" / "market" / "raw"
    out_path = repo / "artifacts" / "market_manifest.json"
    options = sys.argv[1:]
    if "--raw-dir" in options:
        raw_dir = Path(options[options.index("--raw-dir") + 1])
    if "--out" in options:
        out_path = Path(options[options.index("--out") + 1])
    if not raw_dir.exists():
        print(f"raw dir not found: {raw_dir}")
        return 1
    manifest = build_manifest(raw_dir, out_path)
    for entry in manifest["files"]:
        print(
            f"{entry['symbol']}: rows={entry['coverage'].get('n_rows', 0)} "
            f"errors={entry['n_errors']} anomalies={entry['n_anomalies']} "
            f"span={entry.get('first_ts')} .. {entry.get('last_ts')}"
        )
    print(f"manifest ok={manifest['ok']} -> {out_path}")
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
