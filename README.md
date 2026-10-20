# al-eod-analyzer

Extract Brooks-style structure from EOD review charts (S&P 500 Emini, M5), distil it
into a machine-readable playbook, and reproduce the reading with a deterministic
streaming engine — in Python (reference) and MQL5 (live indicator, later EA).

> **Honest framing:** the goal is to *behave similarly to Brooks's reading*, not an
> exact clone. His labels are made with hindsight after the day is over; a live
> indicator must decide with incomplete information, so it uses **provisional** labels
> (may change) and **confirmed** labels (final after enough bars). No profitability is
> promised; every claim must be backed by out-of-sample tests.

## Architecture

```text
images (data/, git-ignored)
  -> extraction (vision client, pluggable) -> labels (artifacts/labels/*.json)
  -> human review -> gold set -> market-data attach (MT5/CSV bars)
  -> streaming engine (src/brooks_lab/engine, on_bar, zero look-ahead)
  -> evaluation vs labels -> playbook (artifacts/playbook/playbook.json)
  -> MQL5 port (mql5/) -> EA (later) -> optional LLM commentary bridge
```

Layered Python package (`src/brooks_lab`): `domain` (pure models/rules) →
`application` (use-cases) → `infrastructure` (files/APIs/MT5/vision) →
`engine` (streaming) → `interfaces` (CLI/reports).

## Install

Requires Python 3.11+. Core deps: `typer`, `pydantic`, `PyYAML`, `Pillow` only.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Offline install (restricted network): `wheelhouse/` (git-ignored) holds every
wheel pinned in `requirements-lock.txt`:

```powershell
# (one-time, on an online machine)
python -m pip download -d wheelhouse --timeout 120 --retries 10 -r requirements-lock.txt
# (offline machine, fresh clone)
python -m pip install --no-index --find-links wheelhouse setuptools wheel
python -m pip install --no-index --find-links wheelhouse --no-build-isolation -e ".[dev]"
```

Never run a non-editable `pip install file:///...` inside the repo path
(shadow-import hazard; guarded by `tests/test_smoke.py`).

Extras: `vision` (httpx network providers), `vision-local` (opencv/pytesseract,
optional, unused by the pipeline), `data` (pandas/numpy, analysis only — never
imported by the engine). The engine package is enforced stdlib-only by
`tests/test_engine_purity.py` (MQL5 parity).

## Quick start

```powershell
brooks --version
python -m tasks check   # canonical quality gate (use instead of `make` on Windows)
```

Git hooks (plan-compliance) activate with `git config core.hooksPath .githooks`
(activated in this checkout); never bypass with `--no-verify`.

<!-- STATUS:BEGIN (generated from docs/STATUS.yaml; do not edit) -->

### Status (auto-generated from docs/STATUS.yaml)

- **Current step:** S2 - Extraction v3: compact schema, validator-gated writes, anchors (pending)
- **Steps done:** S0, S1
- **Steps in progress:** none
- **Last gate:** green (2026-10-20): ruff ok / format ok / mypy --strict ok / pytest green (233 collected) / coverage ~91%
- **Data:** 1678 unique batch-1 charts; 244 filled queue pairs (1 pending); 243 labels; gold 32
- **Market-data coverage:** none
- Updated: 2026-10-19

<!-- STATUS:END -->

## CLI reference (so far)

| Command | Description |
|---|---|
| `brooks --version` / `brooks version` | Show version |
| `brooks ingest` / `brooks manifest-stats` | Image inventory + stats |
| `brooks schema-export` | Dump the label JSON schema |
| `brooks extract` / `brooks extract-status` | File-exchange vision extraction |
| `brooks title-map` | Map batch-1 filename titles to provisional day types |
| `brooks review-queue` / `brooks review-apply` | Human review pages + apply corrections |

Later phases add: `data-check`, `attach-labels`, `coverage-probe`,
`write-response`, `extract-batch`, `evaluate`, `tune`, `live`.

## Plan of record

The project follows `docs/PLAN_V2.md` (master re-plan v2.6): tiered labels
(Bronze/Silver-Dev/Gold-Test), market-data-first scope driven by broker-feed
coverage, validator-gated label writes, and a public-repo safety policy
(`docs/PUBLIC_SAFETY.md`). `docs/MASTER_PROMPT.md` remains the architecture
reference; on conflicts `docs/PLAN_V2.md` wins (ADR-012).

## Config

- `config/default.yaml` — engine thresholds, session times, paths (single source
  for named parameters; no magic constants in code).
- `config/taxonomy.yaml` — label vocabulary, frozen v1.3 for bulk labeling
  (future ids only through ADR + `config/taxonomy_migrations.yaml`).
- `.env` (git-ignored; see `.env.example`) — optional API keys. Core flow works
  offline via file-exchange vision mode.

## Images

Put screenshots in `data/` (see `data/README.md`). They are git-ignored (third-party
copyrighted, personal research use). Derived label JSON may be committed.

## Testing

```powershell
pytest -q --cov=src --cov-fail-under=85
```

Tests never call paid/online APIs (fakes/recorded fixtures only).

## MQL5

`mql5/` holds the later indicator/EA port. Install: copy `mql5/` contents into the
MT5 data-folder `MQL5/` tree, compile in MetaEditor (see `docs/MT5_SETUP.md` once
Phase 9 lands).

## FAQ

- **Will this reproduce Brooks exactly?** No — provisional vs confirmed logic plus
  hindsight bias make exact cloning impossible; see framing above.
- **Do I need an API key?** No. File-exchange extraction works without one.
- **GPU for local vision?** Not required (MX 355 2 GB is a constraint; local vision is
  an optional later experiment, benchmarked first).

## License / legal

Code: MIT (see `pyproject.toml`). The Brooks-style chart images are third-party
material that is NOT distributed in this repository and is kept locally for
personal research only; broker market data is not redistributed; labels and the
playbook are the author's own derived annotations and statistics; the repo is
public by design and must stay public-safe (see `docs/PUBLIC_SAFETY.md`).
Contact for take-down requests.
