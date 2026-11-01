"""Empirical broker-time offset detection (S3 Phase 5b item 3).

The US cash open (09:30 ET) typically has the highest tick volume. For each
candidate server->ET offset, convert server bars to ET and check whether the
max-volume bar on each day falls at/near 09:30 ET. Best offset wins.
Writes artifacts/broker_offset_report.json only (not broker_time.yaml).
"""

from __future__ import annotations

import csv
import json
import statistics
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
RAW_CSV = Path("data/market/raw/rates_US500_M5.csv")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
REPORT_OUT = Path("artifacts/broker_offset_report.json")
DS, DE = 3, 11


def nth_wd(y, m, wd, n):
    first = date(y, m, 1)
    off = (wd - first.weekday()) % 7
    return first + timedelta(days=off + 7 * (n - 1))


def dst_trans(y, m):
    return nth_wd(y, m, 6, 2) if m == DS else nth_wd(y, m, 6, 1)


def is_us_dst(d):
    if d.month < DS or d.month > DE:
        return False
    if DS < d.month < DE:
        return True
    t = dst_trans(d.year, d.month)
    return d >= t if d.month == DS else d < t


def et_off(d):
    return timedelta(hours=-4) if is_us_dst(d) else timedelta(hours=-5)


def load_bars(p):
    rows = []
    with p.open("r", encoding="utf-8-sig", newline="") as h:
        for row in csv.DictReader(h):
            rows.append(
                {
                    "time": datetime.strptime(row["time_server"].strip(), TIME_FORMAT),
                    "v": int(row["tick_volume"]),
                }
            )
    return rows


def group_by_day(rows):
    g = {}
    for r in rows:
        g.setdefault(r["time"].date(), []).append(r)
    return g


def eval_off(byd, oh):
    off = timedelta(hours=oh)
    tot = ex = w5 = w15 = 0
    errs = []
    for d, bars in sorted(byd.items()):
        if d.weekday() >= 5 or not bars:
            continue
        tot += 1
        eo = et_off(d)
        b = max(bars, key=lambda x: x["v"])
        et_a = (b["time"] + off).replace(tzinfo=timezone(eo))
        tgt = datetime.combine(d, time(9, 30), tzinfo=timezone(eo))
        dm = (et_a - tgt).total_seconds() / 60.0
        errs.append(dm)
        if abs(dm) < 1:
            ex += 1
        if abs(dm) <= 5:
            w5 += 1
        if abs(dm) <= 15:
            w15 += 1
    if tot == 0:
        return {"offset_hours": oh, "total_days": 0}
    return {
        "offset_hours": oh,
        "total_days": tot,
        "aligned_exact": ex,
        "aligned_exact_pct": ex / tot,
        "aligned_within_5min": w5,
        "aligned_within_5min_pct": w5 / tot,
        "aligned_within_15min": w15,
        "aligned_within_15min_pct": w15 / tot,
        "median_error_min": statistics.median(errs),
        "mean_abs_error_min": statistics.mean([abs(e) for e in errs]),
    }


def main():
    byd = group_by_day(load_bars(RAW_CSV))
    print(f"Loaded bars across {len(byd)} server days")
    cands = [round(-h / 2, 1) for h in range(4, 29)]
    res = [eval_off(byd, o) for o in cands]
    for r in res:
        off_h = r["offset_hours"]
        days_n = r["total_days"]
        exact_pct = r["aligned_exact_pct"] * 100
        w5m_pct = r["aligned_within_5min_pct"] * 100
        w15m_pct = r["aligned_within_15min_pct"] * 100
        med = r["median_error_min"]
        line1 = f"offset={off_h:>5}h: days={days_n:>4} exact={exact_pct:5.1f}%"
        line2 = f"w5m={w5m_pct:5.1f}% w15m={w15m_pct:5.1f}% med={med}"
        print(line1 + " " + line2)
        print(line1 + " " + line2)
    valid = [r for r in res if r["total_days"] > 0]
    best = max(
        valid,
        key=lambda r: (
            r["aligned_within_5min_pct"],
            -abs(r["median_error_min"] or 0),
        ),
    )
    print(
        f"\nBEST fixed offset: {best['offset_hours']}h "
        f"(w5m={best['aligned_within_5min_pct'] * 100:.1f}% "
        f"exact={best['aligned_exact_pct'] * 100:.1f}%)"
    )
    for name, s in (
        ("DST", {d for d in byd if is_us_dst(d) and d.weekday() < 5}),
        ("NonDST", {d for d in byd if not is_us_dst(d) and d.weekday() < 5}),
    ):
        rbd = {d: byd[d] for d in s if d in byd}
        vr = [r for r in [eval_off(rbd, o) for o in cands] if r["total_days"] > 0]
        if vr:
            br = max(
                vr,
                key=lambda r: (
                    r["aligned_within_5min_pct"],
                    -abs(r["median_error_min"] or 0),
                ),
            )
            off_h2 = br["offset_hours"]
            w5m_pct2 = br["aligned_within_5min_pct"] * 100
            days_n2 = br["total_days"]
            line3 = f"{name}: best={off_h2}h (w5m={w5m_pct2:.1f}% days={days_n2})"
            print(line3)
            print(line3)
    report = {
        "raw_csv": str(RAW_CSV),
        "n_server_days": len(byd),
        "candidates_tested": cands,
        "results": res,
        "best_fixed_offset": best,
        "note": "Fixed-offset scan; seasonal rule from per-regime best above.",
    }
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nReport -> {REPORT_OUT}")


if __name__ == "__main__":
    main()
