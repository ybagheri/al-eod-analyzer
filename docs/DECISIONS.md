
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

## ADR-013 - Legacy-id migration decisions (R-FINISH 8b, 2026-10-20, accepted)

- Context: after the R-FINISH conversion pass (243/244 queue responses
  mapped, 0 quarantines), stored labels still carried legacy taxonomy ids
  (bull_channel, trending_trading_range, reversal_day,
  small_pullback_bull/bear_trend_from_open as day types; low_2_top,
  wedge_bull_channel, triple_top, parabolic_wedge, spike_and_channel and
  day-type ids used as events inside `events`). A first migration table
  demoted these to `other`/`null` + bare needs_review, which loses
  attributes. The user ruled on every mapping (decisions verbatim below).
  Taxonomy stays v1.3: no new event ids, no version bump; only a
  day-type enum re-admission (`bull_channel`), a day-level modifier list,
  a session-open-provenance field and an enumerated
  `needs_review_reason` are added (schema-additive, see the ADR).
- Decisions:
  1. `bull_channel` (day type) is NOT renamed by id. Mapping is decided by
     the on-chart qualifier in the title/note text: "tight"/"small
     pullback" -> `small_pullback_bull_trend`; "broad" ->
     `broad_bull_channel`; bare "channel" -> `bull_channel` stays canonical
     with width=unspecified. `bull_trending_trading_range` is a separate
     day-type symbol still; do not merge it with `broad_bull_channel`.
  2. Dropping "from_open" from an id is allowed ONLY if the information is
     kept: new field `starts_at_session_open` (true/false/unknown) plus
     `starts_at_session_open_source` (title|note|marker|none). Evidence
     must come from the title/note wording or a session-start marker
     (dotted vertical line / date label) directly before the first bar of
     the move; the id itself is NOT evidence and the first visible bar is
     NOT the session open (prior-session bars may be visible). Without
     image evidence: unknown + needs_review (reason missing_evidence).
  3. Compound legacy ids map structurally, never blindly to null:
     `low_2_top` -> `l2` + modifier `at_top` (+ expectation recorded);
     `wedge_bull_channel` -> event `channel` + modifier `with_wedges`
     (width qualifier stays a modifier; none -> width unspecified);
     `triple_top` -> `double_top` + touches=3 (alternative reading
     `range_resistance` kept in review); `parabolic_wedge` -> `wedge` +
     modifier `parabolic` + `at_top`/`at_bottom` implied by direction
     (title first, then dotted-line slope; undecided -> needs_review
     reason ambiguous_direction); `spike_and_channel` -> split into two
     phase rows (`spike` + `channel`, linked, direction from the move)
     when the title evidences it, else needs_review (missing_evidence).
     Remaining unmappable legacy ids go to the S5 review pass as
     `label: null` + `raw_label` + an enumerated
     `needs_review_reason` (never a bare null).
- Conditions common to every lossy rule (hard guarantees):
  - `raw_label` is always kept verbatim.
  - Every migrated row records `mapped_from` (old id) and `rule_id`
    (rule name in `config/taxonomy_migrations.yaml`) and emits a log line.
  - No rule may change `direction` or `outcome` of a row (verified by
    charts-own-image tests).
  - Each rule has a test against the stored label of the chart(s) it came
    from (tests/integration/test_migration_rules.py).
  - The dry run (12 charts, migration replay on stored labels, run on a
    branch/copy after checkpoint commit + backup) reports: rows per
    chart, remapped count by rule_id, needs_review count by reason,
    attributes lost (must be 0) and any row whose direction or outcome
    changed (must be empty).
- Consequences: `config/taxonomy_migrations.yaml` gains handler-backed
  rules (`taxonomy_migrations` + rule_id); loader emits `mapped_from`,
  `rule_id` and `needs_review_reason`; `scripts/migration_dryrun.py`
  produces `artifacts/migration_dryrun.json` on request.


## ADR-014 - Broker time rule + similarity gate outcome (S3, Phase 5b, 2026-11-01, accepted)

- Context: US500 M5 CSV exported from MT5 lives in data/market/raw/rates_US500_M5.csv
  (2020-07-22 16:00 -> 2026-10-23 23:50, 394,817 rows, 1,619 server days). Phase 5b
  needs the server->exchange-time offset to (a) align RTH sessions for coverage
  counting and (b) run the similarity gate that sets the evaluation tolerance.
- Empirical derivation (scripts/empirical_broker_offset.py): the 5-min bar with the
  highest tick volume on each day aligns with 09:30 ET under server = ET + 7 h
  (best fixed offset -7.0 h; both DST and non-DST regimes agree; 23.8% exact,
  27.0% within 5 min, median error 10 min across 1,619 days). Equivalently the
  broker server clock follows US DST: UTC+2 in standard time, UTC+3 in daylight.
  Stored in config/broker_time.yaml (symbol_rules.US500 and SP500Z6).
- Decision: adopt server = ET + 7 h (US DST) as the broker time rule. coverage-probe
  uses DST-aware offsets (-2 h standard / -3 h daylight, since it treats server
  timestamps as UTC before converting to ET). n_cov = 1,209 complete RTH sessions
  (US500, DST-aware).
- Similarity gate (scripts/similarity_gate.py): run on 9 labels with bar-index
  anchors, 7 valid against real bars. Direction agreement 85.7% (6/7), median
  |bar-index error| 0 bars. Gate decision: GO-STRUCTURAL (agreement 75-90%,
  median error <= 3). Consequence: eval.tolerance_bars = 5 in config/default.yaml;
  evaluation uses tolerance ±5 bars and "present within window" logic only.
  Not STOP -> no USER CHECKPOINT C triggered.
