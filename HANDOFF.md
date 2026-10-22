# HANDOFF
_Last updated: 2026-10-22 by Muse Spark (opencode) - S2 batch-3 prep: batch-3 entries in axis_marker_registry.json (44b right-edge next_session semantics, 519/554a no-marker), scripts/check_axis_markers.py next_session/null handling, tests/fixtures/batch3 + BATCH3_HANDOFF.md git-ignored (image-derived market data), docs/evidence/S2.md batch-3 status section; batch-3 reviewer v3 payloads APPLIED (13/13 calibration payloads; scope_ok+alias normalizations logged in S2.md; 2 more golden fixtures frozen; pytest 276; user spot-check pending before tag).
<!-- previous: 2026-10-19 wave-2 fill-out complete (extraction_queue 244/244, 162 labels) -->

<!-- STATUS:BEGIN (generated from docs/STATUS.yaml; do not edit) -->

Plan of record: docs/PLAN_V2.md (sha256 fd3cd030dd71…, method vv2.6)
Current step: S2; STATUS.yaml updated: 2026-10-22
Last gate: green - ruff ok / format ok / mypy --strict ok / pytest green (273 collected) / coverage ~91%
Counts: queue pairs 244/245, labels 243, quarantined 0, gold 32, gold open items 1, calibration sample 38

<!-- STATUS:END -->

## 1. Project in one paragraph

al-eod-analyzer extracts Brooks-style structure from EOD review charts (ES M5
screenshots, batch of 2042 files in `data/raw_batch1/`), attaches it to real M5
market bars from the user's broker (Phase 5b), distils it into a tiered label
set (Bronze/Silver-Dev/Gold-Test), and reproduces the reading with a
deterministic streaming engine (Python reference + MQL5 port). Plan of record:
`docs/PLAN_V2.md` (master re-plan v2.6, ADR-012).

## 2. Current status

- Current step: S2 next (S0 done: `docs/evidence/S0.md`; S1 done: `docs/evidence/S1.md`) — see `docs/STATUS.yaml`
- Plan of record: docs/PLAN_V2.md (sha256 fd3cd030dd717d4c…, method v2.6, ADR-012); `docs/MASTER_PROMPT.md` superseded for phase order/sizing/process
- Phase status: predecessor phases 0-4 done; wave-2 fill-out done (queue 244/244, 162 labels); S0 done (status sync, public-safety scanner+history scan: 1 finding ACCEPTED by user, backups, hooks/CI plan-compliance); S1 done (core deps typer/pydantic/PyYAML/Pillow, extras restructured, wheelhouse offline-install proven in a fresh clone, engine stdlib-only guard)
- Last green quality gate: 2026-10-19 (ruff ✓ / format ✓ / mypy --strict ✓ / pytest green, 180 collected / coverage 92.38% ≥85)

## 3. What was done in this session

- Inventoried `data/`: 5 pilot images (`S&P500_Emini_M5_2022_07_29` … `2022_08_09`).
- Confirmed env: Python 3.14.8, no `git`, no `make`, no Tesseract, no API keys.
- Created skeleton: `pyproject.toml`, `src/brooks_lab/...`, `tests/test_smoke.py`,
  `tasks.py`, `Makefile`, configs, dotfiles, living docs, `mql5/` + `artifacts/` stubs.
- `docs/MASTER_PROMPT.md` already present and matching; kept as-is.
- Built `.venv`, installed package (`--no-deps`) + gate-relevant deps; fixed typer 0.27
  group `--version` (needs `invoke_without_command=True`) and ruff E501 in `tasks.py`.
- Gate GREEN 2026-10-11: ruff ✓, ruff format ✓ (18 files), mypy --strict ✓ (7 files),
  pytest 5 passed, coverage 100% (≥85 required).
- 2026-10-12: user installed Git 2.49.0; repo-local identity set from SSH-authenticated
  GitHub user (ybagheri / noreply email); remote switched to
  `git@github.com:ybagheri/al-eod-analyzer.git`; committed 4338faa (31 files, +1036)
  and pushed (new branch main → origin/main); images/venv confirmed excluded from index.
- Phase 1 implemented: domain `imaging` (ImageRecord/Manifest/StrEnum/parser) + `Clock`;
  infra `PillowProber` (sha256, sha1-id, PIL-only dHash), settings loader, axis hook;
  app `ImageIngestionService` (idempotent atomic manifest write) + stats;
  `brooks ingest` + `brooks manifest-stats` CLI; HTML contact sheet.
- Real run: 5/5 ok, all 1280x720 JPEG, dates 2022-07-29…2022-08-09, 7 missing dates
  (mostly weekends), 0 duplicates/corrupt/tiny; manifest + stats committed, sheet local.
- Fixes during Phase 1: pydantic `date`-field shadowing bug; typer-0.27 `--version`;
  ruff-0.17 rules (StrEnum, datetime.UTC, B008-ignore for typer idiom, RUF001);
  Pillow-12 `Resampling.BILINEAR` + `tobytes()` (getdata deprecated); added types-PyYAML.
- Phase 2 implemented: domain `labels` (DayLabel/EventLabel/ChartTime/ExtractionMeta,
  schema v1, unmapped→raw_label+review-queue invariant, migrate stub); frozen
  `config/taxonomy.yaml` v1 (14 day types, 38 events, synonyms); `Taxonomy` loader +
  normaliser; `build_review_queue` with normalised difflib suggestions;
  `brooks schema-export`; `docs/LABEL_SCHEMA.md` + `docs/GLOSSARY.md` draft (proposed
  numeric definitions, classes); ADR-004 (taxonomy freeze + PT axis time).
- Fixes during Phase 2: pydantic field/type name shadowing (same `date` lesson);
  normalise_wording moved to domain (layering); suggestions match normalised forms.
- Phase 3 implemented: `VisionClient` port + file/fake/anthropic clients;
  `ExtractionPromptBuilder` (config/prompts/extract_v1.md + taxonomy + schema);
  `ExtractionService` (resumable, retried with backoff, strict validation, quarantine,
  image_id check, date-mismatch warnings); `brooks extract` + `brooks extract-status`.
- Pilot (agent as file-exchange reader, ADR-005): 5/5 labeled, valid_rate 1.00,
  0 quarantined; day types {spike_and_channel_bull:1, trading_range:2,
  trend_reversal_to_bear:2}; 35 events (10 wedge, 3 major_bear_surprise, 8 unmapped);
  mean conf day 0.84 / events 0.64. Review queue: Triangle, HST, LL MTR,
  Bar 41 Midday Trend Reversal, Expanding Triangles, HL-tight-channel, LL-minor.
- ENV INCIDENT 2026-10-12 ~14:51: a non-editable `pip install file:///E:/al-eod-analyzer`
  (user confirmed: accidental run in repo path) overwrote the editable install with a
  stale site-packages copy; coverage silently measured 0% while tests passed. Diagnosed
  via `brooks_lab.__file__` + dist-info `direct_url.json`; fixed by uninstall + reinstall
  editable (`--no-build-isolation` after adding setuptools/wheel); regression guard
  `test_package_resolves_to_repo_src` added. No data was harmed (labels re-validated).
- DATA INCIDENT 2026-10-12 (agent fault): ran `brooks extract` after the CLI default
  prompt moved v1→v2, so resume did not skip and 33 labels were overwritten from stale
  queue responses (review work at risk). Recovered by re-applying corrections (history
  kept the junk intermediate revs — truthful chain). Guard added: extract skips labels
  with history unless `--clobber-reviewed` (+ test). Hypothesis (unverified): E: drive
  may be cloud-synced (also explains a transient stale read); user to confirm.
- Phase 4 tooling implemented: `ReviewService` (apply corrections with history archive +
  human-source marking, gold registry `artifacts/gold_set.json`, label stats,
  deterministic stratified sampling); review HTML pages (image left, label right,
  low-confidence first) + index; `brooks review-queue` (pages + gap report + stats)
  and `brooks review-apply` CLI. Fixed pydantic serializer warnings in apply path.
- Taxonomy v1.1 implemented (user-approved 2026-10-12): 8 new EventKinds, normaliser
  strips dots/parens, 40+ new synonyms, ADR-006; remapped 24/33 labels via new
  ReviewService.remap_events (history archived, touched events source=human,
  re-run idempotent) + one-off scripts/remap_taxonomy_v11.py; review queue
  45→19 items (all per keep-list/deferred); "Measuring Gaps" plural also demoted
  (agent judgment, reversible, flagged); HHDT resolved as Higher-High→double_top.
- Review rounds 2-3 applied (user specs 2026-10-12): 7 reworks round 2 (08-18 wedge identity,
  09-12 x_px table, 08-08 bare surprise + merged DT/HST, 08-09 HL split, 04-04 phases,
  08-16 10-row + date null, 08-26 advice split + veto + date null) + 10401c70 day-split
  note + 08-03 bare-surprise fix + 7 gold marks; 8 reworks round 3 (07-07 context split,
  08-15 regime change, 08-29 end-fix, 08-05 13-row split, 08-25 day change, 08-22 16-row,
  09-09 Low-4 canonical, 08-12 veto accepted). New ids: bear_surprise, trend_line,
  low_4, measuring_gap, bull_trend_resumption (taxonomy v1.2, ADR-008/009).
- Bulk gold 2026-10-12: all 25 HIGH-reviewed labels marked gold (7 LOW already gold);
  gold set 32/33 (only 10401c705b30 reviewed-not-approved). Phase 4 DoD met.
- Phase 5a start (user-directed 2026-10-12, dataset expansion): user moved a NEW batch of
  2044 files into `data/raw_batch1/` (same ES/M5 source, dates 2018-11-18..2026-10-14).
  Filename layout `SP500-Emini-M5-<Title>_YYYY_MM_DD.{jpg,png}` embeds the source
  author's hand-written day reading in `<Title>` (provisional free labels, ADR-010);
  one file has no date (`...nested-wedge-and-double-top-in-trading-range.png`).
  Original 33 gold images are NO LONGER in `data/` (moved away with the batch);
  gold JSON labels/history remain intact; batch1 includes the same source days
  (detach/reattach via date planned for Phase 5b market data). `data/raw_batch*/`
  added to .gitignore so images never enter the repo.
- Batch-1 ingest: 2 files deleted on user instruction (corrupt jpg 2023-07-10
  HL-DB..., tiny png 2026-10-14 Min-Climactic...); re-ingested 2042 images
  -> ok=1678, sha/phash-duplicates=364 (kept as alias rows in manifest).
  Artifacts: `artifacts/manifest_batch1.json`, `artifacts/ingestion_stats_batch1.json`.
- Title mapping (ADR-010): `src/brooks_lab/domain/title_taxonomy.py` (regex rule
  tables, deterministic) + `brooks title-map` CLI -> `artifacts/title_map_batch1.json`.
  Coverage 1820/2042 day-type (89%), 184 unique unmapped titles (mostly event-only,
  e.g. Bull-Trap-Then-Wedge-Bottom); head distribution: trading_range-family 596,
  bull_trend_from_open 315, bear_trend_from_open 213, small_pullback_bull 199,
  channels 341, trending_TR 102, reversal-family 139, spike_and_channel 60, resumption 37.
- Tests +35 (test_title_taxonomy.py) -> pytest 159 passed; gate GREEN
  (ruff / format 53 files / mypy --strict 22 files / coverage 92.33%).
- Calibration wave 0 (2026-10-12, commit 1f19db2): `scripts/extract_sample.py` builds a
  deterministic stratified sample (largest 12 title day-type strata, 1 each, spread
  across vintages -> `artifacts/calibration_sample.{txt,json}`) and runs the file-exchange
  extraction restricted to it (12 request+response pairs in `artifacts/extraction_queue`,
  labels -> `artifacts/labels/`, report -> `artifacts/calibration_report.json`).
  Result: 12/12 labeled; **vision-vs-title-map day_type agreement 8/12 (0.667)**.
  All 4 disagreements are filename-title vs on-chart blue title bar conflicts
  (a4bbf4c605c5 filename says BULL, chart title says BEAR; 29bdc49c41ad / dfc0ce0cc967 /
  08bc255b6b87 filename phrasing coarse) - in every case the vision pick follows the
  on-chart title and is the more precise reading; on-chart title outranks filename.
  Schema rule learned: event id `trading_range` does NOT exist - day-part ranges must be
  `trading_range_begin` + `trading_range_end` pairs (5 responses fixed post-quarantine).
   All 12 calibration images are plain-vision labels (source=vision), NOT gold.
- Calibration wave 1 (2026-10-17): extended `scripts/extract_sample.py --build-sample`
  to append-mode (round-robin remaining strata + unmapped/undated/weekend, no re-pick);
  built + vision-labeled 28 more images (spond total 40/2042 sampled). Result: 40/40
  labeled, **vision-vs-title day_type agreement 32/39 comparable (0.821)**; only
  calibration failures were 2 schema fixes (trading_range→begin/end pair,
  bull_trap→failed_breakout), 0 quarantines remain. Semantics learned and recorded:
  traps normalize to `failed_breakout` (raw kept), `mm`→`measured_move`,
  ii/ioi/oo aliases→inside_inside/outside_outside; day-part ranges always
  begin/end pairs. Disagreement set (7, all deliberate per on-chart title):
  29bdc49c41ad trending_TR, fe14a3fe7fe0 trading_range vs broad_bull_channel
  filename, c2ac5b23a509 trending_TR vs broad_bear_channel, c9dd83a405da
  reversal-to-bull vs bull_from_open, a4bbf4c605c5 small_pullback_bear vs bull,
  08bc255b6b87 TR, dfc0ce0cc967 reversal_to_bear. Special-case rows: acbf9694a538
  = EURUSD daily chart (scope anomaly, image_id kept, date null, times `00:00`);
  2adc4cca712d = axis-less course slide (times `00:00`); 4e96fb6e09ac prints
  ET+12 hrs axis (09:00-15:00 style) but recorded on the PT model like wave 0.
  All 40 wave-0+1 labels are plain vision (not gold).
- User calibration decisions (2026-10-17): approved vision picks on the 7
  title-conflict charts (fe14a3fe7fe0 trading_range, c2ac5b23a509 trending_TR,
  c9dd83a405da reversal_to_bull; + a4bbf4c605c5, 29bdc49c41ad, 08bc255b6b87,
  dfc0ce0cc967 listed for review) — on-chart-title precedence rule upheld.
  acbf9694a538 (EURUSD daily) and 2adc4cca712d (axis-less course slide) REMOVED
  from the sample (labels + queue pairs + sample entries deleted, commit b570174;
  report regenerated: 38 sampled, agreement 30/37 = 0.811).
- Review-pages dedup fix (2026-10-17, user-reported): view pages built from
  `manifest_batch1` listed the same chart twice when a hash-duplicate alias row
  shared its image_id (9 charts; e.g. fe14a3fe7fe0 shown for 2023-02-10 AND
  2023-02-13). `load_labels_for_manifest` now loads one label per unique
  image_id (first row wins); new unit test; review CLI output verified
  45 unique entries (40 calibration + 5 pilot ids whose exact image recurs in
  batch1); `artifacts/review*/` is git-ignored. Gate GREEN (pytest 160).
- Round-4 full review applied (2026-10-17, user read ALL 43 review pages; ok =
  whole page approved, inline note = that item only): 6 corrections via
  review-apply (rev1 each, reviewer ybagheri): e8ce92071fd7 + 5a9a1aef78cc +
  ac0332f48144 -> day_type trend_reversal_to_bull; e0d28242bd89 ->
  trend_reversal_to_bear (reversal-day maps to direction-specific reversal);
  08bc255b6b87 "Bull Reversal" -> major_trend_reversal + broken blue line
  re-labelled wedge trendline; 97f1ff2438fc STC start_time 06:45 (red-box
  markers precede 07:00, verified on chart). All other 37 pages approved
  unchanged. Corrections files kept in artifacts/corrections_round4/.
- Round-5 taxonomy v1.3 applied (2026-10-17, user approved tables A/B/C +
  extra): enum/config/title-rules/prompt-v2 updated; 10 labels remapped via
  review-apply corrections_v13 (6 TTR->bear incl. 7cc6cf98f425/29bdc/b0e7/
  c2ac/cf677/e092; 61527045af90->trend_reversal_to_bear;
  a9d707ed92f6->trend_reversal_to_bull; 10401c705b30 + 60c97519d0a5 ->
  trading_range_bear_breakout); mechanical legacy-id pre-patch needed because
  old stored ids became invalid post-enum-change (8 files); title map
  regenerated (1768/2042); calibration report regenerated (agreement 0.706,
  34 comparable — not comparable pre/post change); review pages rebuilt
  (labels=43, unmapped=10); ADR-011 in docs/DECISIONS.md; tests updated
  (v1.3 coverage, bare-reversal rule, title taxonomy params). Gate GREEN
  (160 tests, 92.38%).
- Wave-2 regeneration recovery (2026-10-18): 98 uncommitted extraction_queue
  response files lost to a tooling accident; 71 tracked files restored via
  `git checkout -- artifacts`, 15 restored verbatim from retained copies, the
  remaining 98 re-authored by chart re-inspection (2 images per session) under
  taxonomy v1.3; all 169 queue pairs non-empty and JSON-valid; JSON-scrub
  pass removed stray keys from 92 files; strict responses use BOM-less UTF-8
  writes (PS 5.1 `Set-Content -Encoding UTF8` BOM bug avoided). Gate run:
  labeled=0 skipped=38 pending=0 failed=0; day_type agreement 0.706 (34
  comparable), report + sample regenerated. Wave-2 queue artifacts are
  agent-visible but still uncommitted as a bulk commit. Gate GREEN
  (pytest 166).
- Wave-2 bulk labeling + label-conversion (2026-10-18/19): the ever-growing
  `brooks extract` runs against `--limit 120` taught the schema's strict enum
  rules (compound labels like `wedge_bear_flag` invalid -> enum event ids,
  `trading_range` must be begin/end pairs, `bar_index_hint` int-only, outcome
  in success|fail|partial|unclear, `bear_trend_resumption` day_type invalid
  -> direction-specific types; `bull_trend_resumption` stays valid). Deep
  recursive normalizer scripts (Temp/opencode deep_fix_wave2) repaired
  94+20 existing responses; quarantines then went to 0. Routine labeling of
  newly-created wave-2 requests to 24 filled pairs (00de/03f3/0d72 from the
  prior wave + 17 this wave: 10d978fbbd04, 13a75f921985, 15254ec5c819,
  189730200a33, 1978856221c0, 19ae778ff791, 1e45d0c9fa4f, 1e5d15df5c69,
  227e5ba88949, 2451e063322e, 24820909e570, 26b530d78455, 271ca2f5ad58,
  336488e1219f, 3b173e9384e3, 3e133be4f453, 03272b80a6f8). Copy-slip fix:
  `03272b80a6f8.response.json` contained 00de25dd4e5f's content (wrong
  image_id/from another day) -> quarantined as image_id mismatch; real chart
  (Bull Trend From Open Then TR, 2025-08-14) re-authored, quarantine 0.
  Extract gate: quarantined=0, +20 labels converted (49 batch-1 labels live);
  calibration sample labeled=0 skipped=38 failed=0, agreement 0.706 (34
  comparable); pytest 166 passed. 55 wave-2 request files still have no
  response (extract converts only ids within the `--limit 120` scan window).
- Wave-2 fill-out COMPLETE (2026-10-19, this session): all remaining 38
  request-only files answered by chart re-inspection, 2 images per turn
  (c687a6d8722f … fc17e0fa2472; full id list in the wave commit) — extraction_queue
  now 244 filled pairs, 0 pending. Enum lessons hit again: event
  `trading_range` -> `tight_trading_range`, `low_2` -> `l2`,
  day_type `trend_reversal_to_bear_attempt` -> `trend_reversal_to_bear`
  (32 responses normalized post-quarantine, then 99eba23dad8a straggler);
  after fixes: extract scanned=120 labeled=36 skipped=84 pending=0
  quarantined=1 -> 0, valid_rate 1.00, **162 batch-1 labels live**, failed dir
  empty. Calibration sample agreement 0.706 (34 comparable, unchanged);
  pytest 166 passed. Gate GREEN -> feat commit + push.

## 4. Decisions made (link to ADR numbers)

- ADR-011: taxonomy v1.3 (2026-10-17, user-approved round-5): +bull/bear_trending_
  trading_range, +trading_range_{bull,bear}_breakout; -reversal_day,
  -trending_trading_range; 10 labels remapped (all 6 TTR bear-trending);
  title coverage 1820 -> 1768/2042 (90 generic titles -> vision at scale).

- ADR-001: tech stack (PEP 621, typer/pydantic, ruff/mypy/pytest, tasks.py gate) — see `docs/DECISIONS.md`.
- ADR-004: taxonomy v1 frozen; Pacific axis time; unmapped→review-queue design.
- ADR-005: pilot extraction by the coding agent via file exchange (first-pass, not ground truth).
- ADR-006: taxonomy v1.1 (8 new ids, trap mappings, HHDT resolution).
- ADR-007: reviewer-driven schema extension (modifiers/role/explicit/placement/x_px, optional date) + claim-based outcome + result-direction + prompt v2 + feed-timezone theory.
- ADR-008: round-2 review (roles CONTEXT/ADVICE/BAR_PATTERN, bare bear_surprise/trend_line ids, 13 prompt rules, gold-aware extract guard).
- ADR-009: round-3 review (`bull_trend_resumption` day type, `low_4`/`measuring_gap` ids, outcome-word mapping observed→success etc.).
- ADR-010: batch-1 filename titles = provisional human day_type/event hints via `title_taxonomy.py` + `brooks title-map` (no taxonomy change; never gold; artifacts `manifest_batch1`/`title_map_batch1` separate).

## 5. Next actions (ordered, the very next step first)

1. AGENT: bulk wave 2 — extraction_queue is now FULLY filled (244/244
   request/response pairs, 0 pending, 162 batch-1 labels converted, 0
   quarantines, gates GREEN 2026-10-19). Next step is broadening conversion:
   raise `--limit N` on `brooks extract` in chunks (or loop waves) to convert
   responses beyond the current 120-image scan window; keep the paired-batch
   workflow for any NEW requests the extract run creates.
2. USER: on gold registry — only open human-review item left is
   `10401c705b30` (mark gold yes/no); everything else approved through
   round-5 (2026-10-17).
3. Phase 5b (market data + session calendar) after bulk extraction is
   underway - includes resolving the PT-vs-ET axis question (BOTH styles
   exist: authored ET+12/ET+13 offset charts vs plain PT; wave-1
   4e96fb6e09ac prints ET+12 hrs) before any label->bar attach.

## 6. Open questions / blockers

- None blocking. Push works via user's `~/.ssh/id_ed25519` (tested OK as ybagheri).
- `make` absent on Windows → canonical gate is `python -m tasks check` (documented).
- No API keys, no Tesseract → file-exchange extraction (ADR-005); anthropic path untested live.
- April-pair + Sep-23 axes show 09:00–15:00 (vs PT-style 06:30–13:00): ET feed or cropped axis? DEFAULT: recorded as-shown with PT tz + note; Phase 5 must resolve against real bars before any label→bar attachment.
- User supplied glossary notes 2026-10-12 (OO, ii, TBTL, MTR, LLDB, traps, Triangle, TTR, HST, H1-H3/L1-L2) — folded into GLOSSARY.md; taxonomy v1.1 proposal pending approval (see chat).
- HH DT resolved by user as Higher-High → interim parent double_top (dedicated id deferred; HST stays parent-mapped per ADR-009).
- Feed-axis suspicion (some titles show 09:00–15:00 axes vs PT 06:30–13:00) still unresolved — Phase 5b must verify against real bars.
- Batch-1 filename anomalies for the Phase 5b calendar pass: 29 weekend-dated files (e.g. `2025_01_26`, `2026_03_22/29` Sundays) + 1 undated file (`nested-wedge-and-double-top-in-trading-range.png`) need date normalisation; 355 dates carry duplicate files (hash dedup handles).
- Original 33 gold images no longer on disk; gold labels/history intact (see §3 Phase 5a note).

## 7. Known issues / tech debt

- `mql5/` contains stubs only — expected until Phase 9.
- Full `.[dev]` install incomplete: numpy/pandas/opencv-python/pytesseract/pre-commit
  NOT installed (12–44 MB wheels timed out on slow net); gate-relevant set + ruff/mypy
  installed. Fresh-clone install still declares them in `pyproject.toml` — medium.
- Gate MUST run with `.venv` on PATH (global mypy lacks typer) — documented in §9.

## 8. Data & artifact state

- Images in data/: 33 (15 JPEG + 18 PNG) | Manifest entries: 33/33 (all ok)
- Labels extracted: 33/33 (valid_rate 1.00, 0 quarantined, 285 events, 48 unmapped/46 distinct — incl. reviewer-spec'd structure/day-part rows, 11 day types live) | Reviewed: 33/33 (25 HIGH + 8 LOW) | Gold set: 32/33 (10401c705b30 pending approval)
- Dates CONFIRMED by user 2026-10-12: 04-02 file = 03-31 session, 04-03 file = 04-01 session; 07-29 confirmed correct, 07-22 duplicate file DELETED (manifest/labels/queue cleaned, manifest regenerated 33/33).
- Date flags: 04-02→03-31 and 04-03→04-01 relabelled from title weekday (pipeline warnings fired correctly), both CONFIRMED by user; 07-22/07-29 duplicate resolved (07-29 kept, 07-22 deleted); April + Sep-23 axes run 09:00-15:00 (possible ET feed — Phase 5 must verify, see §6)
- PNG batch (08-01…09-23) has no readable time axis → event times null (15 of 29 new labels)
- Watermark note: Aug/Sep PNGs carry a "Persian_expert_trader" redistribution watermark (third-party, personal research use; same legal basis as data/README)
- Market data coverage: none (Phase 5b)
- Batch-1 dataset (data/raw_batch1/, git-ignored images): 2044 received -> 2042 usable (corrupt 2023-07-10 jpg + tiny 2026-10-14 png deleted) | ok=1678, hash-duplicates=364 | dates 2018-11-18..2026-10-14 | title day_type coverage 1768/2042 (89% -> 87% after v1.3; extra 90 titles resolve via vision)
- Calibration waves 0+1: 38 sampled (2 removed: EURUSD-daily anomaly + axis-less slide) | agreement 0.706 vs new-directional titles (0.811 pre-v1.3; not comparable) | 0 quarantines outstanding | labels NOT gold, all corrections human-applied (rev1-varies, 131 history revs)
- Color: vocabulary v1.3 — day_types 17, events 50 | round-5 review approved every page (ok=all, inline notes fixed)
- Calibration artifacts (git-tracked): artifacts/calibration_sample.{txt,json} (40 ids + strata meta), artifacts/calibration_report.json, scripts/extract_sample.py, 40+28 queue pairs (extraction_queue), 40 wave labels in artifacts/labels/
- Batch-1 extraction state (git-tracked): extraction_queue 244 filled
  request/response pairs (0 pending) | artifacts/labels: 162 batch-1 charts
  converted | last extract: quarantined=0, valid_rate 1.00, scanned=120 | wave-2
  commits: 2bd0c5e + 7e4e4e7 + this wave
- Batch-1 artifacts (git-tracked): artifacts/manifest_batch1.json (~1MB), artifacts/ingestion_stats_batch1.json, artifacts/title_map_batch1.json
- Playbook version: none (Phase 8)

## 9. How to run / verify (copy-paste commands)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
brooks --version
python -m tasks check
brooks ingest
brooks manifest-stats
brooks extract --provider file --model-id muse-spark-opencode
brooks extract-status
brooks title-map --manifest artifacts/manifest_batch1.json --output artifacts/title_map_batch1.json
python scripts/extract_sample.py --build-sample 12 --sample-file artifacts/calibration_sample.txt
python scripts/extract_sample.py --sample-file artifacts/calibration_sample.txt
```

## 10. Metrics snapshot (real numbers only; "NOT RUN" if unknown)

- Extraction: NOT RUN
- Engine vs labels (dev/test): NOT RUN
- Parity Python↔MQL5: NOT RUN

## 11. Rules reminder for the next model

- Read README, ROADMAP, DECISIONS first. Do not skip phases. Update this file before each commit.
