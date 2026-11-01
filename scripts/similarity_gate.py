"""Formal Similarity Gate (S3 Phase 5b item 6). Compares S2 chart anchors vs real
US500 M5 bars using broker rule server = ET + 7 h (US DST: UTC+2 std / UTC+3 dst).
Writes artifacts/similarity_gate.json."""

from __future__ import annotations

import csv
import glob
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
RAW = Path("data/market/raw/rates_US500_M5.csv")
TF = "%Y-%m-%d %H:%M:%S"
OUT = Path("artifacts/similarity_gate.json")
DS, DE = 3, 11


def nth_wd(y, m, wd, n):
    f = date(y, m, 1)
    o = (wd - f.weekday()) % 7
    return f + timedelta(days=o + 7 * (n - 1))


def is_us_dst(d):
    if d.month < DS or d.month > DE:
        return False
    if DS < d.month < DE:
        return True
    t = nth_wd(d.year, d.month, 6, 2) if d.month == DS else nth_wd(d.year, d.month, 6, 1)
    return d >= t if d.month == DS else d < t


def off_for(d):
    return timedelta(hours=-3 if is_us_dst(d) else -2)


def load_bars():
    g = {}
    with RAW.open("r", encoding="utf-8-sig", newline="") as h:
        for row in csv.DictReader(h):
            ts = datetime.strptime(row["time_server"].strip(), TF)
            g.setdefault(ts.date(), []).append(
                {
                    "ts": ts,
                    "o": float(row["open"]),
                    "h": float(row["high"]),
                    "l": float(row["low"]),
                    "c": float(row["close"]),
                }
            )
    return g


def et_session(bars, day):
    off = off_for(day)
    eto = timedelta(hours=-4 if is_us_dst(day) else -5)
    open_et = datetime.combine(day, time(9, 30), tzinfo=timezone(eto))
    close_et = datetime.combine(day, time(16, 0), tzinfo=timezone(eto))
    out = []
    for b in bars:
        t = (b["ts"].replace(tzinfo=timezone(timedelta(0))) + off).astimezone(ET)
        if open_et <= t < close_et:
            out.append({"t": t, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]})
    return out


def hl(s):
    if not s:
        return None, None
    return max(range(len(s)), key=lambda i: s[i]["h"]), min(range(len(s)), key=lambda i: s[i]["l"])


def dir1(s):
    if len(s) < 2:
        return "flat"
    last_c = s[:12][-1]["c"]
    first_o = s[0]["o"]
    if last_c > first_o:
        return "up"
    if last_c < first_o:
        return "down"
    return "flat"


def main():
    by_day = load_bars()
    results = []
    for p in sorted(glob.glob("artifacts/labels/*.json")):
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        a = d.get("anchors") or {}
        hi_hint = a.get("high_of_day_bar_index_hint")
        lo_hint = a.get("low_of_day_bar_index_hint")
        if hi_hint is None and lo_hint is None:
            continue
        ld = date.fromisoformat(d["date"])
        s = et_session(by_day.get(ld, []), ld)
        if not s:
            results.append({"id": d["image_id"], "day": ld.isoformat(), "skipped": True})
            continue
        hi_a, lo_a = hl(s)
        d_a = dir1(s)
        hi_h, lo_h = hi_hint, lo_hint
        hi_e = abs(hi_h - hi_a) if hi_h is not None and hi_a is not None else None
        lo_e = abs(lo_h - lo_a) if lo_h is not None and lo_a is not None else None
        dir_h = a.get("open_dir_first_hour")
        dir_match = (dir_h == d_a) if dir_h else None
        results.append(
            {
                "id": d["image_id"],
                "day": ld.isoformat(),
                "n": len(s),
                "hi_h": hi_h,
                "hi_a": hi_a,
                "hi_e": hi_e,
                "lo_h": lo_h,
                "lo_a": lo_a,
                "lo_e": lo_e,
                "dir_h": dir_h,
                "dir_a": d_a,
                "dir_match": dir_match,
            }
        )
    v = [r for r in results if not r.get("skipped")]
    n = len(v)
    dm = [r for r in v if r["dir_match"] is not None]
    da = sum(1 for r in dm if r["dir_match"]) / len(dm) if dm else 0
    e = [r["hi_e"] for r in v if r["hi_e"] is not None]
    e += [r["lo_e"] for r in v if r["lo_e"] is not None]
    med = median(e) if e else None
    gf = da >= 0.90 and med is not None and med <= 3
    gs = (0.75 <= da < 0.90) or (med is not None and 3 <= med <= 6)
    gate = "GO-FINE" if gf else ("GO-STRUCTURAL" if gs else "STOP")
    rep = {
        "raw_csv": str(RAW),
        "broker_rule": "server = ET + 7 h (US DST)",
        "n_with_anchors": len(results),
        "n_valid": n,
        "direction_agreement": da,
        "median_bar_index_error": med,
        "go_fine": gf,
        "go_structural": gs,
        "stop": not (gf or gs),
        "gate_decision": gate,
        "tolerance_bars": 3 if gf else (5 if gs else None),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"anchors={len(results)} valid={n} dir_ag={da:.1%} med_err={med}")
    print(f"GATE: {gate} tolerance={'±3' if gf else ('±5' if gs else 'STOP')}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
