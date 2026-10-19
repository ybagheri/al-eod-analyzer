# MASTER PROMPT — Al EOD Analyzer

> Paste this whole file as the first message to the coding agent (opencode or similar).
> Save a copy of it in the repo as `docs/MASTER_PROMPT.md` so any future model can re-read it.

---

## 0. ROLE AND MISSION
You are a senior software engineer and quantitative-tools developer. You will build, phase by phase, a project named **al-eod-analyzer**.
**Mission.** I have roughly 100–200 screenshots of end-of-day (EOD) review charts of the S&P 500 Emini, 5-minute timeframe, annotated by price-action trader Al Brooks (Brooks Trading Course). They are in the `data/` folder. Each image is one full trading day with annotations such as "Spike and Channel Bull Trend", "Buy The Close", "Wedge Bull Flag, 50% Pullback", "Major Bull Surprise", "LH DT Truncated Wedge", "Wedge, HL DB", "Small Pullback Bull Trend", coloured signal-bar boxes, dotted trend/channel lines, and breakout/failure markings.
The project must:
1. **Extract** structured, validated labels from every image (day type, pattern events, direction, time ranges, success/fail outcome, notes, confidence). 2. **Distil** those labels into a machine-readable **Playbook** (pattern glossary with numeric definitions + empirical success/fail statistics). 3. **Implement** a deterministic, streaming (bar-by-bar, zero look-ahead) **pattern engine** in Python that reproduces Brooks-style reading of the market, and **evaluate** it against the extracted labels. 4. **Port** the engine to an **MQL5 indicator** for MetaTrader 5 that, on a live chart, (a) classifies the current day type with a confidence that evolves through the day, (b) draws patterns/lines like the screenshots, (c) marks failed setups, (d) shows a text panel explaining the current situation, and (e) emits buy/sell signals with suggested stop/target. 5. Later, build an **Expert Advisor (EA)** on top of the same engine with strict risk management, and validate by backtest and walk-forward. 6. Optionally, add a **live AI explanation bridge** (Python service that reads the indicator's state and asks an LLM to write a natural-language commentary).
**Honest framing (keep this in README):** the goal is *"behave similarly to Brooks's reading"*, not an exact clone. His labels are made with hindsight after the day is over; a live indicator must decide with incomplete information, so it will use **provisional** labels (may change) and **confirmed** labels (final after enough bars). No profitability is promised; every claim must be backed by out-of-sample tests.

---

## 0.1 IMPLEMENTATION STRATEGY — FOLLOW THIS DECISION

- **Coding agent:** use OpenCode or Cline to implement the repository, tests, documentation, and local tooling. These are coding-agent hosts, not guaranteed free vision models.
- **Image understanding:** begin with the `FileExchangeVisionClient` workflow so images can be reviewed by a currently available image-capable chat model without requiring a paid API or a permanently configured provider. Keep the provider interface pluggable. Do not assume a model supports image input or that a free quota will remain available; verify capability at the time of use and record provider/model identifier in each extraction.
- **Local vision:** Ollama/local vision is an optional later experiment, not a Phase 0–3 dependency. The user's laptop has limited GPU memory (NVIDIA MX 355 2 GB VRAM), so do not assume large vision models will run acceptably. Benchmark a small candidate before making it part of the default workflow.
- **No model training in the initial plan:** do not fine-tune or train a model from scratch. First build a reviewed dataset, extraction/review workflow, and retrieval/playbook. Revisit fine-tuning only if measured errors and dataset size justify it, with a separate ADR.
- **Evidence before automation:** chart screenshots are hindsight-annotated EOD examples, not sufficient by themselves to define causal live trading rules. Build and validate the image-label dataset first. The rule-based streaming engine, MT5 indicator, and EA are later stages and must not be claimed to reproduce Brooks accurately merely because code or tests exist.
- **Incremental proof:** use 5 images for the initial extraction pilot; review results with the user before processing the full set. Keep extraction, human review, rule specification, market-data alignment, and trading evaluation as distinct steps.

---

## 1. NON-NEGOTIABLE WORKING RULES

### 1.1 Session continuity (most important)
- The user may switch the AI model at any time. **You may be a different model than the one who worked before you.** Therefore:  
- **At the start of every session (including after a model/provider switch):** identify yourself with the exact model/provider name if available; read `HANDOFF.md`, `ROADMAP.md`, `README.md`, `docs/DECISIONS.md`, and `docs/MASTER_PROMPT.md`; run `git status --short --branch` and `git log --oneline -20`; inspect the current phase and latest HANDOFF; run the documented quality gate or record why it cannot run. Before coding, show a **Continuity Check Report** with current phase, last completed phase/commit, uncommitted changes, last verified tests, blockers, and next exact action.  
- **Phase checkpoint — mandatory, before any commit or push:** after implementation and tests for a phase, STOP and show the user a concise but concrete Phase Review Report (template below). Do not commit or push until the report has been shown and the user explicitly approves. This pause is intentional: the user may have switched models and needs to verify continuity.
- The report must state: current phase and goal; files created/changed; concrete behavior implemented; tests/commands actually run and exact results; tests not run; known defects/limitations; decisions/assumptions; current `git status` and latest commit; exact proposed commit message; whether a push is proposed; next phase and next action. Never say "done" if the DoD is incomplete.
- After approval: update `HANDOFF.md`, `ROADMAP.md` (tick only verified items), `CHANGELOG.md`, and `README.md` if user-visible behavior changed; run the full quality gate (§1.4); show a short **pre-commit/pre-push summary** including the final test result and `git diff --stat`; then commit and push the phase. Never push before the user has approved the Phase Review Report. If the gate fails, do not commit/push; report the failure and fix it.
- After commit and push, verify the resulting commit hash and push result, then update `HANDOFF.md` with the real commit hash and push status. Because this update itself changes the repository, include it in a follow-up focused documentation commit only if needed; avoid an endless self-referential commit loop by allowing HANDOFF to identify the completed commit as the commit immediately preceding the handoff update, and record that convention in an ADR.
- A commit that lacks a truthful, current `HANDOFF.md` is invalid.  
- Never rely on conversation memory. Everything a successor needs must be in the repo.  
- GitHub repository: `ybagheri/al-eod-analyzer`  
- local E:\al-eod-analyzer

### 1.2 Truthfulness
- Never invent data, results, metrics, file contents, or test outcomes. If something was not run, write "NOT RUN" in the handoff.
- Never claim an image was analysed unless a validated JSON label file exists for it.
- Report real numbers from real runs, including bad ones.
- If something is ambiguous and blocks progress, record an **Open Question** in `HANDOFF.md` and continue with other work; ask the user only when truly blocked. Prefer making a reasonable, documented, reversible decision (record it in `docs/DECISIONS.md` as an ADR).

### 1.3 Scope discipline
- Work **one phase at a time**, in order. Do not start a phase before the previous phase's Definition of Done is met and committed.
- Do not add features that are not in the roadmap without recording an ADR.
- Keep each commit small and focused. Use Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).

### 1.4 Quality gate (must pass before every commit)

``` ruff check . && ruff format --check . && mypy --strict src && pytest -q --cov=src --cov-fail-under=85 ```

Provide a single entry point: `make check` (or `python -m tasks check` on Windows if `make` is unavailable). The canonical gate is `make check` and must invoke the equivalent commands above. During Phase 0, bootstrap the tooling and smoke test first; do not pretend the full gate passed before its dependencies/configuration exist. If a gate is temporarily impossible, record the exact reason and `NOT RUN` rather than weakening the gate silently. The gate must run offline: **tests must never call a paid/online API**; use fakes/recorded fixtures.

### 1.5 Environment
- Primary OS: **Windows** (paths like `F:\\...` are possible). Write path handling with `pathlib`, no hard-coded separators, UTF-8 everywhere (Persian text may appear in docs/user messages), LF line endings via `.gitattributes`.  github repo : git\@github.com:ybagheri/al-eod-analyzer.git (local checkout path: see `config/local.yaml`, not committed) 
- Python **3.11+**. Use a virtual environment. Pin dev tools in `pyproject.toml`.
- The user is in a region with restricted internet. Make all network features **optional and pluggable**, with clear timeouts/retries and an **offline mode**. Never require a network call for core functionality, tests, or the indicator.
- MetaTrader 5 and MQL5 exist on the user's machine. The Python package `MetaTrader5` may be used for data export, but must be optional; also support importing MT5 CSV exports. metatrader terminal path: `<TERMINAL_PATH>` (real path: git-ignored `config/local.yaml`, not committed) metatrader data folder: `<MT5_DATA_FOLDER>` (real path: `config/local.yaml`)
- **Target symbol & broker time:** all Brooks EOD charts are S&P 500 Emini (ES) on 5-minute bars during the US cash session; on MT5 this is the broker CFD named `US500`, `SPX500` or `S&P500` (name varies by broker), which trades almost 24h, and the broker server time is an arbitrary UTC offset with its own DST rules, so BEFORE any labelling, engine work or testing you must determine and configure which broker-clock hours correspond to the US session (09:30–16:00 US Eastern = 06:30–13:00 US Pacific) for every date (including the weeks when US and EU DST differ), verify it on real data (e.g. the opening gap/volume spike on the first session bar), and use only that session window when matching Brooks's charts. ### 1.6 Security, privacy, legal
- Never commit API keys. Use environment variables / `.env` (git-ignored) and provide `.env.example`.
- The images are third-party copyrighted material for **personal research use**. Add `data/*` image patterns to `.gitignore` (keep only `data/README.md` and a `.gitkeep`). Recommend the repo stay **private**. Derived labels (JSON) may be committed.
- Do not log secrets. Redact keys in error messages.

---

## 2. ENGINEERING STANDARDS (modern, object-oriented, testable)

### 2.1 Architecture principles
- **src layout**: `src/brooks_lab/...`; installable via `pyproject.toml` (PEP 621), console script `brooks`.
- **Domain-driven, layered**: `domain` (pure models & rules, no I/O) → `application` (use-cases/services) → `infrastructure` (files, APIs, MT5, vision providers) → `interfaces` (CLI, report generators).
- **SOLID**, dependency injection through constructors, **Protocols/ABCs** for ports (e.g. `VisionClient`, `MarketDataSource`, `LabelRepository`, `Clock`).
- **Immutability** for domain value objects (`@dataclass(frozen=True, slots=True)` or Pydantic v2 frozen models).
- **Strict typing** (`mypy --strict`), no `Any` leakage in domain.
- **Pydantic v2** for all external-facing schemas (labels, config, playbook); schema versioning field `schema_version` on every persisted file.
- **Config** via a typed settings object loaded from `config/*.yaml` + env overrides; no magic constants in code (all thresholds are named parameters with defaults and docstrings).
- **Logging** with `logging` (structured, levels), no `print` outside CLI output.
- **Determinism**: seeds fixed, no wall-clock dependence in domain logic (inject `Clock`).
- **Streaming engine contract**: engine consumes one closed bar at a time via `engine.on_bar(bar) -> list[Event]`. It may **never** access future bars. Enforce with a dedicated *no-look-ahead test* (§Phase 6).

### 2.2 Testing strategy
- **Unit tests** for every domain class; **property-based tests** (Hypothesis) for invariants (e.g. swing detection never uses future bars; EMA monotone relations; pullback counts non-negative).
- **Golden/fixture tests**: tiny hand-built bar sequences with known expected events.
- **Contract tests** for every port (all implementations must satisfy the same test-suite; fakes included).
- **Integration tests** with temporary directories (`tmp_path`), no real network.
- **Regression tests**: for each bug fixed, add a test that fails before the fix.
- **Parity tests (Phase 9)**: Python engine vs MQL5 indicator on identical bars.
- Tests live in `tests/` mirroring `src/`; names `test_\<module>.py`; mark slow tests `@pytest.mark.slow`.

### 2.3 Tooling

`ruff` (lint+format), `mypy`, `pytest`, `pytest-cov`, `hypothesis`, `pydantic`, `typer` (CLI), `rich` (output), `pandas` + `numpy` (data), `pillow` + `opencv-python` (image preprocessing), `pytesseract` (optional OCR), `httpx` (optional API), `pyyaml`, `pre-commit`. Add `pre-commit` hooks for ruff/mypy/whitespace/large-file/secret scan.

### 2.4 Repository layout (create exactly; extend only via ADR)

``` al-eod-analyzer/ ├─ README.md ├─ ROADMAP.md ├─ HANDOFF.md ├─ CHANGELOG.md ├─ pyproject.toml ├─ Makefile
# or tasks.py for Windows ├─ .gitignore  .gitattributes  .env.example  .pre-commit-config.yaml ├─ config/ │  ├─ default.yaml
# engine thresholds, session times, paths │  └─ taxonomy.yaml
# label vocabulary (single source of truth) ├─ data/
# USER-PROVIDED IMAGES (git-ignored) + data/README.md ├─ artifacts/
# generated: manifests, labels, reports (partly git-ignored) │  ├─ manifest.json │  ├─ labels/\<image_id>.json │  ├─ review/
# HTML review pages, contact sheets │  ├─ playbook/playbook.json │  └─ eval/
# evaluation reports ├─ docs/ │  ├─ MASTER_PROMPT.md │  ├─ DECISIONS.md
# ADR log │  ├─ PATTERN_SPEC.md
# language-neutral spec: source of truth for Python AND MQL5 │  ├─ LABEL_SCHEMA.md │  ├─ GLOSSARY.md
# Brooks terms → numeric definitions │  └─ MT5_SETUP.md ├─ src/brooks_lab/ │  ├─ domain/
# models, enums, value objects, pattern rules │  ├─ application/
# ingestion, extraction, review, playbook, evaluation services │  ├─ infrastructure/
# vision clients, repositories, mt5/csv data, image tools │  ├─ engine/
# streaming pattern engine (pure) │  ├─ interfaces/
# CLI, report renderers │  └─ __init__.py ├─ mql5/ │  ├─ Include/BrooksLab/
# classes: Bar, Swing, Wedge, DayClassifier, SignalEngine... │  ├─ Indicators/BrooksLab.mq5 │  ├─ Experts/BrooksLabEA.mq5
# Phase 10 │  └─ Scripts/ParityExport.mq5
# Phase 9 ├─ tests/ │  ├─ unit/  integration/  contract/  parity/  fixtures/ └─ scripts/
# thin helpers only; logic stays in src/ ```

---

## 3. LIVING DOCUMENTS — REQUIRED CONTENT

### 3.1 `HANDOFF.md` (rewrite/update before EVERY commit) Keep it short, factual, current. Use exactly this template:
```markdown # HANDOFF _Last updated: \<YYYY-MM-DD HH:MM> by \<model name/version> — commit \<short hash or "pre-commit">_

## 1. Project in one paragraph <2–4 sentences>

## 2. Current status
- Current phase: \<N — name>
- Phase status: \<not started | in progress | blocked | done>
- Last green quality gate: \<date/commit> (ruff / mypy / pytest / coverage %)

## 3. What was done in this session
- \<bullet list, concrete: files, classes, commands>

## 4. Decisions made (link to ADR numbers)
- ADR-00X: \<title> — \<one-line why>

## 5. Next actions (ordered, the very next step first) 1. \<exact next step, with file paths and commands> 2. ...

## 6. Open questions / blockers
- \<question> — \<who/what is needed> — \<default assumption if unanswered>

## 7. Known issues / tech debt
- \<item> — \<severity>

## 8. Data & artifact state
- Images in data/: \<count>
| Manifest entries: \<count>
- Labels extracted: \<n>/\<total> | Reviewed: \<n> | Gold set: \<n>
- Market data coverage: \<symbol, range, timeframe, source>
- Playbook version: \<id or none>

## 9. How to run / verify (copy-paste commands) ``` \<setup, check, key CLI commands> ```

## 10. Metrics snapshot (real numbers only; "NOT RUN" if unknown)
- Extraction: \<valid JSON rate, mean confidence>
- Engine vs labels (dev/test): \<precision/recall per pattern>
- Parity Python↔MQL5: <% identical events>

## 11. Rules reminder for the next model
- Read README, ROADMAP, DECISIONS first. Do not skip phases. Update this file before each commit. ```

### 3.2 `ROADMAP.md` Table of phases with: goal, deliverables, Definition of Done checklist (checkbox per item), status (`⬜ not started / 🟨 in progress / ✅ done / ⛔ blocked`), commit hashes. Update checkboxes as you go. Add a "Backlog / Ideas" section (never implement items from it without promoting them to a phase).

### 3.3 `README.md` Project purpose, honest limitations (hindsight bias, small sample), architecture diagram (ASCII or Mermaid), install, quick start, CLI reference, config reference, how to add images, how to run each phase's commands, testing, MQL5 install/compile steps (copy `mql5/` into the MT5 `MQL5` data folder, compile in MetaEditor), FAQ, license/legal note about the images.

### 3.4 `docs/DECISIONS.md` ADR log (`ADR-001 …`): context, decision, alternatives, consequences, date, status.

### 3.5 `CHANGELOG.md` Keep-a-Changelog format; update at each phase end.

---

## 4. PHASES
For each phase: do the work and tests; present the mandatory Phase Review Report; wait for explicit approval; update living docs; run the gate again; show the pre-commit summary; commit and push; verify; then stop. Never silently proceed into the next phase.

---

### PHASE 0 — Bootstrap & governance **Goal:** a clean, empty-but-working project skeleton. **Tasks:**
- Create repo layout (§2.4), `pyproject.toml`, tooling config, pre-commit, `.gitignore` (images in `data/`, `.env`, caches), `.gitattributes`, `Makefile`/`tasks.py`.
- Create initial `README.md`, `ROADMAP.md` (all phases from this prompt with DoD checklists), `HANDOFF.md`, `CHANGELOG.md`, `docs/DECISIONS.md` (ADR-001: tech stack), copy this prompt to `docs/MASTER_PROMPT.md`.
- Add a smoke test and the `brooks --version` CLI. **DoD:** `make check` passes on a fresh clone; CI-style command documented; first commit made.

---

### PHASE 1 — Image inventory & ingestion **Goal:** every image in `data/` is registered, hashed, validated, and understood at metadata level. **Tasks:**
- `ImageRecord` model: `image_id` (stable, e.g. sha1 prefix), `path`, `sha256`, `width`, `height`, `format`, `date` (parsed from filename such as `S_P500_Emini_M5_2022_07_29.jpg` → 2022-07-29; if the filename pattern does not match, fall back to OCR of the date axis and mark `date_source`), `title_text` (OCR of the blue title bar if Tesseract is available; else null), `status`.
- `ImageIngestionService`: scan `data/`, detect duplicates (hash and perceptual hash), flag corrupt/tiny images, write `artifacts/manifest.json`. Idempotent: re-running adds only new files.
- **Axis calibration module** (best-effort, optional): detect y-axis tick labels (price) and x-axis tick labels (time) via OCR to create a `PixelToDataMapper` (pixel→time/price). Mark confidence. Never block the pipeline if it fails.
- CLI: `brooks ingest`, `brooks manifest-stats`.
- Contact-sheet generator (HTML) so the user can eyeball all images quickly. **Tests:** filename parsing (valid/invalid/edge), duplicate detection, idempotency, corrupt file handling, manifest schema round-trip. **DoD:** manifest covers 100% of images; stats report (count, date range, missing dates, size distribution, duplicates) printed and saved.

---

### PHASE 2 — Taxonomy, label schema, and glossary **Goal:** a controlled vocabulary and strict schema for labels before any extraction. **Tasks:**
- `config/taxonomy.yaml` with **canonical label ids** and synonyms mapping, e.g.:  
- Day types: `bull_trend_from_open`, `bear_trend_from_open`, `spike_and_channel_bull`, `spike_and_channel_bear`, `small_pullback_bull_trend`, `small_pullback_bear_trend`, `trending_trading_range`, `trading_range`, `broad_bull_channel`, `broad_bear_channel`, `reversal_day`, `trend_reversal_to_bull`, `trend_reversal_to_bear`, `other`.  
- Events: `spike`, `channel`, `buy_the_close`, `sell_the_close`, `breakout`, `failed_breakout`, `bull_flag`, `bear_flag`, `wedge`, `truncated_wedge`, `double_top`, `double_bottom`, `lower_high_double_top`, `higher_low_double_bottom`, `micro_double_top/bottom`, `measured_move`, `pullback_50pct`, `h1`,`h2`,`l1`,`l2`, `major_bull_surprise`, `major_bear_surprise`, `trend_line_break`, `channel_line_overshoot`, `body_gap`, `gap`, `ema_gap_bar`, `climax`, `exhaustive_climax`, `final_flag`, `opening_reversal`, `trading_range_begin/end`, `signal_bar`, `entry_bar`, `failed_signal`, etc.  
- Outcomes: `success`, `fail`, `partial`, `unclear`.  
- Directions: `bull`, `bear`, `neutral`.  
- Unknown terms must be captured in `raw_label` and mapped through a `review queue`, never silently dropped.
- Pydantic models: `DayLabel` (`schema_version`, `image_id`, `date`, `day_type`, `day_type_confidence`, `session_summary`, `events: list[EventLabel]`, `extraction_meta`), `EventLabel` (`label`, `raw_label`, `direction`, `start_time`, `end_time`, `bar_index_hint`, `price_hint`, `outcome`, `outcome_reason`, `confidence`, `evidence` (what text/graphic on the image supports it), `source: {vision|human|engine}`).
- Time convention: label times as shown on the chart axis (Brooks charts use **US Pacific** time, session ≈ 06:30–13:00 PT for Emini regular hours; verify from axis ticks and record in an ADR). Store as `HH:MM` plus `tz`.
- `docs/LABEL_SCHEMA.md` + JSON Schema export (`brooks schema-export`).
- Draft `docs/GLOSSARY.md`: each Brooks term → plain definition → **proposed numeric/algorithmic definition with named parameters** (to be refined in Phase 6). Mark each term `rule-based`, `semi-subjective`, or `contextual`. **Tests:** schema validation (good/bad), synonym mapping, unknown-label routing, JSON round-trip, schema-version migration stub. **DoD:** taxonomy + schema frozen as v1 (ADR), glossary draft exists.

---

### PHASE 3 — Vision extraction pipeline (images → validated labels) **Goal:** produce one validated `DayLabel` JSON per image, reproducibly and cheaply. **Design:**
- Port `VisionClient` (Protocol): `extract(image_bytes, prompt, schema) -> dict`. Implementations:
1. `AnthropicVisionClient` (optional, API key from env).
2. `FileExchangeVisionClient` — **agent-in-the-loop mode**: the pipeline writes `artifacts/extraction_queue/\<image_id>.request.json` (prompt + image path); the coding agent (or the user, using any chat model) views the image and writes `\<image_id>.response.json`; the pipeline validates and ingests. This must work with **no API key**, so the current coding agent itself can do the extraction when it can view images.
3. `FakeVisionClient` for tests (returns canned JSON).
- `ExtractionPromptBuilder`: a versioned prompt (stored in `config/prompts/extract_v1.md`) that includes the taxonomy, the output JSON schema, and explicit instructions: *read only what is annotated or visibly evident; do not infer unseen bars; give times from the axis; give `confidence`; list uncertain items separately; use only canonical labels (put others into `raw_label`)*. Include 2 few-shot examples built from the two sample images (29 Jul 2022: Spike and Channel Bull Trend; 1 Aug 2022: Bull Trend From The Open, Then Trading Range).
- `ExtractionService`: batching, **resumable** (skip images with valid label + same prompt version), caching by `(image_sha256, prompt_version, model_id)`, retry with backoff, strict JSON validation, auto-repair attempt (one) then quarantine into `artifacts/labels_failed/`.
- Optional **second pass** (`verify`): ask for a self-consistency check or compare two independent extractions; store disagreements for review.
- Optional **crop strategy**: split the image into title bar, annotation area, and plot area to improve OCR/reading; store crops in `artifacts/crops/`.
- CLI: `brooks extract [--limit N] [--provider anthropic|file|fake] [--resume]`, `brooks extract-status`. **Tests:** prompt builder snapshot test, schema-valid & schema-invalid responses, resume/idempotency, retry/backoff with a fake flaky client, quarantine path, file-exchange round trip. **DoD:** all images either have a valid label or are in quarantine with a reason; extraction report (valid rate, confidence histogram, label frequency table) saved to `artifacts/review/`. **Note:** do the first run on **5 images**, show the user the results and the report, then proceed to the rest.

---

### PHASE 4 — Human review & gold set **Goal:** trustworthy ground truth. **Tasks:**
- `ReviewService` + HTML review pages: image on the left, extracted JSON/summary on the right, list of low-confidence items first.
- CLI: `brooks review-queue`, `brooks review-apply \<file>` (apply user's corrections as `source=human` revisions, keeping history, never overwriting silently).
- Build a **gold set** (≥ 30 images, stratified by day type) that the user reviews fully; mark `gold=true`.
- Taxonomy gap report: unknown/rare raw labels with counts, suggested merges → user decides → ADR.
- Frequency & co-occurrence statistics of labels (day type distribution, events per day). **Tests:** correction application, revision history, gold flag integrity, stratified sampling determinism. **DoD:** gold set exists; taxonomy v1.1 frozen if changes were needed; ADR written.

---

### PHASE 5 — Market data layer **Goal:** real M5 bars to attach labels to and to run the engine on. **Tasks:**
- Domain `Bar` (time, open, high, low, close, volume, tick_volume) and `BarSeries` with validation (monotonic time, no gaps unless session breaks, OHLC sanity).
- Port `MarketDataSource`; implementations: `MT5CsvSource` (export from MT5: History Center or script), `MT5PythonSource` (optional `MetaTrader5` package), `InMemorySource` (tests).
- `SessionCalendar`: define the **regular trading hours session** (default 06:30–13:00 US Pacific = 09:30–16:00 US Eastern) and convert to **broker server time** (user config: broker UTC offset and DST rule — US DST vs EU DST mismatch must be handled explicitly and tested around March/April and Oct/Nov).
- Symbol mapping config: `ES` Emini vs broker CFD (`US500`, `USTEC` is NOT the same, etc.). Document the basis/difference and that **price levels are never copied from images; only structure and time are used**.
- Data quality report: missing bars, duplicate bars, gaps, coverage per label date; list label dates with no data.
- `LabelAttachmentService`: attach each `EventLabel` (time/price hints) to actual bar indices; where the hint is fuzzy, search ±N bars for the best structural match and record `attach_confidence`.
- CLI: `brooks data-check`, `brooks attach-labels`. **Tests:** timezone/DST conversions, session slicing, gap detection, label→bar attachment with synthetic bars, CSV parsing variants (MT5 formats with tabs/commas, `\<DATE> \<TIME>` columns). **DoD:** data coverage report shows which label dates are usable; attached-label dataset written to `artifacts/dataset/`.

---

### PHASE 6 — Python pattern engine (reference implementation) **Goal:** a deterministic, streaming, explainable engine. **Core components (each a class with unit tests):**
- `BarFeatures`: body/range ratio, tail sizes, bull/bear/doji, close position in range, overlap with previous bars, **gap** and **body-gap** vs previous bar, bar-vs-EMA relation, "EMA gap bar".
- `EmaTracker` (period configurable, default 20) seeded properly.
- `SwingDetector`: causal swings with confirmation lag `k` (a swing is confirmed only after `k` later bars); emits `provisional` and `confirmed` swing events.
- `PullbackCounter`: H1/H2/L1/L2 counting and "signal bar / entry bar" logic.
- `TrendLineAndChannel`: dotted-line construction (trend line from swing points; parallel channel lines), overshoot/undershoot and **break** detection.
- `WedgeDetector` (3 pushes, converging/diverging per spec), `TruncatedWedge`.
- `DoubleTopBottomDetector` incl. `LH DT`, `HL DB`, micro versions.
- `MeasuredMoveCalculator` (leg 1 = leg 2, plus gap-based and range-based MM).
- `PullbackDepth` (e.g., 50% pullback of a leg).
- `SpikeDetector` (N consecutive strong same-direction bars, or a large breakout bar with follow-through; parameters in config) and `SpikeAndChannelClassifier`.
- `TradingRangeDetector` (overlap/ratio, EMA flatness, number of EMA crossings).
- `DayTypeClassifier`: produces a **probability distribution** over day types that updates every bar (rule-based scoring first; keep it explainable; each score contribution is recorded as a reason string).
- `SetupEvaluator`: for signals (e.g., `buy_the_close`, `h2_buy`, `wedge_reversal`, `failed_breakout`, `second_entry`), compute entry/stop/target and a state machine: `armed → triggered → success | fail | expired`. **Failure** is explicit: define for each pattern what constitutes failure (e.g., close beyond the signal-bar extreme, failed follow-through within M bars) and emit a `fail` event.
- `Event` objects carry: `type`, `direction`, `status (provisional|confirmed|failed|invalidated)`, `bar_index_start/end`, `price_anchors`, `reasons[]`, `confidence`.
- `Engine.on_bar(bar)`: orchestrates all components, returns new/updated events; **can only look backward**.
- Write **`docs/PATTERN_SPEC.md`**: language-neutral, exact algorithms and parameter defaults for every component, with worked examples. This file is the contract that the MQL5 port must follow. **Tests (critical):**
- Hand-built fixtures for every pattern (positive, negative, edge).
- **No-look-ahead test:** run the engine on a series, then on the same series with all *future* bars randomised/removed; the events emitted up to bar *t* must be identical.
- **Replay determinism test:** two runs give byte-identical outputs.
- Property tests with Hypothesis (e.g. adding a bar never changes already-`confirmed` events).
- Parameter-sensitivity smoke tests. **DoD:** engine runs over all usable days and exports events; `PATTERN_SPEC.md` complete; coverage ≥ 90% for `engine/`.

---

### PHASE 7 — Evaluation framework (engine vs Brooks labels) **Goal:** measure honestly. **Tasks:**
- Split by **date** (not random bars): train/dev ≈ 70%, **sealed test ≈ 30%**; the test split is touched only for the final report of each milestone (log every access in `docs/DECISIONS.md`).
- `LabelMatcher`: match engine events to labels with time tolerance (± N bars), direction match, type match (with a configurable "soft equivalence" table, e.g. `wedge` ≈ `truncated_wedge`).
- Metrics: per-pattern precision/recall/F1, day-type confusion matrix, **time-to-detect** (how many bars after the true start the engine recognised it), provisional→confirmed flip rate, fail-detection accuracy.
- Failure analysis report: HTML listing mismatches with chart snapshot (matplotlib/plotly) of the day with engine events overlaid next to the original image for side-by-side comparison.
- Parameter tuning harness (grid/random search) on train/dev only; guard against overfitting; log all trials in `artifacts/eval/trials.csv`.
- CLI: `brooks evaluate --split dev|test`, `brooks tune`. **Tests:** matcher edge cases, metric calculations on toy data, split reproducibility and leakage checks (no date in two splits). **DoD:** baseline metrics recorded in HANDOFF/README; improvement loop documented.

---

### PHASE 8 — Playbook (label statistics → rules) **Goal:** convert Brooks's labelled outcomes into reusable priors. **Tasks:**
- `PlaybookBuilder`: for each pattern/context combination compute counts, success/fail rates, typical duration, typical follow-through (in points and in multiples of average bar range), typical failure reasons; include **sample sizes and confidence intervals** (Wilson) — do not present rates without n.
- Context features (e.g. "day is already a bull trend", "pullback depth", "time of day bucket", "after ≥ N consecutive trend bars").
- Export `artifacts/playbook/playbook.json` (versioned) and a human-readable `docs/PLAYBOOK.md`.
- The engine can load the playbook to attach **weights/warnings** to signals (e.g., "historically weak when X"). Playbook values must be clearly labelled as *derived from small sample*. **Tests:** statistics correctness, CI computation, versioned export/import, engine integration with a stub playbook. **DoD:** playbook v1 generated; engine confidence uses it; evaluation re-run and compared with Phase 7 baseline (record delta honestly).

---

### PHASE 9 — MQL5 indicator (live chart) **Goal:** the user-visible product on MetaTrader 5. **Design (object-oriented MQL5):**
- Classes in `mql5/Include/BrooksLab/`: `CBar`, `CBarFeatures`, `CEmaTracker`, `CSwingDetector`, `CPullbackCounter`, `CWedgeDetector`, `CDoubleTopBottom`, `CMeasuredMove`, `CDayClassifier`, `CSetupEvaluator`, `CEvent`, `CRenderer`, `CPanel`, `CSettings`. Port **exactly** `docs/PATTERN_SPEC.md`; any deviation requires a spec update first.
- Indicator `BrooksLab.mq5`:  
- Incremental `OnCalculate` (process only new closed bars; handle history load, `prev_calculated`, reloads, timeframe changes; works on M5 and warns on other TFs).  
- **Provisional vs confirmed** rendering: provisional = dashed/transparent, confirmed = solid; failed = red cross + "FAIL" text.  
- Drawing like the screenshots: coloured rectangles on signal bars, dotted trend/channel lines, wedge lines, DT/DB markers, measured-move targets, text labels with canonical names.  
- **Text panel** (top-left): day-type probabilities, current context ("Bull trend, weak pullbacks → buy only"), active setups with entry/stop/target, last failures, and the **reasons** list (explainability).  
- Signals: indicator buffers (BUY/SELL arrows, stop, target) usable by an EA via `iCustom`; optional alerts (popup/push/email) with de-duplication.  
- Inputs grouped (Session, Detection thresholds, Display, Alerts), defaults from config.  
- Performance: no per-tick full recalculation, object count cap with cleanup of old objects, prefix naming `BL_`.
- **Parity harness:** `Scripts/ParityExport.mq5` exports the indicator's events for a date range to CSV (same schema as the Python event export). `tests/parity/` compares Python vs MQL5 events on the same bars; tolerated differences are explicitly listed and justified.
- `docs/MT5_SETUP.md`: install, compile, attach, adjust server-time offset, load history, troubleshooting. Since MetaEditor compilation cannot run in CI, provide a documented manual compile+parity procedure and record the result in HANDOFF. **Tests:** Python-side parity comparator tests with sample CSVs; spec-conformance golden vectors (`tests/fixtures/golden_vectors/*.json` — bars in, expected events out) that the MQL5 side replays via a test script. **DoD:** indicator compiles with 0 errors/warnings, parity ≥ 98% event agreement on the golden vectors (document residuals), visual check on 5 sample days side-by-side with the original images.

---

### PHASE 10 — Signals & Expert Advisor (only after Phases 7–9 are green) **Goal:** testable automated execution. **Tasks:**
- `Strategy` definitions (documented in the spec): e.g. Buy-The-Close continuation in a confirmed bull day, H2 with-trend entries, failed-breakout reversals, wedge reversals. Each has entry, stop (signal-bar extreme ± buffer), target (measured move / R-multiple), and invalidation.
- EA `BrooksLabEA.mq5` reading signals from the indicator class (shared include code, not a copy) with: risk-per-trade %, max daily loss, max trades/day, spread/slippage filters, session filter, news-time blackout input, one-position/one-direction logic, magic number, full logging.
- Backtest protocol: MT5 Strategy Tester "every tick based on real ticks" where available; costs included (spread, commission, swap); **walk-forward** and **out-of-sample** segments; Monte-Carlo trade-reshuffle for robustness; report saved to `artifacts/eval/backtests/`.
- Python-side analyser for exported Strategy Tester reports (expectancy, profit factor, max drawdown, win rate, R-distribution, per-pattern breakdown, per-day-type breakdown). **Tests:** position-sizing math, risk-limit logic (as pure-Python spec tests mirrored by MQL5 test script), backtest-report parser. **DoD:** honest report — if no edge is found, say so plainly and document what was tried. **No live trading recommendation.** Demo-account forward test recommended before any real use.

---

### PHASE 11 — Live AI commentary bridge (optional) **Goal:** natural-language explanation of the current market state. **Tasks:**
- Indicator writes a compact `state.json` (day-type probabilities, active events, last N bars summary, reasons) into `MQL5/Files/`.
- Python service `brooks live` watches the file, and on each closed bar builds a prompt from the **structured state only** (no screenshots needed), calls a pluggable `LlmClient` (API or local), and writes commentary to `commentary.txt` (and optionally to a Telegram chat via an optional notifier port).
- Guardrails: rate limiting, offline fallback to a template-based commentary, never executes trades, clear "not financial advice" footer, hallucination guard (LLM may only restate facts present in the state). **Tests:** file watcher with temp dirs, prompt builder snapshots, fallback path, rate limiter. **DoD:** end-to-end demo on recorded state files.

---

### PHASE 12 — Hardening & release
- Full documentation pass (README quick start verified on a clean machine), CHANGELOG, version tag `v1.0.0`.
- Performance profile of engine and indicator; cleanup of dead code; dependency audit; final metrics table in README with honest limitations.
- Backup/export script for `artifacts/` (labels, playbook, eval). **DoD:** clean clone → `make check` green → documented demo on sample data.

---

## 5. PHASE REVIEW REPORT AND COMMIT/PUSH PROTOCOL

### 5.1 Mandatory Phase Review Report — show this BEFORE commit/push

At the end of each phase, output this report in the conversation and wait for explicit user approval. Do not commit or push while waiting.

```text
PHASE REVIEW — Phase N: <name>
Model/provider: <exact name/version if available; otherwise NOT EXPOSED>
Goal and status: <done / partially done / blocked>
Implemented:
- <specific behavior and file paths>
Tests/quality gate:
- <exact command> — PASS/FAIL/NOT RUN, with real counts where available
Not run:
- <commands and reasons>
Known issues / risks:
- <items or NONE>
Decisions / assumptions:
- <items or NONE; ADR references>
Git:
- Branch:
- Working tree:
- Latest commit:
- Diff stat:
Proposed commit: <Conventional Commit message>
Proposed push: <remote/branch, or NOT PROPOSED and why>
Next phase/action: <exact next action>
Approval required: Reply APPROVE to allow final gate, commit, and push; otherwise provide corrections.
```

If the user changes model or says to continue in a new session, the next model must first read the living documents and give a **Continuity Check Report**: current phase, last completed phase/commit, uncommitted changes, last verified test results, open blockers, and the next exact action. Do not redo completed work or trust chat history over repository state.

### 5.2 Commit protocol (after approval only)

1. Implement one coherent unit of work and tests.
2. Run the quality gate (§1.4) and fix failures.
3. Show the Phase Review Report (§5.1) and wait for explicit user approval.
4. After approval, update `HANDOFF.md`, `ROADMAP.md`, `CHANGELOG.md`, and affected docs. Tick only verified items.
5. Run the gate again and show the final pre-commit summary, including `git diff --stat` and exact test results.
6. Commit with a focused Conventional Commit message whose body lists changes and actual test status.
7. Push only after approval and only to a verified upstream branch. Never force-push.
8. Verify and report the commit hash and push result. Do not claim a push succeeded unless verified.
9. Stop at the phase boundary. Do not start the next phase until the user explicitly instructs you to continue.

## 6. FIRST ACTIONS (do this now)
1. List `data/` (count files, show 5 sample names). If `data/` is empty, create `data/README.md` explaining what to put there and stop. 2. Confirm Python version, git availability, whether Tesseract is installed (optional), whether an API key is available (optional) — report, don't assume. 3. Execute **Phase 0** only. Present its Phase Review Report and wait for approval before committing/pushing. After successful commit/push, stop; do not begin Phase 1 until the user explicitly instructs you to continue. 4. Begin every later session with the session-start checklist in §1.1.

## 7. DEFINITION OF "GOOD" FOR THIS PROJECT  
- Every claim is backed by a test or a real measurement.
- The engine never uses future data.
- The indicator explains *why* it says what it says.
- Failures are first-class citizens (detected, drawn, and counted).
- A new model can pick up the work from `HANDOFF.md` in under 5 minutes. \
&#x20;&#x20;