# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Wave-2 bulk labeling wave: 24 wave-2 request/response pairs filled (routine
  agent labeling under the strict v1.3 enums; compound labels forbidden,
  trading_range always begin/end pairs, int bar_index_hint, outcome enum
  success|fail|partial|unclear); 20 new labels converted -> 49 batch-1 labels
  live; 55 wave-2 request files still pending responses.
- Wave-2 regeneration recovery: all 169 batch-1 extraction_queue request+response
  pairs restored/refilled and JSON-valid under taxonomy v1.3 (71 tracked restored
  via git checkout, 15 restored verbatim, 98 re-authored by chart re-inspection at
  2 images per session); JSON-scrub pass removed stray keys from 92 responses;
  strict BOM-less UTF-8 write pattern documented to avoid the PS 5.1
  `Set-Content -Encoding UTF8` BOM bug. Calibration gate: labeled=0 skipped=38
  pending=0 failed=0, day_type agreement 0.706 (34 comparable); commit 2bd0c5e.
- Taxonomy v1.3 (ADR-011, user-approved): `bull/bear_trending_trading_range`
  + `trading_range_{bull,bear}_breakout` added; generic `trending_trading_range`
  and `reversal_day` removed from the vocabulary; title rules and prompt v2
  updated; 10 labels remapped (6 TTR -> bear_trending_trading_range,
  61527045af90 -> trend_reversal_to_bear, a9d707ed92f6 -> trend_reversal_to_bull,
  10401c705b30 + 60c97519d0a5 -> trading_range_bear_breakout). Title-map
  coverage 1768/2042 (generic titles resolve via vision at wave scale).
- Calibration round-4 review (all 43 review pages read through): 6 labels
  corrected via `brooks review-apply` (reviewer ybagheri, history archived):
  4 day_type retypes (e8ce92071fd7/5a9a1aef78cc/ac0332f48144 -> trend_reversal_
  to_bull, e0d28242bd89 -> trend_reversal_to_bear), 08bc255b6b87 Bull Reversal
  -> major_trend_reversal + blue-line break relabelled wedge, 97f1ff2438fc STC
  start 06:45 (red boxes precede 07:00).

### Fixed

- Hash-duplicate charts no longer appear twice in the review index:
  `load_labels_for_manifest` now loads one label per unique `image_id`
  (alias `duplicate_of` rows in `manifest_batch1` no longer duplicate entries);
  `artifacts/review*/` all local-only via .gitignore.

### Added

- Phase 5a dataset expansion: batch of 2042 usable ES/M5 charts ingested from
  `data/raw_batch1/` (2018-11-18..2026-10-14; ok=1678, duplicates=364; corrupt +
  low-res files deleted). Filename titles mapped to provisional taxonomy ids by
  `title_taxonomy.py` + new `brooks title-map` command (`title_map_batch1.json`,
  89% day-type coverage, ADR-010); images stay git-ignored via `data/raw_batch*/`.
- Calibration wave 0: `scripts/extract_sample.py` (deterministic stratified
  sample) + 12 vision-extracted labels; vision day_type agrees with the filename
  title map on 8/12, with all misses traced to filename-vs-on-chart-title gaps
  (`artifacts/calibration_report.json`).
- Calibration wave 1: append-mode sample builder + 28 more vision-extracted
  labels (40 sampled total, 0 quarantines outstanding); day_type agreement vs
  title map 32/39 comparable (0.821); semantics recorded (traps ->
  `failed_breakout`, `mm` -> `measured_move`, ii/ioi/oo aliases, day-part
  ranges as begin/end pairs); special rows: EURUSD-daily scope anomaly,
  axis-less course slide, ET+12 hrs axis chart.

- Phase 0 skeleton: installable `brooks-lab` package, `brooks --version` CLI,
  `tasks.py`/`Makefile` quality gate, configs, living docs, `mql5/` stubs.
- Phase 1 ingestion: `ImageRecord`/`Manifest` schemas, `ImageIngestionService`
  (hash + perceptual-hash duplicates, corrupt/tiny flags, idempotent manifest),
  `brooks ingest` / `brooks manifest-stats` CLI, HTML contact sheet.
- Phase 2 taxonomy: frozen vocabulary v1, `DayLabel`/`EventLabel` schemas,
  synonym normaliser, unmapped-label review queue, `brooks schema-export`,
  `LABEL_SCHEMA.md` + `GLOSSARY.md` draft.
- Phase 3 extraction: `VisionClient` port (file-exchange, fake, anthropic),
  versioned prompt builder, resumable/retried/quarantining batch service,
  `brooks extract` / `brooks extract-status`, 5-image pilot labels (first-pass).
- Batch 2: 29 more ES/M5 charts labelled (34/34 total, 261 events, 0 quarantined);
  date corrections (04-02→03-31, 04-03→04-01, user-confirmed), 07-22/07-29
  duplicate resolved (07-29 kept, 07-22 file deleted → 33/33), ET-axis suspicion
  recorded for Phase 5.
- Phase 4 review workflow: `ReviewService` (corrections + history + gold registry),
  HTML review pages, `brooks review-queue` / `brooks review-apply`, label stats.
  Gold set pending user review (0/33).
- Review round 1: 10/33 labels corrected per reviewer specs (ADR-007 schema extension:
  modifiers/role/explicit/placement/x_px, optional date; prompt extract_v2 with 5
  reviewer rules; claim-based outcome + result-direction conventions); extract guard
  against clobbering reviewed labels (`--clobber-reviewed`).
- Taxonomy v1.1: 8 reviewer-approved pattern ids + 40 synonyms (ADR-006); 24/33
  labels remapped with history.
- Review round 2: 7 full reworks + 10401c70/08-03 fixes + 7 gold marks per reviewer
  specs; new roles (context/advice/bar_pattern), bare bear_surprise + trend_line ids
  (ADR-008); prompt v2 extended with 13 more reviewer rules + pattern glossary;
  extract also skips gold labels without --clobber-reviewed.
- Review round 3: 8 full reworks (07-07, 08-15 regime change, 08-29, 08-05, 08-25 day
  change, 08-22, 09-09 Low-4 canonical, 08-12 veto accepted); new ids low_4,
  measuring_gap + bull_trend_resumption day type (taxonomy v1.2, ADR-009).

## [0.1.0] — TBD (Phase 0 release, pending gate + first commit)
