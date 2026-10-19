# AGENTS.md — rules for any coding agent working on al-eod-analyzer

Plan of record: `docs/PLAN_V2.md` (it supersedes `docs/MASTER_PROMPT.md` wherever they conflict) (read the current step only after reading this file). Status: `docs/STATUS.yaml`.

## Non-negotiables
1. Talk to the user in **Persian**; code, docs, ADRs, commits, JSON in **English**.
2. Re-read this file and `docs/STATUS.yaml` at session start and every ~40 tool calls.
3. Do **one step at a time**; never start the next step before the current Definition of Done is evidenced in `docs/evidence/<step>.md`.
4. Do not change, skip, reorder, or relax the plan without an ADR **and** the user's explicit approval. If blocked: stop and ask in Persian; never improvise silently.
5. Gate before every commit: `python -m tasks check` (with `.venv` on PATH). Commit format: `S<k>: <summary>`. Update `HANDOFF.md` and `STATUS.yaml` before each commit. No `--no-verify`.
6. Work on branch `step/S<k>-<name>`; merge to `main` only after the user approves; tag `S<k>-done`.
7. Never write response JSON by hand or via PowerShell; use `brooks write-response`.
8. Never overwrite human-reviewed or gold labels; never run `brooks extract --clobber-reviewed`.
9. Gold-Test is frozen and may be read only by logged `brooks evaluate --split test` runs. No tuning on it.
10. No new taxonomy ids outside ADR + migration table. Taxonomy is v1.3.
11. The repo is **public** (user decision). Never commit images, market data, `data/`, `config/local.yaml`, secrets, or personal paths; `scripts/public_safety_scan.py` must pass (gate + CI, including full history). Never rewrite history without approval.
12. No profitability claims. Report real numbers with confidence intervals, or "insufficient data".
13. No paid/online API assumptions. File-exchange vision is the default.
14. **R-FINISH:** finish the labeling work already started (pending ~55 requests, pending reviews) first. **R-NEW:** any new chart sent to vision must have a date inside broker-data coverage, newest block first. Charts used to design the taxonomy/prompt never enter Gold-Test.

## Stop and wait at these USER CHECKPOINTS
B MT5 M5 export (symbol, coverage, CSV) · C similarity gate STOP outcome · D ambiguous dates · E each 25-chart Gold-Test review block · F end of engine iteration · plus: a flagged item in the public-safety history scan. (Checkpoint A is retired.)

## If you notice you deviated
Say so immediately in Persian, revert, and record it in the evidence file.

## Environment (details in `docs/PLAN_V2.md` §0A; real paths only in git-ignored `config/local.yaml`)
Windows + Alpari MT5. Symbols: `US500` (CFD), `SP500Z6` (futures, expires ~Dec 2026 — export early, archive raw CSVs). MT5 access is **read-only export only**: never trade, never change terminal/account settings, never delete or edit other files in the MT5 folders.
