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

## [0.1.0] — TBD (Phase 0 release, pending gate + first commit)
