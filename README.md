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

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Quick start (Phase 0)

```powershell
brooks --version
python -m tasks check   # canonical quality gate (use instead of `make` on Windows)
```

`make check` runs the same gate on systems with `make`.

## CLI reference (so far)

| Command | Description |
|---|---|
| `brooks --version` / `brooks version` | Show version |

Later phases add: `ingest`, `manifest-stats`, `schema-export`, `extract`,
`extract-status`, `review-queue`, `review-apply`, `data-check`, `attach-labels`,
`evaluate`, `tune`, `live`.

## Config

- `config/default.yaml` — engine thresholds, session times, paths (single source
  for named parameters; no magic constants in code).
- `config/taxonomy.yaml` — label vocabulary (DRAFT stub; frozen as v1 in Phase 2).
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
Phase 9 lands). Nothing tradable exists yet — Phase 0 is skeleton only.

## FAQ

- **Will this reproduce Brooks exactly?** No — provisional vs confirmed logic plus
  hindsight bias make exact cloning impossible; see framing above.
- **Do I need an API key?** No. File-exchange extraction works without one.
- **GPU for local vision?** Not required (MX 355 2 GB is a constraint; local vision is
  an optional later experiment, benchmarked first).

## License / legal

Code: MIT (see `pyproject.toml`). Chart images in `data/` are third-party
copyrighted — personal research use only; keep this repo **private**.
