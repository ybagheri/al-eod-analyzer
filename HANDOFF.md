# HANDOFF
_Last updated: 2026-10-11 by Muse Spark (opencode) — commit pre-commit_

## 1. Project in one paragraph

al-eod-analyzer extracts Brooks-style structure from EOD review charts (ES M5
screenshots in `data/`), distils it into a playbook, and reproduces the reading with
a deterministic streaming engine (Python reference + later MQL5 port). Phase 0 builds
the skeleton only; no extraction, engine, or trading logic exists yet.

## 2. Current status

- Current phase: 0 — Bootstrap & governance
- Phase status: in progress
- Last green quality gate: 2026-10-11 pre-commit (ruff ✓ / mypy --strict ✓ 7 files / pytest 5 passed / coverage 100%)

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

## 4. Decisions made (link to ADR numbers)

- ADR-001: tech stack (PEP 621, typer/pydantic, ruff/mypy/pytest, tasks.py gate) — see `docs/DECISIONS.md`.

## 5. Next actions (ordered, the very next step first)

1. USER: install Git for Windows, then in repo: `git init` (if needed) + connect `git@github.com:ybagheri/al-eod-analyzer.git`; verify `git --version`.
2. USER: reply APPROVE to allow commit + push of Phase 0 (commit msg: `chore: bootstrap Phase 0 skeleton, CLI, and quality gate`).
3. Next model/session: finish full `pip install -e ".[dev]"` (numpy/pandas/opencv-pending, slow net), re-run gate, then start Phase 1 only on user instruction.

## 6. Open questions / blockers

- Git not installed → cannot commit/push yet (user action: install Git for Windows).
- `make` absent on Windows → canonical gate is `python -m tasks check` (documented).
- No API keys, no Tesseract → fine for Phase 0; file-exchange mode planned for Phase 3.

## 7. Known issues / tech debt

- `config/taxonomy.yaml` is a draft stub (freezes in Phase 2) — low.
- `mql5/` contains stubs only — expected for Phase 0.
- Full `.[dev]` install incomplete: numpy/pandas/opencv-python/pytesseract/pre-commit
  NOT installed (12–44 MB wheels timed out on slow net); gate-relevant set + ruff/mypy
  installed. Fresh-clone install still declares them in `pyproject.toml` — medium.
- Gate MUST run with `.venv` on PATH (global mypy lacks typer) — documented in §9.

## 8. Data & artifact state

- Images in data/: 5 | Manifest entries: 0 (Phase 1)
- Labels extracted: 0/5 | Reviewed: 0 | Gold set: 0
- Market data coverage: none (Phase 5)
- Playbook version: none (Phase 8)

## 9. How to run / verify (copy-paste commands)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
brooks --version
python -m tasks check
```

## 10. Metrics snapshot (real numbers only; "NOT RUN" if unknown)

- Extraction: NOT RUN
- Engine vs labels (dev/test): NOT RUN
- Parity Python↔MQL5: NOT RUN

## 11. Rules reminder for the next model

- Read README, ROADMAP, DECISIONS first. Do not skip phases. Update this file before each commit.
