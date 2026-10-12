# ROADMAP

Status legend: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked.

| Phase | Goal | Status | Commit |
|---|---|---|---|
| 0 — Bootstrap & governance | Clean working skeleton, tooling, `brooks --version`, gate green | ✅ done | `4338faa` (pushed origin/main) |
| 1 — Image inventory & ingestion | Manifest of all images, contact sheet | ✅ done | `917beb1` (pushed origin/main) |
| 2 — Taxonomy, label schema, glossary | Controlled vocabulary + strict `DayLabel` schema v1, glossary draft | ✅ done | `04e4d97` (pushed origin/main) |
| 3 — Vision extraction pipeline | One validated `DayLabel` JSON per image (5-image pilot first) | 🟨 in progress (review pending) | — |
| 4 — Human review & gold set | Trusted ground truth, ≥30-image gold set | ⬜ not started | — |
| 5 — Market data layer | Real M5 bars, session calendar, label→bar attachment | ⬜ not started | — |
| 6 — Python pattern engine | Deterministic streaming engine + `PATTERN_SPEC.md` | ⬜ not started | — |
| 7 — Evaluation framework | Honest engine-vs-labels metrics, date-split, tuning harness | ⬜ not started | — |
| 8 — Playbook | Pattern statistics with n + CIs, `playbook.json` + `PLAYBOOK.md` | ⬜ not started | — |
| 9 — MQL5 indicator | Live chart product, parity ≥98% on golden vectors | ⬜ not started | — |
| 10 — Signals & EA | Strategies, risk-managed EA, walk-forward + honest report | ⬜ not started | — |
| 11 — Live AI commentary bridge (optional) | `state.json` → LLM commentary service | ⬜ not started | — |
| 12 — Hardening & release | Docs pass, `v1.0.0`, final metrics | ⬜ not started | — |

## Phase 0 — Definition of Done

- [x] Repo layout per spec (§2.4) created
- [x] `pyproject.toml`, tooling config, pre-commit, `.gitignore`, `.gitattributes` created
- [x] `README.md`, `ROADMAP.md`, `HANDOFF.md`, `CHANGELOG.md`, `docs/DECISIONS.md` created; prompt saved as `docs/MASTER_PROMPT.md`
- [x] `brooks --version` CLI + smoke test
- [x] `make check` / `python -m tasks check` passes on a fresh clone (verified 2026-10-11 in `.venv`; gate must run with venv on PATH)
- [ ] First commit made (BLOCKED: `git` not installed on this machine)

## Phase 1 — Definition of Done

- [x] Manifest covers 100% of images (5/5, all ok)
- [x] Stats report (count, date range, missing dates, sizes, duplicates) printed and saved

## Backlog / Ideas

- Local-vision benchmark (small Ollama model) — only after Phase 3 pilot.
- Fine-tuning revisit — only if measured errors + dataset size justify it (separate ADR).
- (Add ideas here; never implement without promoting to a phase.)
