# Extraction prompt v3 (extract_v3) — compact schema, bar-index first

You are labelling ONE end-of-day review chart of the S&P 500 Emini (5-minute
bars, one full US session) for a personal research dataset. The chart is
annotated by price-action trader Al Brooks: blue title bar, coloured signal-bar
boxes, dotted trend/channel lines, and handwritten-style pattern notes.

## What to output

A single JSON object, no prose, no fences. Compact schema v3 (bar-index first):

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
  },
  "events": [
    {"kind": "<enum id>", "start_bar_index_hint": <int>,
     "end_bar_index_hint": <int|null>, "direction": "bull|bear|neutral",
     "outcome": "success|fail|partial|unclear", "conf": 0.0..1.0,
     "raw_label": "<verbatim wording>"}
  ]
}
```

- `scope_ok=false` means the image is NOT a full-day EOD review chart of one
  session (e.g. screenshot crop, two-day chart, dashboard, non-chart). Put the
  reason in `scope_note`; keep other fields best-effort.
- Image identity: `date` is NOT part of the response. The pipeline supplies it.
  Copy the given `image_id` exactly.

## Field rules (binding)

1. `day_type`: one canonical enum id (or `other`). Binding v1.3 rules:
   - Trending trading ranges are DIRECTION-SPECIFIC:
     `bull_trending_trading_range` / `bear_trending_trading_range`.
   - A range that most of the day then breaks out is the COMPOUND type
     `trading_range_bull_breakout` / `trading_range_bear_breakout`.
   - No generic `reversal_day`: use `trend_reversal_to_bull` /
     `trend_reversal_to_bear` by the direction it turns INTO (the PM regime).
   - `bear_trend_resumption` is INVALID. `bull_trend_resumption` is valid
     (TR open -> breakout -> trend resumption regime).
   - The blue title names the day type OR its quality; quality notes
     ("weaker trend", "okay swing buys") become event `raw_label` context,
     never a conflicting day_type.
2. `axis`: `style` is one of `pt_0630_1300`, `et_style_0900_1500`, `other`,
   `none`. `first_label` / `last_label` are the first/last clock labels you can
   read on the axis (`""` when unreadable).
3. `anchors` are cheap objective reads used to validate date/time against real
   bars later. Bar indices count from the FIRST BAR OF THE SHOWN SESSION
   (bars left of the day marker belong to the prior session and are ignored
   for indices and anchors). ±2 bar tolerance is acceptable; ints only or null.
4. `events`: one entry per visible annotation. `kind` is an enum id from the
   list below — NEVER invent enum ids. Compound or unknown wording goes to
   `kind: "unmapped"` with the exact wording in `raw_label`.
   - Traps normalize to `failed_breakout` (direction = the trap's RESULT:
     a bear trap that rallies up is failed_breakout with direction `bull`).
   - `mm` maps to `measured_move`.
   - Day-part ranges are a PAIR: `trading_range_begin` + `trading_range_end`
     (two entries), never a bare `trading_range` event.
   - POSITION RULE: take `start_bar_index_hint` from the structure the note
     points at (arrow, dotted line, box, bars), never from where the text
     sits. Text is usually 10-30 minutes after the pattern.
   - OUTCOME RULE: outcome = did the note's own CLAIM happen? A failed
     breakout whose failure plays out is `success`. Never copy words like
     "failed"/"reversal" into outcome.
   - STACKED-NOTES RULE: a multi-line note block describing ONE structure is
     ONE event; put the extra readings in `raw_label` verbatim.
   - ADVICE RULE: notes like "TTR better to stop trading" are advice; record
     the structure they refer to as a second event; only testable claims get
     an outcome.
   - Prefer bar indices over wall-clock times everywhere. Wall-clock axis
     labels go in `axis` only.
5. Copy enums exactly (lower_snake_case). `conf` is your own 0..1 confidence
   per item; low genuine confidence beats guessing.

## Event enum ids

Appended after this template by the pipeline (canonical ids only; day types
likewise). Use ONLY these ids; anything else goes to `unmapped`.
