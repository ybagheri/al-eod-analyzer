# Extraction prompt v1 (extract_v1) — template

You are labelling one end-of-day review chart of the S&P 500 Emini (5-minute bars,
one full US session) for a personal research dataset. The chart is annotated by
price-action trader Al Brooks: blue title bar, coloured signal-bar boxes, dotted
trend/channel lines, and handwritten-style pattern notes.

## What to output

A single JSON object matching the label schema (DayLabel v1). No prose, no fences.

## How to read the chart (rules)

1. Read ONLY what is annotated or visibly evident. Do not infer unseen bars.
2. `day_type`: use one canonical id from the taxonomy below (or `other`).
3. `events`: one entry per visible annotation. `label` must be a canonical event id;
   if the wording has no canonical match, set `label` to null and keep the exact
   wording in `raw_label` (never drop it, never force a wrong id).
4. Times: read `HH:MM` from the chart axis (US Pacific). Store `{"time": "HH:MM",
   "tz": "America/Los_Angeles"}`. Omit times you cannot read (null).
5. `outcome`: judge success/fail only when the chart shows what happened after the
   event; else `unclear` with an `outcome_reason`.
6. `confidence`: 0..1 per day type and per event. List genuinely uncertain items
   with low confidence rather than guessing.
7. `evidence`: name the supporting text/graphic (e.g. "blue title bar",
   "red box on 10:35 bar", "dotted wedge lines").
8. `image_id` and `date` are given below — copy them exactly.
9. `extraction_meta`: {"provider": <given>, "model_id": <given>,
   "prompt_version": "extract_v1"}.

## Few-shot examples (textual, from reviewed charts)

Example A — 29 Jul 2022 (Spike and Channel Bull Trend):
day_type=spike_and_channel_bull (0.9). Events: spike (bull, morning, success),
channel (bull, midday, success), buy_the_close (bull, 12:55 PT, success,
evidence "Buy The Close note + strong last bars").

Example B — 1 Aug 2022 (Bull Trend From The Open, Then Trading Range):
day_type=bull_trend_from_open (0.7, note the afternoon range in session_summary).
Events: spike (bull, success), trading_range_begin/trading_range_end (neutral,
times from axis), failed_breakout (bear attempt midday, fail).

## Taxonomy and schema

Appended after this template by the pipeline (canonical ids + field reference).
