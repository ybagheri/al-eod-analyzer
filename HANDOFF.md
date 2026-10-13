# HANDOFF
_Last updated: 2026-10-12 by Muse Spark (opencode) — HEAD c41875b + uncommitted Phase 4 tooling (awaiting review)_

## 1. Project in one paragraph

al-eod-analyzer extracts Brooks-style structure from EOD review charts (ES M5
screenshots in `data/`), distils it into a playbook, and reproduces the reading with
a deterministic streaming engine (Python reference + later MQL5 port). Phase 0 builds
the skeleton only; no extraction, engine, or trading logic exists yet.

## 2. Current status

- Current phase: 4 — Human review & gold set
- Phase status: in progress (tooling + review kit done, user review pending; gold 0/33)
- Last green quality gate: 2026-10-12 pre-commit (ruff ✓ / format ✓ 51 files / mypy --strict ✓ 21 files / pytest 113 passed / coverage 93.4%)

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

## 4. Decisions made (link to ADR numbers)

- ADR-001: tech stack (PEP 621, typer/pydantic, ruff/mypy/pytest, tasks.py gate) — see `docs/DECISIONS.md`.
- ADR-004: taxonomy v1 frozen; Pacific axis time; unmapped→review-queue design.
- ADR-005: pilot extraction by the coding agent via file exchange (first-pass, not ground truth).

## 5. Next actions (ordered, the very next step first)

1. USER: review the 33 labels via artifacts/review/pages/index.html (lowest confidence first); reply with corrections and/or bulk APPROVE.
2. Agent: author corrections files + `brooks review-apply` (history archived, gold marked).
3. After approval of tooling: commit (`feat: Phase 4 review workflow and kit`) + push.
4. Phase 5 starts ONLY on explicit user instruction.

## 6. Open questions / blockers

- None blocking. Push works via user's `~/.ssh/id_ed25519` (tested OK as ybagheri).
- `make` absent on Windows → canonical gate is `python -m tasks check` (documented).
- No API keys, no Tesseract → file-exchange extraction (ADR-005); anthropic path untested live.
- April-pair + Sep-23 axes show 09:00–15:00 (vs PT-style 06:30–13:00): ET feed or cropped axis? DEFAULT: recorded as-shown with PT tz + note; Phase 5 must resolve against real bars before any label→bar attachment.
- User supplied glossary notes 2026-10-12 (OO, ii, TBTL, MTR, LLDB, traps, Triangle, TTR, HST, H1-H3/L1-L2) — folded into GLOSSARY.md; taxonomy v1.1 proposal pending approval (see chat).
- HH DT resolved by user as Higher-High → interim parent double_top (dedicated id deferred to v1.2).

## 7. Known issues / tech debt

- `mql5/` contains stubs only — expected until Phase 9.
- Full `.[dev]` install incomplete: numpy/pandas/opencv-python/pytesseract/pre-commit
  NOT installed (12–44 MB wheels timed out on slow net); gate-relevant set + ruff/mypy
  installed. Fresh-clone install still declares them in `pyproject.toml` — medium.
- Gate MUST run with `.venv` on PATH (global mypy lacks typer) — documented in §9.

## 8. Data & artifact state

- Images in data/: 33 (15 JPEG + 18 PNG) | Manifest entries: 33/33 (all ok)
- Labels extracted: 33/33 first-pass (valid_rate 1.00, 0 quarantined, 254 events, 19 unmapped — v1.1 remap done, all remaining per keep-list/deferred) | Reviewed: 0 | Gold set: 0
- Dates CONFIRMED by user 2026-10-12: 04-02 file = 03-31 session, 04-03 file = 04-01 session; 07-29 confirmed correct, 07-22 duplicate file DELETED (manifest/labels/queue cleaned, manifest regenerated 33/33).
- Date flags: 04-02→03-31 and 04-03→04-01 relabelled from title weekday (pipeline warnings fired correctly), both CONFIRMED by user; 07-22/07-29 duplicate resolved (07-29 kept, 07-22 deleted); April + Sep-23 axes run 09:00-15:00 (possible ET feed — Phase 5 must verify, see §6)
- PNG batch (08-01…09-23) has no readable time axis → event times null (15 of 29 new labels)
- Watermark note: Aug/Sep PNGs carry a "Persian_expert_trader" redistribution watermark (third-party, personal research use; same legal basis as data/README)
- Market data coverage: none (Phase 5)
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
```

## 10. Metrics snapshot (real numbers only; "NOT RUN" if unknown)

- Extraction: NOT RUN
- Engine vs labels (dev/test): NOT RUN
- Parity Python↔MQL5: NOT RUN

## 11. Rules reminder for the next model

- Read README, ROADMAP, DECISIONS first. Do not skip phases. Update this file before each commit.
