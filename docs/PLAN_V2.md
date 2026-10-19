# MASTER RE-PLAN PROMPT — al-eod-analyzer (v2.6 method)

> **v2.6 adds (after the previous agent's 2026-10-19 report, commit `2300fe7`):** R-FINISH is now mostly done (queue 244/244, 0 pending, 162 batch-1 labels), so S2 item 8 becomes *convert what is filled + audit the lossy enum rewrites*; further labeling under the old workflow is forbidden. **v2.5 adds (after re-checking the live repo/HANDOFF on 2026-10-19):** `docs/MASTER_PROMPT.md` precedence rule; contamination is judged by **session date** (the original 33 gold images are no longer on disk and their days reappear in batch-1 under different files); re-linking gold labels to batch-1 files (S4 item 7); all repo counts in this prompt are approximate and must be re-verified. **v2.4 adds:** two explicit rules about which charts get labeled: **R-FINISH** (finish the labeling work that is already started, whatever the dates) and **R-NEW** (any *new* chart sent to vision must come from the broker-data coverage window, newest-first). See §3, S2 item 8, S5 item 1b. **v2.3 adds:** the repository **stays PUBLIC by the user's decision** (educational project). The old "make the repo private" checkpoint A is **retired** and replaced by an automated, enforced *public-safety* policy (S0 item 3, §8.3). **v2.2 adds:** §0A (concrete, user-verified broker environment: Alpari MT5, symbols `US500` and futures `SP500Z6`, folder paths) and the matching changes in S3 (dual-source export, futures-contract stitching, per-source similarity gate). **v2.1 changes vs v2:** (1) scope is now **driven by the real data coverage of the user's broker feed** (a CFD feed that closely tracks ES futures, but probably only a few months of M5 history); work proceeds **newest-first, backward in time** as far as data exists; (2) sizing, splits and tiers are **adaptive** to coverage (§3); (3) a **go/no-go similarity gate** decides the evaluation tolerance (§5 S3); (4) a new **§8 Plan-compliance and enforcement** section makes deviations detectable and hard.

You are the next coding agent on the repository `al-eod-analyzer` (Python package `brooks_lab`, Windows, PowerShell, no `make`, `git` installed, repo-local SSH push works). The repo already has Phases 0–4 done and Phase 5a in progress. This prompt **re-plans the remaining work**, fixes known process problems, and tells you exactly what to build and in what order. Follow it literally. Where it conflicts with older docs, this prompt wins, and you record the change as ADR-012.

---

## 0. Communication and working rules

1. Talk to the user in **Persian**. Write all code, docs, ADRs, commit messages, and JSON in **English**.
2. Before doing anything, read in this order: `README.md`, `ROADMAP.md`, `HANDOFF.md`, `docs/MASTER_PROMPT.md` (the earlier master prompt: **superseded** by this prompt for phase order, dataset sizing and process; its architecture and principles still apply; on any conflict this prompt wins and ADR-012 records it), `docs/DECISIONS.md`, `docs/LABEL_SCHEMA.md`, `docs/GLOSSARY.md`, `config/taxonomy.yaml`, `config/default.yaml`. **Verify claims against the actual repo** (run `git log --oneline -20`, `git status`, `python -m tasks check`, `brooks extract-status`). The docs are known to be partly stale; trust the code and artifacts over prose.
3. Never skip the quality gate: `python -m tasks check` (ruff, ruff format, mypy --strict, pytest, coverage ≥ 85%). Run it with `.venv` on PATH. Gate must be green before every commit.
4. Commit small and often (at least once per completed step below). Update `HANDOFF.md` before every commit. Push after each commit.
5. Ask the user questions **only** at the explicit "USER CHECKPOINT" markers below (batch all questions for a checkpoint into one message, in Persian, with a recommended default for each). Between checkpoints, proceed autonomously.
6. Do not delete, move, or overwrite anything in `data/`, `artifacts/gold_set.json`, or any label that has `source=human` or is in the gold set. Never run `brooks extract` with `--clobber-reviewed`.
7. Environment facts you must respect: slow network (large wheels time out), no API keys, no Tesseract, GPU is a 2 GB MX 355 (do not plan local vision). Extraction by the agent via file exchange (ADR-005) remains the default vision path. **Do not assume any paid or online API is reachable.** The Anthropic client stays optional and untested-live.
8. Honest framing (keep it everywhere): the goal is to behave *similarly* to Brooks's reading, not to clone it. His labels are made with hindsight; the live engine emits **provisional** and **confirmed** labels. No profitability claims; every claim needs out-of-sample evidence with confidence intervals.
9. **Plan compliance:** this prompt is the plan of record. You may not change it, skip steps, reorder steps, relax a Definition of Done, or substitute your own approach without (a) an ADR and (b) the user's explicit approval in the chat. If something in the plan cannot be done, **stop and ask in Persian** instead of improvising. Follow §8 at all times.

---

## 0A. Verified environment facts (given by the user; verify by looking, do not assume)

- OS: Windows. Broker platform: **Alpari MetaTrader 5**.
  - Terminal: `<TERMINAL_PATH>\terminal64.exe (real path: config/local.yaml)`
  - **MT5 data folder:** `<MT5_DATA_FOLDER> (real path: config/local.yaml)`
  - Scripts go in `<data folder>\MQL5\Scripts`; exported CSV appears in `<data folder>\MQL5\Files`.
  - MetaEditor is expected next to `terminal64.exe` (`MetaEditor64.exe`); compile with `MetaEditor64.exe /compile:"<file.mq5>" /log:"<log>"`. If it is missing or fails, ask the user to open the script in MetaEditor and press F7.
- **Candidate symbols:**
  - `US500` — the broker's S&P 500 **CFD** (may have longer history; behavior near ES must be tested, not assumed).
  - `SP500Z6` — the broker's **futures contract** (S&P 500, month code Z = December, digit 6 = 2026; contract letters: H=Mar, M=Jun, U=Sep, Z=Dec). A single futures contract only has history for its listing life (a few months) and **expires around the third Friday of December 2026** (verify); after that, the symbol may become unavailable and a new contract (`SP500H7`) takes over. Therefore **export as early as possible and archive the raw CSV files; never rely on the terminal still holding the data later.**
  - There may be sibling contracts (e.g. `SP500U6`, `SP500M6`, `SP500H6`, `SP500Z5`) still visible or hidden. Discover them; do not guess names (see S3 step 1).
- Local paths live in `config/local.yaml` (**git-ignored**); commit only `config/local.example.yaml` with placeholders. Code reads paths from the local config, never from hard-coded literals.
- **Safety scope for MT5 access:** you may (a) write the read-only export script into `MQL5\Scripts`, (b) compile it, (c) read the CSV files it produces from `MQL5\Files` and copy them into the repo's `data/market/`. You must **not** place orders or write trading code in this step, change terminal/account settings, log in or out, or delete/modify any other file in the MT5 folders. The user runs the script inside MT5 (or you launch nothing).

---

## 1. Why we are re-planning (diagnosis)

Current state: 2042 batch-1 charts ingested (1678 unique, 364 hash-duplicates), 33 original charts reviewed (32 gold), about 49 batch-1 charts vision-labeled, 55 request files without response, taxonomy v1.3 (17 day types, 50 events). Metrics for extraction, engine, and parity are all "NOT RUN".

Problems found (each one must be fixed by the steps in this prompt):

| # | Problem | Consequence |
|---|---------|-------------|
| P1 | Plan is to vision-label all 1678 charts by file exchange, ~2 charts per agent turn | ~800+ turns; unrealistic; low marginal value |
| P2 | Market data (Phase 5b) is not started, yet it is the critical path; nothing can be evaluated without real bars | No engine, no metrics, no playbook |
| P3 | Axis/time ambiguity (PT 06:30–13:00 vs 09:00–15:00 vs ET+12/ET+13) unresolved | Label→bar attachment would be silently wrong |
| P4 | 29 weekend-dated files, 1 undated file, 355 dates with duplicate files | Wrong-date leakage, split leakage |
| P5 | Data-loss incidents: stale-prompt overwrite of 33 labels; 98 uncommitted response files lost; response copied into the wrong file (`image_id` mismatch); PowerShell BOM bug from hand-written JSON | Process is fragile |
| P6 | Taxonomy churned v1.0→v1.3 in about a week; enum changes invalidated stored ids and needed manual pre-patching | Re-labeling cost, non-comparable metrics |
| P7 | Vision-vs-title day_type agreement fell to 0.706 (34 comparable) after v1.3 and is not comparable to 0.811 before | No stable baseline |
| P8 | Docs drift: README and HANDOFF §1 say "Phase 0 only"; ROADMAP shows Phase 5 "not started" and a stale Phase 0 checkbox; HANDOFF §8 still describes 33 images | New agents get misled |
| P9 | Repo is **public** (user decision: it stays public) while README says it must be private; the project works with third-party copyrighted charts (some watermarked "Persian_expert_trader") and broker market data | A public repo is crawled by bots and scrapers regardless of human visitors, and git history is permanent: one accidental commit of images, broker data, local config or a secret is public forever. Needs an automated guard, not trust |
| P10 | `numpy/pandas/opencv/pytesseract/pre-commit` declared but not installed; opencv/pytesseract are unused | Fresh-clone install is broken or heavy |
| P11 | Scope anomalies exist (EURUSD daily chart, axis-less course slide) with no automatic filter | Pollutes statistics |
| P12 | Dataset grew from the original plan of ~100–200 images to 2042 without a sizing argument | Effort not tied to statistical need |
| P13 | The broker feed that resembles ES futures probably covers only the last few months, so most charts (2018–2025) cannot be attached to real bars | Dataset size and splits must be driven by **data coverage**, not by chart count |

---

## 2. New method in one page

**Principle: images are ground truth for evaluation, not the product.** The product is a deterministic engine running on real M5 bars. Therefore:

1. **Get real bars first** (Phase 5b before more extraction). The user's broker CFD feed is believed to track ES futures closely but to have limited history. Scope is **data-driven and newest-first**: find out exactly which sessions have valid M5 bars (the *coverage*), and work from the most recent session **backward in time** as far as coverage goes. If the user later obtains older data, the work extends backward without changing the frozen test block.
2. **Verify similarity instead of assuming it:** a cheap *anchor* test (chart-derived day direction, bar index of day high/low) against the real bars decides the evaluation tolerance (go/no-go gate in S3).
3. **Tier the labels** instead of labeling everything with vision. Only charts inside coverage receive event-level labels:
   - **Bronze** (day-level, almost free): title-map day_type for all covered charts, sanity-checked automatically against real bars.
   - **Silver-Dev** (event-level, vision, compact schema, validated): the older part of the covered charts.
   - **Gold-Test** (event-level, human-approved, frozen): the **newest block** of covered charts, random-stratified inside the block, never used for tuning.
   - **Hard set** (active learning): chosen where engine and bronze/silver disagree; dev only.
   - **Label-only pool** (charts outside coverage): not attached to bars. Already-started labeling work is finished (rule R-FINISH, §3); no *new* vision labeling outside coverage (rule R-NEW, §3).
4. **Run the engine on all covered days** (and on any extra ES-like M5 history the user can provide) to produce pattern statistics with n and confidence intervals. The playbook comes from engine-detected patterns and real-bar outcomes, validated against labels, not from Brooks's claims.
5. **Fix the process** (validator-gated writes, taxonomy migration table, status single-source, backups, enforcement in §8) before scaling up.

---

## 3. Dataset sizing and splits (adaptive; justify in ADR-012)

Wilson 95% interval half-widths for a proportion near 0.5: n=30 ≈ ±17 pp, n=50 ≈ ±13.5 pp, n=100 ≈ ±9.6 pp. Plan to these numbers and report them honestly.

**Definitions.** *Coverage* C = the set of regular-hours (RTH) sessions for which at least one candidate broker source (`US500` CFD or the stitched futures series) has complete, valid M5 bars (determined in S3; each session records which source it uses in `artifacts/market_source_map.json`). *N_cov* = number of unique, non-excluded charts whose resolved date is in C (determined in S4). Everything below depends on N_cov, so **do not label event-level charts before N_cov is known.**

| Case | N_cov | Gold-Test (newest block) | Silver-Dev | Hard set | Playbook status |
|------|-------|--------------------------|-----------|----------|-----------------|
| A | ≥ 400 | newest ~100 charts (≥ the newest ~25% of covered charted days, min 80) | up to 300 of the older covered charts | ~100 later, dev only | normal; "insufficient data" for rare kinds |
| B | 150–399 | newest ~60 charts (min 40) | **all** remaining covered charts | optional | exploratory; many kinds "insufficient" |
| C | < 150 | newest ~40 charts | all remaining covered charts | none | **exploratory only**; before S9 ask the user to extend coverage (CHECKPOINT) |

**Chronological split (replaces any fixed calendar boundary).** Test = the **newest** block, dev = everything older. Record `splits.test_start_date` in `config/default.yaml` when the test block is frozen. Group by calendar date: all files with the same date go to the same split. **The test boundary never moves**, even if older data is added later; newly added older months join **dev only**.

**Newest-first block order.** Process covered data in time blocks of about 3 calendar months, from the most recent backward. Label **Gold-Test first** (so it is frozen early, before any tuning), then Silver-Dev block by block going backward. After each block: attach, label, evaluate on dev.

**Bronze** = all covered, non-excluded charts (title-map day_type; ~13% unmapped titles get the day-only vision pass).

**Anchors-only audit:** all covered charts if N_cov ≤ 150, otherwise ~100 random covered charts, plus all anomaly files (weekend-dated, undated, axis-style outliers).

**Charts outside coverage (label-only pool) and the two labeling rules.** Keep their files and manifest rows with `in_coverage=false`.
- **Rule R-FINISH (complete what is started).** Work already started is finished, not abandoned, whatever the dates: (a) charts already labeled (the 33 original gold, the 38 calibration charts, and the batch-1 charts labeled so far — about 49 according to HANDOFF; these groups may overlap, so verify the real numbers with `brooks extract-status` and by counting `artifacts/labels/`) are kept and reviewed or completed as needed; (b) batch-1 request files that still have no response (55 per the 2026-10-18 HANDOFF; reported as 0 pending after the 2026-10-19 wave — verify) are completed, and filled-but-unconverted responses are converted, through the validator-gated path. Never re-extract a chart that already has a valid label.
- **Rule R-NEW (new charts only from coverage, newest-first).** Beyond that in-progress set, **no new chart is sent to vision labeling unless its resolved date is inside the broker-data coverage**, and new charts are picked newest block first (block order above). Do not pull out-of-coverage charts "to fill quotas": if coverage yields fewer charts than the Case targets, label what exists and report the shortfall.
- **Where finished charts go.** A chart finished under R-FINISH that is **outside** coverage cannot be used for engine evaluation or playbook statistics; it serves taxonomy/prompt calibration and as a human-reviewed example, and is **promoted into dev automatically** if coverage later extends back to its date. A chart finished under R-FINISH that is **inside** coverage joins the tier given by its date (test block → Gold-Test candidate; older → Silver-Dev). Exception: any chart that was used to design the taxonomy, write or tune the extraction prompt, or calibrate (the 33 originals and the 38 calibration charts) is **contaminated**; contamination is judged by `image_id` **and by session date**, because the original 33 gold images are no longer on disk and the same source days reappear in batch-1 under different files and hashes, so every chart of a contaminated date is treated as contaminated and must never be in Gold-Test; it may serve in Silver-Dev. If a contaminated chart falls in the test date block, keep it out of the test split entirely and list it in `artifacts/excluded_from_test.json`.

**Stopping rules** (stop labeling more charts of a pattern when ANY holds): (a) ≥ 30 gold/silver instances for that event kind in dev and ≥ 15 in test; (b) the next 25 charts shrink the CI half-width of its detection F1 by < 2 pp; (c) the covered strata are exhausted. Rare kinds that never reach n=30 are reported as "insufficient data". **Do not pad statistics with charts outside coverage.**

Excluded from every tier (flag `scope_ok=false`, keep the files): non-ES or non-M5 charts, axis-less slides, corrupt/tiny files, undated files unresolved after S4.

---

## 4. Ordered work plan (new ROADMAP)

Rewrite `ROADMAP.md` with exactly this table (status ✅/🟨/⬜) and per-phase Definition of Done. Keep old commit hashes for finished phases. Do not skip a step; do not start a step before the previous step's DoD is met unless marked "parallel".

| Step | Name | Replaces | Parallel? |
|------|------|----------|-----------|
| S0 | Re-plan, doc sync, safety rails, privacy | new | no |
| S1 | Dependency and environment repair | new | with S0 |
| S2 | Extraction v3: compact schema, validator-gated writes, anchors | part of 5a | no |
| S3 | Phase 5b: market data layer + session calendar + axis resolution | 5b | no |
| S4 | Phase 5c: date alignment and label→bar attachment (bronze sanity checks) | 5b/5c | no |
| S5 | Phase 5a-reduced: Silver-Dev and Gold-Test labeling | 5a | parallel with S6 after S4 |
| S6 | Phase 6: Python streaming engine v0 (+ `PATTERN_SPEC.md`) | 6 | parallel with S5 |
| S7 | Phase 7: evaluation framework + first baseline report | 7 | no |
| S8 | Active-learning Hard set + engine iteration | new | no |
| S9 | Phase 8: playbook (stats with n and CIs) | 8 | no |
| S10 | Phase 9: MQL5 indicator with parity ≥ 98% | 9 | no |
| S11 | Phase 10: signals + EA + walk-forward | 10 | no |
| S12 | Phase 11 (optional) LLM commentary bridge | 11 | optional |
| S13 | Phase 12: hardening and `v1.0.0` | 12 | no |

---

## 5. Detailed instructions per step

### S0 — Re-plan, doc sync, safety rails, privacy

1. Save this prompt **verbatim** as `docs/PLAN_V2.md` (the plan of record; record its SHA-256 in `docs/PLAN_V2.sha256`) and write **ADR-012** ("v2 method: tiered labels, market-data-first, validator-gated writes"). Include the sizing table, split rule, stopping rules, and the list P1–P12.
2. **Single source of truth for status:** create `docs/STATUS.yaml` (current step, step statuses, counts, last gate result, last commit). Add `scripts/sync_status.py` that renders the status blocks in `README.md`, `ROADMAP.md`, and `HANDOFF.md` §1, §2, §8. Add a test that fails when the rendered blocks differ from `STATUS.yaml`. Then fix all stale text (P8): README quick-start status, ROADMAP Phase 0 checkbox ("First commit made" → done), HANDOFF §1 (no longer "Phase 0 only"), HANDOFF §8 (batch-1 numbers).
3. **Public-safety policy (P9) — the repo stays PUBLIC; do NOT ask the user to make it private.** Make "safe to be public" an automated, enforced property:
   - Write `scripts/public_safety_scan.py` (stdlib only) and run it on the working tree **and the entire git history** (`git log --all --name-status`, `git rev-list --objects --all`). It flags: image/video/archive files (jpg, jpeg, png, gif, webp, bmp, mp4, zip, ...); anything under `data/`; market data (`*.csv` larger than 200 KB, MT5 history files); `config/local.yaml`, `.env`; secrets (regexes for API keys, tokens, private keys, `-----BEGIN`); absolute personal paths such as `C:\Users\<name>\`; blobs larger than 1 MB; queue files that embed image bytes (base64) or long verbatim transcriptions of on-chart text.
   - Output `docs/PUBLIC_SAFETY.md` (what is tracked and why it is safe, what is ignored) and fail the gate if the working tree or any new commit violates the rules. CI runs the full-history version.
   - Strengthen `.gitignore` (`data/`, `*.csv` under `data/market/`, `config/local.yaml`, `wheelhouse/`, `_backups/`, images) and add tests.
   - **If the history scan finds anything flagged:** stop and tell the user in Persian with the exact commits/files and the options (rewrite history with `git filter-repo`, or accept the exposure). Never rewrite or force-push history without explicit approval.
   - Replace every "keep this repo private" sentence in README/ROADMAP/docs with an accurate legal notice: *code is MIT; the Brooks-style chart images are third-party material that is NOT distributed in this repository and is kept locally for personal research; broker market data is not redistributed; labels and the playbook are the author's own derived annotations and statistics; contact for take-down requests.*
   - Public-repo hygiene: never commit absolute personal paths or usernames (use `config/local.yaml`), keep chart titles from file names out of tracked artifacts when they identify third-party course material beyond a short normalized day-type (keep `image_id` + normalized fields; raw filenames only in git-ignored files), and never commit anything from `MQL5\Files` or the MT5 data folder except the project's own `.mq5` scripts.
4. **Backups (P5):** create `scripts/backup.py` that writes a timestamped zip of `artifacts/` (labels, queue, gold_set, manifests) to a path outside the repo (configurable; default `..\_backups\al-eod-analyzer\`), keeping the last 10. Run it before every bulk step and add `python -m tasks backup`.
5. Commit the 98+ recovered/uncommitted extraction files first if any are still uncommitted (`git status`), so nothing is at risk before refactors.

6. **Build the enforcement layer from §8** (AGENTS.md, plan-hash guard, plan-compliance check in the gate, git hooks, optional CI, step branches, evidence files). This is part of S0, not optional.

DoD: docs consistent and test-enforced; ADR-012 merged; backup works; public-safety scan implemented, run on full history, and clean (or flagged to the user with options); §8 enforcement implemented and demonstrated (show the gate failing on a deliberately modified `docs/PLAN_V2.md`, then revert).

### S1 — Dependency and environment repair (P10)

1. Make the **engine and domain pure Python (stdlib only)**: this is required for exact MQL5 parity and avoids heavy wheels.
2. Restructure `pyproject.toml` extras: core (typer, pydantic, PyYAML, Pillow), `dev` (ruff, mypy, pytest, coverage, types-*), `data` (pandas, numpy — only for analysis/reports), `vision-local` (opencv, pytesseract — optional, unused). Remove opencv/pytesseract from default/dev.
3. Create an offline wheel cache: `python -m pip download -d wheelhouse -r requirements-lock.txt` (retry with `--timeout 120 --retries 10`; resume by file) and document `pip install --no-index --find-links wheelhouse ...`. `wheelhouse/` is git-ignored.
4. Keep the regression guard `test_package_resolves_to_repo_src`. Document: never run a non-editable `pip install file:///...` in the repo path.
5. pre-commit: install it only if the wheel is cached; otherwise leave the config and document.

DoD: fresh clone → install with core+dev succeeds offline from the wheelhouse; gate green.

### S2 — Extraction v3: compact schema, validator-gated writes, anchors

Goal: more charts per agent turn, zero hand-written JSON, no more copy-slip, BOM, or schema-enum errors.

1. **Taxonomy freeze + migration table (P6).** Freeze v1.3 as the bulk-labeling vocabulary. Add `config/taxonomy_migrations.yaml` (old id → new id(s), with version) and make the label loader auto-migrate legacy ids on read so enum changes never invalidate stored files again. Any future taxonomy change requires: ADR, migration entry, a migration test, regeneration of the calibration report, and a version stamp. Stamp every report and label with `taxonomy_version` and `prompt_version`.
2. **Compact extraction schema v3** (`config/prompts/extract_v3.md` + `docs/LABEL_SCHEMA.md` update). Per chart, one JSON object:
   - `image_id`, `scope_ok` (bool), `scope_note`.
   - `day_type` (enum), `day_type_conf`.
   - `axis`: `style` ∈ {`pt_0630_1300`, `et_style_0900_1500`, `other`, `none`}, `first_label`, `last_label`.
   - **`anchors`** (cheap, objective, used to validate date/time against real bars): `open_dir_first_hour` ∈ {up, down, flat}, `day_close_vs_open` ∈ {above, below, near}, `high_of_day_bar_index_hint`, `low_of_day_bar_index_hint` (bar index from the first bar of the shown session, integers, ±2 tolerance acceptable), `n_bars_visible`.
   - `events`: array of `{kind (enum id only), start_bar_index_hint, end_bar_index_hint (optional), direction, outcome ∈ {success, fail, partial, unclear}, conf, raw_label}`. Compound or unknown labels go in `raw_label` with `kind: "unmapped"` and are pushed to the review queue; never invent enum ids.
   - Keep the schema rules already learned: day-part ranges are `trading_range_begin` + `trading_range_end` pairs; traps normalize to `failed_breakout`; `mm`→`measured_move`; `bar_index_hint` is int-only; `bear_trend_resumption` is invalid (use direction-specific types); `bull_trend_resumption` is valid.
   - Time precision: prefer **bar index** over wall-clock time (axis styles vary); wall-clock only when the axis is legible.
3. **Validator-gated writes (P5).** Implement `brooks write-response --image-id <id> --file <path|stdin>`: parses, validates strictly against the schema and taxonomy, checks that `image_id` in the body equals the target id and exists in the manifest, writes **atomically** (temp file + rename) as **BOM-less UTF-8 with LF**, refuses to overwrite an existing response unless `--replace` and the old one is human-sourced-free. The agent must **never** hand-write response JSON via PowerShell/`Set-Content`; it must pipe through this command (or a Python helper that calls the same service).
4. **Batch tooling:** `brooks extract-batch --tier silver-dev --n 6` prints the next N request prompts (stratified order from the sample file); the agent labels them in one turn (target **4–6 charts per turn**), submits through `write-response`, then `brooks extract --limit N` converts. `brooks extract` refuses to run if `git status` shows uncommitted changes under `artifacts/extraction_queue` (override flag `--allow-dirty`, off by default) and always skips labels that have history unless `--clobber-reviewed`.
5. **Checkpoint commits:** one commit per wave of ≤ 40 labeled charts, preceded by `python -m tasks backup`.
6. **Day-only schema** (`extract_day_v3.md`): for the ~13% unmapped titles, only `image_id`, `scope_ok`, `day_type`, `day_type_conf`, `axis`, `anchors`. Target 8 charts per turn.
7. **Scope filter (P11):** `scope_ok=false` rows are excluded from all statistics; add a CLI report `brooks scope-report`.
8. **Finish in-progress work first (rule R-FINISH, §3) — now a short job.** The previous agent's last report (2026-10-19, commit `2300fe7`; **verify it** with `git log -3`, `git status`, `brooks extract-status`): extraction queue 244/244 filled, 0 request files pending, 162 batch-1 labels active, quarantine 0, calibration agreement 0.706, 166 tests passing, working tree clean. Therefore R-FINISH reduces to:
   - (a) Confirm no request file lacks a response; convert any filled responses still outside the `--limit` scan window (use a limit that covers the whole queue). **No new vision work, and no "raise `--limit` and keep labeling" under the old workflow.** From here on, R-NEW applies to every new chart.
   - (b) **Audit the ad-hoc enum rewrites.** The previous agent rewrote 33 response files with one-off scripts (`trading_range → tight_trading_range`, `low_2 → l2`, `trend_reversal_to_bear_attempt → trend_reversal_to_bear`) and earlier repaired about 114 files with recursive "deep fix" scripts. Some of these mappings are **lossy**: a bare `trading_range` is not necessarily a *tight* range (and by the schema rule a day-part range should be a `trading_range_begin`/`trading_range_end` pair); an `_attempt` reversal means something different from a completed reversal. For each rewritten event: recover the original value (from `raw_label` if preserved, otherwise from git history of `artifacts/extraction_queue`), record every mapping rule in `config/taxonomy_migrations.yaml` with `quality: exact|lossy`, keep the original in `raw_label`, set `needs_review=true` on lossy ones, and write `artifacts/lossy_normalizations.json` (grouped **by mapping rule**, with counts and example image_ids). Send the user one Persian message asking for a decision **per rule**, not per item, and propose proper representations (for example a modifier flag `attempt=true`, or a separate `trend_reversal_attempt` id) through the ADR + migration process instead of collapsing meanings.
   - (c) From now on **no ad-hoc normalizer scripts**: all normalization happens only through the migration table + loader, with a history entry on every changed label.
   - (d) The converted charts are assigned to tiers by date once coverage is known (§3); they do not all need human review now.

DoD: tests for validator, atomic write, migration, dirty-tree guard; a 12-chart dry run through the new path with 0 quarantines; calibration re-baselined (S4 explains how).

### S3 — Market data layer (Phase 5b), coverage probe, similarity gate, axis resolution (P2, P3, P13)

**Context:** the user has an MT5 broker whose CFD feed is believed to be very similar to ES futures, with probably only a few months of M5 history. Treat "similar to ES" as a **hypothesis to be tested**.

1. **Export tooling (read-only) and instructions.**
   - Write `mql5/Scripts/ExportSymbols.mq5`: lists **all** symbols (`SymbolsTotal(false)`, including hidden ones) whose name contains `SP500`, `US500`, `SPX`, `ES` or `S&P` (case-insensitive), with `SymbolInfoString` description/path, expiration time (`SYMBOL_EXPIRATION_TIME`) where applicable, and the date of the first available M5 bar (`SeriesInfoInteger(..., SERIES_FIRSTDATE)` / `SERIES_SERVER_FIRSTDATE`); writes `symbols_sp500.csv` to `MQL5\Files`.
   - Write `mql5/Scripts/ExportRatesM5.mq5` with inputs `InpSymbol`, `InpFrom`, `InpTo`: ensures the symbol is selected (`SymbolSelect`), forces history load (`CopyRates` in chunks, retrying while `SeriesInfoInteger(SERIES_SYNCHRONIZED)` is false), and writes `rates_<symbol>_M5.csv` with columns `time_server, open, high, low, close, tick_volume, real_volume, spread` (server time, ISO format, `.` decimal). Read-only, no trading calls. Also write a `<symbol>_export_info.txt` with first/last bar time, bar count, digits, and contract specification fields.
   - Write `docs/MT5_EXPORT.md`: plain steps (with a Persian summary for the user): open the data folder (*File → Open Data Folder*), confirm the scripts appear in the Navigator, set *Tools → Options → Charts → Max bars in chart* to the largest value, open an M5 chart of each symbol and scroll back (or use History Center, F2) so the terminal actually holds all stored bars, then run `ExportSymbols` and `ExportRatesM5` for **`US500`, `SP500Z6` and every sibling contract found**, and copy the CSVs into `data/market/raw/` (or let the agent copy them from `MQL5\Files`).
   - **USER CHECKPOINT B:** send the user (Persian) the instructions, say that `SP500Z6` expires in December and should be exported **now**, and ask for confirmation that the CSVs are in place. Until the CSVs arrive, build against the CSV contract with synthetic fixtures and continue S0–S2.
   - **1b. Futures contract stitching (no back-adjustment).** Analysis is intraday, so do **not** back-adjust prices. For each RTH session choose the contract with the highest total tick volume during that session (fallback: the contract with the nearest unexpired expiry before the roll window of about 8 days before expiry). Record the choice per date in `artifacts/market_source_map.json` (`date, symbol, rule, alt_symbols`) and flag roll-week sessions. Compare `US500` and the futures source for each overlapping session (daily direction, high/low bar index, range ratio) and report the difference in `artifacts/source_comparison.json`.
2. **CSV contract:** `timestamp_server, open, high, low, close, tick_volume, spread` plus manifest fields `source`, `symbol`, `server_utc_offset_policy`. Raw files live in `data/market/` (git-ignored); `artifacts/market_manifest.json` records hashes, first/last session, coverage, gaps.
3. **Server-time → UTC → exchange time.** Determine the broker's offset rule empirically: across all sessions find the 5-minute bar with the highest average tick volume / range near the US cash open; that bar is 09:30 America/New_York. Derive the offset in each regime (US DST vs non-DST, as many brokers follow US DST for server time), validate it on all days, and store it as `config/broker_time.yaml` with tests. Never trust the broker documentation alone.
4. **Session calendar:** `SessionCalendar` for the US cash session 09:30–16:00 America/New_York ≙ 06:30–13:00 America/Los_Angeles, DST-correct, with holidays/half-days (`config/calendar_us.yaml`). Use `zoneinfo` (+ `tzdata` on Windows). `session_bars(date)` returns the RTH M5 bars (78 on a normal day) with 0-based `bar_index` from the session open. CFD bars outside RTH are ignored.
5. **Coverage probe:** `brooks coverage-probe` prints and saves `artifacts/coverage.json`: first and last complete RTH session, number of complete sessions, missing/short sessions, gaps, duplicates, suspicious ranges. Then compute **N_cov** after S4 and pick Case A/B/C from §3. **Report the numbers to the user in Persian** and propose how far back to go.
6. **Similarity gate (go / no-go), run separately for each candidate source (`US500`, and the stitched futures series).** Pick, per date range, the source that scores best (prefer futures when scores are equal, since the charts come from ES futures). On the covered charts (≥ 30 if available, otherwise all) with anchors from the chart (`open_dir_first_hour`, `day_close_vs_open`, `high_of_day_bar_index_hint`, `low_of_day_bar_index_hint`), compute against the real bars: direction agreement and median |bar-index error| of the day high and low. Decision:
   - **GO-FINE:** direction agreement ≥ 90% and median error ≤ 3 bars → evaluate events with tolerance ±3 bars (also report ±1 and ±5).
   - **GO-STRUCTURAL:** agreement 75–90% or median error 3–6 bars → evaluate day-type, large structures, and events with tolerance ±5 bars and "present within window" logic only.
   - **STOP:** agreement < 75% → do not proceed; **USER CHECKPOINT C** with options: (a) another/longer data source, (b) restrict automatic evaluation to day level and switch to manual review (user marks engine output correct/incorrect on ~40–50 sample days), (c) accept exploratory-only. Record the outcome in an ADR and in `config/default.yaml` (`eval.tolerance_bars`).
7. **Axis resolution protocol** (`scripts/resolve_axis.py` + tests): for the anchors-only audit sample compare chart anchors to the real bars under hypotheses `H_PT` (06:30–13:00 PT), `H_ET_plus_k` (k ∈ {0, 12, 13}), and plausible broker-offset shifts; score per chart and aggregate per axis style; save `artifacts/axis_resolution.json` plus a short Persian summary. Adopt a hypothesis per style when median |bar-index error| ≤ 2 and direction agreement ≥ 90%; otherwise mark the style `ambiguous` and do not attach its charts until the user decides. Because labels use **bar index** (S2), most axis ambiguity becomes harmless.
8. `MarketBarsRepository` port + CSV adapter (stdlib `csv`; pandas optional) and `brooks data-check` quality report (`artifacts/data_check.json`).

DoD: coverage report and N_cov known; broker time rule validated; similarity gate decided and recorded in an ADR; session calendar tests (DST edges, half-days); axis resolution output produced.

### S4 — Date alignment and label→bar attachment (Phase 5c)

1. **Coverage flagging:** after date resolution mark every chart `in_coverage` true/false in the manifest; compute N_cov and choose Case A/B/C (§3) in an ADR. Charts outside coverage are not attached and not extracted further.
2. **Date normalization (P4)** for covered or near-boundary charts: for weekend-dated files and the undated file, generate candidate sessions (previous trading day, next trading day, ±1–3 days) and pick the one with the best anchor score; if the top two are within a small margin, put the chart in `artifacts/date_review.json` for the user (one Persian message, CHECKPOINT D). Record decisions in `artifacts/date_overrides.json` (never rename files).
3. **Automatic bronze sanity check (no vision):** for each covered dated chart with a title-map day_type compute from real bars: open-to-close direction, first-hour direction, range vs ATR, trend-ness (fraction of bars closing in trend direction, pullback depth). Flag contradictions (e.g., `bull_trend_from_open` but the day closed below the open). Output `artifacts/bronze_sanity.json` with mismatch rates by day type; exclude flagged charts from bronze statistics until reviewed.
4. **Duplicates:** dedupe by `image_id`; keep alias rows; the split function groups by date.
5. **Attachment:** `attach-labels` writes labels onto bars by `(date, bar_index)`, refusing when session bar count is inconsistent with `n_bars_visible` beyond tolerance. Report attached / refused / ambiguous counts.
6. **Re-baseline calibration (P7):** regenerate `artifacts/calibration_report.json` under taxonomy v1.3 with a confusion matrix (vision vs title-map, both directions), per-family agreement and the disagreement list, keeping the rule "on-chart title outranks filename". Stamp taxonomy and prompt versions. The 0.706 figure is the reference; later changes are compared only against the same stamp.

7. **Re-link the original gold labels (they have no image on disk).** The 33 original gold images were moved away when batch-1 arrived, but their labels and history are intact and the same source days appear in batch-1. For each gold label find the batch-1 file(s) with the same session date (and matching on-chart title or other chart features if several), record the link in `artifacts/gold_relink.json` (`gold_image_id → batch1_image_ids, confidence`), and ask the user (one Persian message, with the review pages) to confirm ambiguous links. Linked gold labels may then be shown with their image and, if the date is inside coverage, attached to bars (as Silver-Dev material, never Gold-Test); unlinked ones stay label-only.

DoD: every covered chart has a resolved date or a quarantine reason; N_cov and Case chosen; bronze sanity report exists; attachment tests green.

### S5 — Gold-Test then Silver-Dev labeling (parallel with S6, newest-first)

1. Build deterministic (seeded) sample files **from covered charts only**, following the Case chosen in S4: `artifacts/sample_gold_test.json` (newest block, stratified by day-type family, frozen on creation; store the list's SHA-256 in `docs/DECISIONS.md`) and `artifacts/sample_silver_dev.json` (older covered charts, processed in ~3-month blocks, newest block first). Exclude `scope_ok=false` and unresolved bronze-flagged charts.
1b. **Source of new charts (rule R-NEW):** every *new* chart sent to vision must come from the covered set and the sample files above, newest block first. Charts finished under R-FINISH are assigned to tiers by date as described in §3 (contaminated charts never enter Gold-Test).
2. **Label Gold-Test first**, then Silver-Dev blocks going backward in time. Use the compact schema through `write-response`, 4–6 charts per turn, one commit per ≤ 40 charts.
3. **Review workflow for the user** (existing HTML pages: image left, label right, low confidence first): Gold-Test = 100% reviewed; Silver-Dev = random 20% spot-check plus all low-confidence items. **USER CHECKPOINT E** at the end of each 25-chart Gold-Test block, in the style "ok = whole page approved, inline note = that item only".
4. Resolve the open item `10401c705b30` (gold yes/no) at the first checkpoint.
5. **Freeze Gold-Test:** `frozen: true` in `artifacts/gold_test_manifest.json`; a test fails if any frozen label changes without an ADR. The engine and all tuning code must be unable to read Gold-Test labels (the evaluation harness enforces this by split name).
6. If the user later supplies older broker data, repeat S3–S4 for the new range, label older blocks into **dev only**, and never move the test boundary.

DoD: Gold-Test frozen and reviewed; Silver-Dev labeled per Case; stopping-rule report per event kind (n in dev/test, "insufficient data" flags).

### S6 — Python streaming engine v0 (Phase 6)

Architecture (existing layering): `domain` → `application` → `infrastructure` → `engine` → `interfaces`. Engine is **pure Python, deterministic, config-driven** (no magic constants: every threshold in `config/default.yaml` under `engine.*`), `on_bar(bar) -> list[Signal/LabelUpdate]` with **zero look-ahead** (a property-based test truncates the series at every bar and asserts identical outputs up to that bar).

1. Write `docs/PATTERN_SPEC.md` first: for each event kind in taxonomy v1.3 give a numeric, bar-based definition, the earliest bar it can be **provisional**, the rule/lag for **confirmed**, invalidation rules, and which context it needs. Start with a **core set of ~12 kinds**: `trading_range_begin/end`, `wedge`, `double_top`/`double_bottom`, `major_trend_reversal`, `failed_breakout`, `measured_move`, `trend_line` break, `bull/bear_surprise`, `h1–h2/l1–l2` pullback counts, `spike_and_channel` phases, `broad/tight channel`. Extend only after the core is evaluated.
2. Day-type classifier with checkpoints (after bar 6, 12, 24, 36, and EOD) producing a **probability/score with provisional vs final** status, so live behavior can be evaluated honestly.
3. Label lifecycle model: `PROVISIONAL → CONFIRMED | INVALIDATED`, with `first_seen_bar`, `confirmed_bar`, `flip_count`. Metrics later use confirmed labels at their confirmation bar (live-valid) and also final labels (hindsight-valid), clearly separated.
4. Generate **golden vectors** (input bars → expected outputs, as JSON) from the Python engine for later MQL5 parity tests; store under `tests/golden/`.
5. Keep complexity in check: write a baseline first (rule-based day-type from simple stats), then add patterns one by one, each with unit tests and a spec entry. Do not tune on Gold-Test.

DoD: spec complete for the core set; engine passes no-look-ahead tests; golden vectors generated; coverage ≥ 85%.

### S7 — Evaluation framework (Phase 7) and first baseline

1. Splits: `dev` (older covered sessions) and `test` (the newest frozen block, `splits.test_start_date`), grouped by date; tolerance comes from `eval.tolerance_bars` set by the S3 similarity gate; the test split is only read by `brooks evaluate --split test`, which logs every run (timestamp, engine version, config hash, taxonomy version) to `artifacts/eval_runs.jsonl`. Limit test runs to one per engine version.
2. Metrics:
   - Day-type: accuracy and macro-F1 at each checkpoint (bar 12/24/36/EOD) against gold; agreement vs bronze reported separately with the stated bronze noise ceiling (≈ 0.7–0.8 vs on-chart reading).
   - Events: precision/recall/F1 per kind with tolerance ±N bars (N in config; also report ±1 and ±3), direction agreement, **detection latency** (bars between the label's start and first detection), provisional→confirmed flip rate, false-positive rate per day.
   - CIs: Wilson for proportions, bootstrap (by day) for F1; show "insufficient data" when n < 15.
   - Baselines to beat: majority class; title-prior; random-timing detector. Report lift over baselines.
3. Output `docs/EVAL_REPORT.md` (auto-generated) and `artifacts/eval_*.json`. Replace every "NOT RUN" in the metrics snapshot with real numbers.
4. **Tuning harness** (`brooks tune`): grid/random search on **dev only**, with date-blocked cross-validation; no multiple unreported trials (log all trials).

DoD: first honest baseline on dev, one test run recorded, metrics snapshot filled.

### S8 — Active learning Hard set and iteration

1. Select ~100 charts (not in Gold-Test dates) where the engine disagrees with bronze or silver labels (high disagreement score, plus 30% random to avoid bias). Label them (compact schema), review, add to dev (never to test).
2. Iterate on the engine; each iteration = ADR-lite note + eval run on dev. Re-run test only for tagged candidate versions.
3. Stop iterating when dev F1 gains on core kinds fall below 2 pp for two consecutive iterations or the user approves moving on (**USER CHECKPOINT F** with the metrics table in Persian).

### S9 — Playbook (Phase 8)

1. Run the best engine over **all days with real bars** (all ~1678 charted days and any extra ES M5 history available). For each pattern: `n`, outcome definitions (e.g., follow-through measured in ATR multiples or ticks within K bars after confirmation; MFE/MAE), success rates with Wilson CIs, conditioning by day type and time of day, and cost-free vs cost-aware numbers.
2. Publish only patterns with n ≥ 30 in dev and ≥ 15 in test; otherwise "insufficient data". With short broker coverage many kinds will be "insufficient"; say so plainly and, if the user can obtain older ES-like data, extend backward (dev only) rather than loosening the thresholds.
3. Outputs: `artifacts/playbook/playbook.json` (schema-validated) and `docs/PLAYBOOK.md`. State clearly that outcomes are measured on real bars, not copied from Brooks, and that nothing here is a profitability claim.

### S10 — MQL5 indicator (Phase 9)

1. First produce `docs/MT5_SETUP.md`: determine the broker server time offset and DST behavior, symbol name (US500/SPX500/etc.), and RTH window on the **broker clock** before any parity testing; implement the session logic from S3 inside the indicator and make it configurable by input parameters.
2. Port the engine logic faithfully from `PATTERN_SPEC.md` (same state machine, same thresholds loaded from a generated `.mqh` constants file produced from `config/default.yaml` to avoid drift).
3. Parity test: a script feeds the golden-vector bars to the indicator through a Strategy Tester/script run and compares outputs; **target ≥ 98% parity** per kind; list diffs. Provide drawing (lines, labels, failure marks) and a text panel for the live explanation, using provisional vs confirmed styling.
4. Keep OOP and separation: `CBarSeries`, `CSession`, `CPatternDetector` (per kind), `CLabelStore`, `CRenderer`.

### S11 — Signals and EA (Phase 10)

Signals only from patterns with documented out-of-sample evidence in the playbook. The EA must be risk-managed (fixed fractional risk, max daily loss, no martingale or grid, spread/slippage/commission model, session filter), and evaluated with **walk-forward** analysis on data not used for tuning; deliver an honest report including drawdown and the CFD-vs-futures caveat.

### S12 — Optional LLM commentary bridge; S13 — Hardening

Only after S10 parity. Then docs pass, `CHANGELOG.md`, fresh-clone install test, `v1.0.0` with final metrics, and the legal notice (images and broker data never in the repo; personal research use only; the repo is public and must stay public-safe per `docs/PUBLIC_SAFETY.md`).

---

## 6. Additional technical requirements

### 6.1 Naming, IDs and versions
- Stable chart identity = `image_id` (sha1-based). Date always comes from `date_overrides.json` → filename → null, in that order.
- Every artifact has `schema_version`; every label has `taxonomy_version`, `prompt_version`, `source` ∈ {title, vision, human, engine}, and `history[]`.

### 6.2 Compact response example (shape only; use real enum ids)
```json
{
  "image_id": "<sha1-id>",
  "scope_ok": true,
  "day_type": "bull_trend_from_open",
  "day_type_conf": 0.8,
  "axis": {"style": "pt_0630_1300", "first_label": "06:30", "last_label": "13:00"},
  "anchors": {"open_dir_first_hour": "up", "day_close_vs_open": "above",
              "high_of_day_bar_index_hint": 70, "low_of_day_bar_index_hint": 3, "n_bars_visible": 78},
  "events": [
    {"kind": "wedge", "start_bar_index_hint": 40, "end_bar_index_hint": 52,
     "direction": "bull", "outcome": "success", "conf": 0.7, "raw_label": "Wedge Bull Flag"}
  ]
}
```

### 6.3 Tests to add (non-exhaustive)
Validator rejects wrong `image_id`, BOM, unknown enums, compound labels; atomic write; dirty-tree guard; migration table; status sync; split-by-date grouping; frozen Gold-Test guard; session calendar (DST, half-days); axis resolution on synthetic fixtures; attach refusal on bar-count mismatch; engine no-look-ahead property test; label lifecycle; evaluation metrics against hand-computed examples; golden-vector round trip.

### 6.4 Things you must not do
- No random re-extraction of already-labeled charts; no overwriting human-reviewed labels.
- No tuning on Gold-Test; no peeking at test metrics outside logged runs.
- No new taxonomy ids outside the ADR + migration process.
- No hand-written JSON via PowerShell; no committing images; no adding heavy dependencies to the engine.
- No profitability claims.

---

## 7. First actions (do these now, in order)

1. Read the docs and verify the repo state (§0.2). Report discrepancies to the user in Persian, briefly.
2. Run S0 and S1.
3. Present USER CHECKPOINT B (MT5 export of the broker's M5 history: symbol, coverage, CSV) in a Persian message with recommended defaults, then continue with S1–S2 while waiting. (Checkpoint A is retired; the repo stays public.)
4. After every step: gate green → backup → update `STATUS.yaml` and sync docs → commit → push → short Persian progress note with the next step.

When this prompt's steps are complete, `HANDOFF.md` must let a new model continue with no chat context.


---

## 8. Plan-compliance and enforcement (mandatory; built in S0)

The user cannot watch every command, so deviations must be **detectable, blocked where possible, and cheap to revert**.

### 8.1 Session protocol
1. At the start of every session (and again after every ~40 tool calls) re-read `AGENTS.md`, `docs/STATUS.yaml`, and the current step in `docs/PLAN_V2.md`. State in Persian: current step, its Definition of Done, and what you will do now.
2. Work on **one step at a time** (the only allowed overlap is the "parallel" pairs in §4). Never start step k+1 before the DoD of step k is evidenced.
3. At the end of every step produce `docs/evidence/<step>.md` with: commands run and short output summaries, test/gate results, files created/changed, metrics (real numbers only), **deviations from the plan (write "none" or list each, with ADR link)**, and open risks. Then print a short Persian self-audit.
4. Stop at every USER CHECKPOINT and wait. You may continue only with work that does not depend on the answer.

### 8.2 Deviation protocol
If you believe the plan is wrong or impossible: stop, explain in Persian (what, why, options, recommendation), and wait. Do not silently substitute another approach. If you realize you already deviated, say so immediately, revert (`git revert` / restore from backup), and log it in the evidence file.

### 8.3 Mechanical enforcement (implement in S0, keep green forever)
- **`AGENTS.md`** in the repo root (short, ≤ 60 lines): the non-negotiables (see the companion file), pointer to `docs/PLAN_V2.md` and `docs/STATUS.yaml`, the Persian-chat/English-files rule, the checkpoint list.
- **Plan hash guard:** `docs/PLAN_V2.sha256` holds the hash of `docs/PLAN_V2.md`. The gate fails if the plan file changes unless `docs/DECISIONS.md` contains an ADR that references the new hash and the text "user-approved".
- **`plan-compliance` check inside `python -m tasks check`:** `STATUS.yaml` schema valid; at most one step `in_progress` (except the allowed parallel pairs); a step may be `done` only if `docs/evidence/<step>.md` exists with all required sections; the frozen Gold-Test manifest hash is unchanged; the public-safety scan passes (no images, market data, local config, secrets, personal paths or oversized blobs tracked); no label with `source=human` was modified without a history entry; commit messages follow `S<k>: <summary>` (checked on the last N commits).
- **Git hooks** in `.githooks/` activated with `git config core.hooksPath .githooks`: `pre-commit` (fast checks), `commit-msg` (prefix `S<k>:` and a reference to STATUS), `pre-push` (full gate). Document that `--no-verify` is forbidden.
- **CI:** add `.github/workflows/gate.yml` that runs the same gate on every push and pull request (hooks can be bypassed locally; CI cannot). If CI is unavailable, say so in the evidence file.
- **Branch workflow:** each step on a branch `step/S<k>-<name>`; merge into `main` only after the user's approval message for that step; tag `S<k>-done`. This lets the user (or another model) review `git diff main..step/S<k>-<name>`.
- **Gold-Test isolation:** the evaluation harness refuses to run tuning on the test split; every test run is logged in `artifacts/eval_runs.jsonl`.

### 8.4 Hard prohibitions (repeat of §6.4, enforced where possible)
No tuning on Gold-Test; no new taxonomy ids outside ADR + migration; no hand-written JSON through PowerShell; no overwriting human-reviewed labels; no committing images or market data; no heavy dependencies in the engine; no profitability claims; no edits to `docs/PLAN_V2.md` without ADR and user approval; no skipping the gate.
