# Extraction prompt v2 (extract_v2) — template

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
   event; else `unclear` with an `outcome_reason`. Outcome means "did what the
   label claims happen" (a failed breakout whose failure plays out is `success`).
6. `direction`: the RESULT direction of the pattern (a bull trap that collapses
   is `bear`), not the direction of the move that created it.
7. `confidence`: 0..1 per day type and per event. List genuinely uncertain items
   with low confidence rather than guessing.
8. `evidence`: name the supporting text/graphic from THIS image only
   (e.g. "blue title bar", "red box on 10:35 bar", "dotted wedge lines").
   Never justify from other charts in the series.
9. `image_id` and `date` are given below — copy them exactly. If the image shows
   no verifiable date, set `date` to null and say so in `session_summary`.
10. `extraction_meta`: {"provider": <given>, "model_id": <given>,
    "prompt_version": "extract_v2"}.
11. Modifiers: append nuance to `modifiers` (e.g. HH, LH, HL, LL, minor, at_ema,
    2nd_leg, contracting) instead of inventing new labels.

## Reviewer rules (from human review, binding)

- TIME/POSITION RULE: take position from the structure the note points at
  (arrow, dotted line, box, bars), never from where the text sits. Text is
  usually placed beside or below the pattern, often 10–30 minutes later.
- EVIDENCE RULE: evidence must come only from the current image. Reject
  phrases like "same template placement as other charts".
- STACKED-NOTES RULE: a multi-line note block (e.g. "Wedge / DT / 50% pullback")
  describes ONE structure: emit one row with modifiers, not one row per line.
- CROSS-IMAGE TIME RULE: axis clock labels are not comparable between images
  (the feed offset varies: some axes read PT-style 06:30–13:00, others
  09:00–15:00). For each image record first_bar_label, last_bar_label, and
  bar_no (counted from the first visible bar) for every pattern. Treat clock
  time as secondary; keep `tz` as printed and flag suspicion in the summary.
- QUALIFIED LABELS RULE: when a note contains two claims (e.g. "credible swing
  buy, but weak signal bar"), score each claim separately and use
  outcome=partial when only one holds. Record bounce and reversal results
  separately in `outcome_reason`.
- COMPOUND NOTE RULE (replaces context-clause handling): a note of the form
  "X but Y so Z" has three parts: X = pattern/signal row; Y = context modifier
  or reason; Z = expectation row with its own dir and outcome. X and Z often
  point in opposite directions, so never give the whole note one dir/outcome.
  Place X by what the chart draws (line, box, arrow), not by where the text sits.
- PATTERN IDENTITY RULE: several patterns may share one name in one image. Give
  each its own id, base_type, role (independent | push_N_of_<parent> | parabolic),
  x_px range and price. Never merge or drop rows because the names match.
- UI ARTIFACTS RULE: ignore mouse cursors, window buttons, watermarks and
  screenshot borders. They are never evidence, and a cursor's position must not
  be used as a price.
- DAY MARKER RULE: the day marker on the axis is the reference for the session
  date; a date label at the far left belongs to the prior session (use it only
  as the year source). Bars left of the day marker belong to the prior session
  and are ignored.
- ABBREVIATION RULE: if a note's abbreviation is not in the glossary (e.g. "HST"),
  do not mark the row "unclear". Test the best reading against the chart geometry,
  record it as unverified with the check you made, and propose a glossary entry.
- TARGET RULE: a labeled target line (e.g. "MM") is a price level, not an event.
  Record target price, x range, and whether and when price reached it
  (hit / overshoot / undershoot, in points).
- OUTCOME RULE: outcome = did the note's own claim happen? Notes about a failed
  breakout, failed wedge, reversal or trap are "success" when that
  failure/reversal actually happened. Never copy words like "failed" or
  "reversal" into outcome. Record breakout_dir and result separately, and set
  dir to the implied direction.
- DAY TYPE VS QUALITY RULE: the title gives the day type; notes like "weaker
  trend" or "okay swing buys" describe the quality of one phase. Encode them as
  modifiers (trend_quality) or expectations on that phase, never as a conflict
  with the day type. Record the day as phases where the title implies them.
- ADVICE NOTES RULE: notes like "TTR better to stop trading" or "not great buys
  but okay" are advice or setup-quality remarks (role: advice). Record the
  structure they refer to as separate rows and give outcome only to testable
  claims (expectations).
- SCALE MODIFIER RULE: "Minor" / "Micro" are scale modifiers, never base types.
  "micro double bottom" means two adjacent bars with equal lows; a structure
  spanning hours is a double_bottom with modifier minor.
- LABEL REUSE RULE: the same note text can mark different structures in one image
  (e.g. two "Minor HL DB" at two different lows). Anchor each note to what its
  arrow, box or dotted line touches, and link the structures instead of merging.
- LABELED LEVEL CHECK: when a chart labels a derived level (e.g. "Midpoint of
  day", "Open of Day"), recompute it from the measured day high/low (or open)
  and report the difference in points. If it disagrees by more than 2 points,
  flag the calibration as unreliable.
- NUMBERS RULE: re-measure every price the extractor quotes in its evidence
  against the chart's own extremes and axis. If it disagrees by more than
  2 points, correct it and say so.

## Reviewer-approved pattern glossary (use these readings first)

- ii (inside-inside): two consecutive inside bars; breakout-mode compression.
- OO (outside-outside): two consecutive outside bars; breakout mode, direction
  neutral until resolved.
- HST: most likely Head and Shoulders Top — test against geometry, unverified.
- MTR (Major Trend Reversal): strong trend-line break + test back + reversal
  signal; compounds (LL/HL/LH MTR) map here with the qualifier in raw_label.
- LL DB: lower-low double bottom (slight undercut); HL DB: higher-low bottom.
- Triangle (incl. expanding/nested/possible): range with >=3 pushes; breakout
  imminent, direction ~50/50 unless resolved on-chart.
- TTR: tight trading range at/after the open (10+ small bars, many reversals).
- Traps: failed breakouts that reverse (bear trap -> up, bull trap -> down).
- Bare "Bear Surprise" (no "major" on chart) is bear_surprise, not
  major_bear_surprise. Bare "Triangle" notes are triangle, not wedge.
- bull_trend_resumption: TR open -> breakout -> trend resumption regime.
- low_4: fourth-entry sell signal (High/Low 1-4 are standard Brooks entries).
- measuring_gap: breakout gap projecting the next leg (with an MM marker).

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
