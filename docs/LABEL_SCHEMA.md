# LABEL_SCHEMA (v1, frozen by ADR-004; additive reviewer fields by ADR-007;
# compact extraction schema v3 by plan step S2)

Single source of truth for label structure: `src/brooks_lab/domain/labels.py`.
Machine-readable export: `brooks schema-export` → `artifacts/label_schema.json`.
Label schema stays v1: all post-freeze additions are OPTIONAL fields, so old
files validate under new code and new files stay readable (unknown fields are
preserved structurally; see ADR-007). Legacy taxonomy ids are migrated on READ
via `config/taxonomy_migrations.yaml` (`brooks_lab.infrastructure.label_store`);
every label/report is stamped with `extraction_meta.taxonomy_version` and
`extraction_meta.prompt_version`.

## Time convention

Brooks EOD chart axes use US session hours, but the FEED TIMEZONE VARIES:
PT-style axes read ≈ 06:30–13:00, others (April pair, 09-23) read 09:00–15:00,
consistent with a Central feed (RTH 08:30–15:15 CT). Axis clock labels are
therefore NOT comparable between images. Times are stored as `HH:MM` plus `tz`
(`ChartTime`), default `America/Los_Angeles`; per-image deviation is recorded
in `session_summary` and MUST be resolved against real bars in Phase 5.
Never convert to broker time here. Bar indices and prices from the image are
*hints only* (`bar_index_hint`, `price_hint`, `x_px`); real bar attachment
happens in Phase 5.

## DayLabel

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int ≥ 1 | Currently 1 |
| `image_id` | string | From the ingestion manifest (sha1[:12]) |
| `date` | date (YYYY-MM-DD) \| null | Trading date; null when the image shows no verifiable date |
| `day_type` | DayType enum | 14 canonical ids incl. `other` |
| `day_type_confidence` | 0..1 | Annotator/extractor confidence |
| `session_summary` | string | One-paragraph reading of the day |
| `scope_ok` | bool \| null | P11 scope filter from v3 responses (`null` = legacy label) |
| `scope_note` | string | Why `scope_ok=false` (crop, two-day chart, …) |
| `axis` | AxisInfo \| null | v3: axis style (`pt_0630_1300` \| `et_style_0900_1500` \| `other` \| `none`) + first/last clock label |
| `anchors` | Anchors \| null | v3 objective anchors (see below) |
| `needs_review` | bool | True when a lossy taxonomy migration touched the day type |
| `events` | list[EventLabel] | Max 200 |
| `extraction_meta` | ExtractionMeta | provider + model_id + prompt_version + taxonomy_version (+ extracted_at) |

## Anchors (v3 response)

| Field | Type | Notes |
|---|---|---|
| `open_dir_first_hour` | up \| down \| flat | Direction of the first hour |
| `day_close_vs_open` | above \| below \| near | Close vs open |
| `high_of_day_bar_index_hint` / `low_of_day_bar_index_hint` | int≥0 \| null | From the first bar of the shown session (±2 tolerance) |
| `n_bars_visible` | int≥0 \| null | Bar count of the shown session |

## Compact response schema v3 (extract_v3 / extract_day_v3)

The vision agent returns ONE compact JSON object per chart (never DayLabel v1,
never free text); `brooks write-response` validates it against the taxonomy
and writes the queue response atomically, then `brooks extract` converts it to
a DayLabel. Deviations must use `kind: "unmapped"` + verbatim `raw_label` —
never invented enum ids.

```json
{
  "image_id": "<from manifest>",
  "scope_ok": true,
  "scope_note": "",
  "day_type": "<enum id>",
  "day_type_conf": 0.0,
  "axis": {"style": "pt_0630_1300", "first_label": "06:35", "last_label": "12:55"},
  "anchors": {"open_dir_first_hour": "up", "day_close_vs_open": "above",
              "high_of_day_bar_index_hint": 55, "low_of_day_bar_index_hint": 12,
              "n_bars_visible": 78},
  "events": [{"kind": "<enum id|unmapped>", "start_bar_index_hint": 20,
              "end_bar_index_hint": 26, "direction": "bull",
              "outcome": "success", "conf": 0.8, "raw_label": "verbatim wording"}]
}
```

- `extract_day_v3` (day-only pass for charts with non-canonical titles) omits
  `events` entirely.
- `date` is NOT part of the response; the pipeline takes it from the manifest.
- Bar indices count from the FIRST BAR OF THE SHOWN SESSION (bars left of the
  day marker belong to the prior session). Wall-clock times are recorded only
  in `axis.first_label`/`axis.last_label`.
- Binding normalizations: traps → `failed_breakout`; `mm` → `measured_move`;
  day-part ranges → `trading_range_begin` + `trading_range_end` pairs;
  `bar_index_hint` is int-only; `bear_trend_resumption` is invalid;
  `bull_trend_resumption` is valid.

## EventLabel

| Field | Type | Notes |
|---|---|---|
| `label` | EventKind \| null | Canonical id; **null = unmapped**, must keep `raw_label` |
| `raw_label` | string | Verbatim annotator wording; never dropped |
| `modifiers` | list[string] | Reviewer modifier system: HH/LH/HL/LL, minor, at_ema, 2nd_leg, contracting, … (no new canonical id needed) |
| `role` | pattern \| entry_signal \| expectation \| day_part \| structure \| exit_signal \| day_phase \| context \| advice \| bar_pattern | What the row IS (default pattern). `bar_pattern` = ii/OO-style candle structures |
| `direction` | bull \| bear \| neutral | RESULT direction of the pattern (a bull trap that collapses is `bear`) |
| `start_time` / `end_time` | ChartTime \| null | Axis times (position from structure, never from text placement), not bar indices |
| `x_px` | [start, end] \| null | Pixel span for axis-less images |
| `bar_index_hint` / `price_hint` | int≥0 / float \| null | Fuzzy locators for Phase 5 attachment |
| `end_bar_index_hint` | int≥0 \| null | v3: optional end bar of compound events |
| `needs_review` | bool | True when a lossy taxonomy migration touched this event |
| `outcome` | success \| fail \| partial \| unclear | CLAIM-BASED: did what the label claims happen? (a failed breakout whose failure plays out is `success`) |
| `outcome_reason` | string | Why; record split results (bounce vs reversal) and failure modes here |
| `confidence` | 0..1 | Overall judgment (placement-weighted for indicator use) |
| `label_explicit` / `placement` | 0..1 \| null | Reviewer axes: text-explicitness vs position-certainty (null = unscored) |
| `evidence` | string | Supporting text/graphic from THIS image only |
| `source` | vision \| human \| engine | Who produced the label |

## Unmapped labels → review queue

Events with `label=null` are collected by `build_review_queue()` into counted
`ReviewItem`s (`raw_label`, count, image_ids, difflib suggestion). The user
decides merges; merges land in `taxonomy.yaml` synonyms with a new ADR.

## Migration

`migrate_day_label()` accepts the pre-v1 camelCase stub shape (no version) and
v1 payloads; newer versions raise. Schema changes require a version bump + ADR.

## Minimal example

```json
{
  "schema_version": 1,
  "image_id": "2e92a62eecc3",
  "date": "2022-07-29",
  "day_type": "spike_and_channel_bull",
  "day_type_confidence": 0.85,
  "session_summary": "Spike and channel bull trend; buyers held control all day.",
  "events": [
    {
      "label": "buy_the_close",
      "raw_label": "Buy The Close",
      "direction": "bull",
      "start_time": {"time": "12:55", "tz": "America/Los_Angeles"},
      "end_time": null,
      "outcome": "success",
      "confidence": 0.8,
      "evidence": "blue title bar + last-hour annotation",
      "source": "vision"
    }
  ],
  "extraction_meta": {
    "provider": "file",
    "model_id": "manual-review",
    "prompt_version": "extract_v1"
  }
}
```
