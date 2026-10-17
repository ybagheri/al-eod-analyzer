# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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
