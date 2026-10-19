
## ADR-012 - Master re-plan v2.6: tiered labels, market-data-first, validator-gated writes (2026-10-19, accepted)

- Context: the 2026-10-19 wave finished R-FINISH (extraction_queue 244/244
  filled, 0 pending, 162 batch-1 labels, 0 quarantines, pytest 166 green),
  but the roadmap to Phases 6-12 was unworkable: the old plan implied
  vision-labeling all 1678 unique charts by file exchange (~800+ agent
  turns; P1), market data (Phase 5b) was not started while being the
  critical path (P2), axis/time ambiguity was unresolved (P3), dataset
  size was never tied to statistical need (P12/P13), and several process
  failures (hand-written JSON, BOM, copy-slip, stale-prompt overwrite)
  kept recurring (P5). The user supplied a master re-plan prompt (v2.6,
  now saved verbatim as `docs/PLAN_V2.md`, SHA-256 in
  `docs/PLAN_V2.sha256`). This ADR records the adoption and the decisions
  that follow from it. `docs/MASTER_PROMPT.md` remains the reference for
  architecture/principles but is superseded by `docs/PLAN_V2.md` for
  phase order, dataset sizing and process.
- Decision (summary; normative text is PLAN_V2 itself):
  1. Images are ground truth for EVALUATION, not the product; the product
     is a deterministic engine on real M5 bars. Phase 5b (market data)
     jumps ahead of further extraction.
  2. Scope is data-driven and newest-first: coverage C comes from the
     broker feed (`US500` CFD and/or stitched futures contracts), N_cov
     decides Case A/B/C sizing (ADR-012 sizing table in PLAN_V2 §3), and
     the chronological split freezes the newest block as Gold-Test
     (`splits.test_start_date`; boundary never moves).
  3. Tiered labels: Bronze (title-map day_type + bronze sanity), Silver-Dev
     (vision, compact schema v3), Gold-Test (human-reviewed, frozen,
     newest block), Hard set (active learning, dev only). Label-only pool
     outside coverage. R-FINISH: in-progress work is finished (now
     complete); R-NEW: every NEW chart sent to vision must be inside
     coverage, newest block first. Charts used to design the
     taxonomy/prompt (the 33 originals + 38 calibration charts) are
     contaminated by image_id AND session date; contaminated dates never
     enter Gold-Test.
  4. Extraction v3: compact schema with `anchors` (bar-index hints),
     validator-gated `brooks write-response` (atomic, BOM-less, strict),
     dirty-tree guard, migration table `config/taxonomy_migrations.yaml`
     with quality: exact|lossy so future enum changes never invalidate
     stored labels; taxonomy v1.3 is frozen for bulk labeling (P6).
  5. Public-safety policy (P9): the repo stays PUBLIC (user decision;
     old checkpoint A retired). `scripts/public_safety_scan.py` scans the
     working tree and full git history; images, `data/`, market data,
     `config/local.yaml`, secrets, personal paths and >1 MB blobs must
     never be tracked; a flagged item is a USER CHECKPOINT.
  6. Process (P5, P8): `docs/STATUS.yaml` is the single source of status
     (synced to README/ROADMAP/HANDOFF by `scripts/sync_status.py` with a
     failing test); `scripts/backup.py` zips `artifacts/` before bulk
     steps; `python -m tasks check` gains a plan-compliance check
     (STATUS schema, one in_progress step, evidence files, Gold-Test
     frozen hash, public-safety, human-label history, `S<k>:` commit
     format); git hooks (`.githooks/`, `core.hooksPath`) and CI
     (`.github/workflows/gate.yml`) enforce the same gate; steps run on
     `step/S<k>-<name>` branches, merged to main only after user
     approval, tagged `S<k>-done`.
- Consequences: ROADMAP.md is rewritten to the S0..S13 table with the
  statuses at adoption (Phases 0-4 done; S0 just starting; S1..S13
  pending); no further chart labeling under the old workflow (R-NEW
  governs everything); similarity gate (S3) decides evaluation tolerance
  (GO-FINE / GO-STRUCTURAL / STOP); docs stale text is fixed in S0; any
  deviation from PLAN_V2 requires an ADR and explicit user approval.