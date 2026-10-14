# LABEL_SCHEMA (v1, frozen by ADR-004; additive reviewer fields by ADR-007)

Single source of truth for label structure: `src/brooks_lab/domain/labels.py`.
Machine-readable export: `brooks schema-export` → `artifacts/label_schema.json`.
Label schema stays v1: all post-freeze additions are OPTIONAL fields, so old
files validate under new code and new files stay readable (unknown fields are
preserved structurally; see ADR-007).

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
| `events` | list[EventLabel] | Max 200 |
| `extraction_meta` | ExtractionMeta | provider + model_id + prompt_version (+ extracted_at) |

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
