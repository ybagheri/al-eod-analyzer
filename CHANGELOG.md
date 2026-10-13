# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

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

## [0.1.0] — TBD (Phase 0 release, pending gate + first commit)
