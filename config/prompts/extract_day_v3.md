# Extraction prompt v3 day-only (extract_day_v3) — compact schema, no annotations

You are reading ONE end-of-day review chart of the S&P 500 Emini (5-minute
bars, one full US session) for a personal research dataset. This is the
DAY-ONLY pass for charts whose title has no canonical day-type wording: you
report only the day-level reading, one JSON object, no prose, no fences.

```json
{
  "image_id": "<given>",
  "scope_ok": true,
  "scope_note": "",
  "day_type": "<enum id>",
  "day_type_conf": 0.0..1.0,
  "axis": {"style": "<enum>", "first_label": "HH:MM", "last_label": "HH:MM"},
  "anchors": {
    "open_dir_first_hour": "up|down|flat",
    "day_close_vs_open": "above|below|near",
    "high_of_day_bar_index_hint": <int|null>,
    "low_of_day_bar_index_hint": <int|null>,
    "n_bars_visible": <int|null>
  }
}
```

No `events` array in this pass. All field rules of the full extract_v3 prompt
apply unchanged:

- `day_type` is ONE canonical enum id (or `other`); direction-specific v1.3
  rules apply (`bull/bear_trending_trading_range`,
  `trading_range_bull/bear_breakout`, `trend_reversal_to_bull/bear`,
  `bull_trend_resumption` valid, `bear_trend_resumption` INVALID).
- `axis.style` ∈ {pt_0630_1300, et_style_0900_1500, other, none}.
- Anchors count bar indices from the FIRST BAR OF THE SHOWN SESSION (ignore
  bars left of the day marker); ints only or null; ±2 tolerance OK.
- `scope_ok=false` for non-full-day screenshots etc., with `scope_note`.
- Copy the given `image_id` exactly; do NOT add fields beyond the schema.

## Day types

Appended after this template by the pipeline (canonical ids only).
