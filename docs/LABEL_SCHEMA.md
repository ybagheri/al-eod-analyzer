# LABEL_SCHEMA (v1, frozen by ADR-004)

Single source of truth for label structure: `src/brooks_lab/domain/labels.py`.
Machine-readable export: `brooks schema-export` → `artifacts/label_schema.json`.

## Time convention

Brooks EOD chart axes use **US Pacific time** (regular session ≈ 06:30–13:00 PT).
Times are stored as `HH:MM` strings plus a `tz` field (`ChartTime`), default
`America/Los_Angeles`. Never convert to broker time here — session mapping is a
Phase 5 concern. Bar indices and prices from the image are *hints only*
(`bar_index_hint`, `price_hint`); real bar attachment happens in Phase 5.

## DayLabel

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int ≥ 1 | Currently 1 |
| `image_id` | string | From the ingestion manifest (sha1[:12]) |
| `date` | date (YYYY-MM-DD) | Trading date shown on the chart |
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
| `direction` | bull \| bear \| neutral | Default neutral |
| `start_time` / `end_time` | ChartTime \| null | Axis times, not bar indices |
| `bar_index_hint` / `price_hint` | int≥0 / float \| null | Fuzzy locators for Phase 5 attachment |
| `outcome` | success \| fail \| partial \| unclear | Hindsight outcome from the annotation |
| `outcome_reason` | string | Why the outcome was judged so |
| `confidence` | 0..1 | Per-event confidence |
| `evidence` | string | Which text/graphic supports this event |
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
