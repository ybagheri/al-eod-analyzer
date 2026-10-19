# ROADMAP

Plan of record: `docs/PLAN_V2.md` (master re-plan v2.6, ADR-012) — supersedes the
old phase table for the remaining work; finished predecessor phases are kept for
history. Status legend: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked.

## Status (auto-generated from docs/STATUS.yaml)

<!-- STATUS:BEGIN (generated from docs/STATUS.yaml; do not edit) -->

| S0 | Re-plan, doc sync, safety rails, privacy | ✅ done | `—` |
| S1 | Dependency and environment repair | ⬜ pending | `—` |
| S2 | Extraction v3: compact schema, validator-gated writes, anchors | ⬜ pending | `—` |
| S3 | Phase 5b: market data layer + session calendar + axis resolution | ⬜ pending | `—` |
| S4 | Phase 5c: date alignment and label->bar attachment | ⬜ pending | `—` |
| S5 | Phase 5a-reduced: Silver-Dev and Gold-Test labeling | ⬜ pending | `—` |
| S6 | Phase 6: Python streaming engine v0 | ⬜ pending | `—` |
| S7 | Phase 7: evaluation framework + first baseline report | ⬜ pending | `—` |
| S8 | Active-learning Hard set + engine iteration | ⬜ pending | `—` |
| S9 | Phase 8: playbook (stats with n and CIs) | ⬜ pending | `—` |
| S10 | Phase 9: MQL5 indicator with parity >= 98% | ⬜ pending | `—` |
| S11 | Phase 10: signals + EA + walk-forward | ⬜ pending | `—` |
| S12 | Phase 11 (optional) LLM commentary bridge | ⬜ pending | `—` |
| S13 | Phase 12: hardening and v1.0.0 | ⬜ pending | `—` |

<!-- STATUS:END -->

| Step | Name | Replaces | Parallel? |
|------|------|----------|-----------|
| S0 | Re-plan, doc sync, safety rails, privacy | new | no |
| S1 | Dependency and environment repair | new | with S0 |
| S2 | Extraction v3: compact schema, validator-gated writes, anchors | part of 5a | no |
| S3 | Phase 5b: market data layer + session calendar + axis resolution | 5b | no |
| S4 | Phase 5c: date alignment and label→bar attachment (bronze sanity checks) | 5b/5c | no |
| S5 | Phase 5a-reduced: Silver-Dev and Gold-Test labeling | 5a | parallel with S6 after S4 |
| S6 | Phase 6: Python streaming engine v0 (+ `PATTERN_SPEC.md`) | 6 | parallel with S5 after S4 |
| S7 | Phase 7: evaluation framework + first baseline report | 7 | no |
| S8 | Active-learning Hard set + engine iteration | new | no |
| S9 | Phase 8: playbook (stats with n and CIs) | 8 | no |
| S10 | Phase 9: MQL5 indicator with parity ≥ 98% | 9 | no |
| S11 | Phase 10: signals + EA + walk-forward | 10 | no |
| S12 | Phase 11 (optional) LLM commentary bridge | 11 | optional |
| S13 | Phase 12: hardening and `v1.0.0` | 12 | no |

## S0 — Definition of Done

- [x] Prompt saved (verbatim modulo personal-path redaction) as `docs/PLAN_V2.md`; SHA-256 in `docs/PLAN_V2.sha256`; ADR-012 written
- [x] `docs/STATUS.yaml` single source of truth + `scripts/sync_status.py` + drift test
- [x] Stale text fixed (README status/legal, ROADMAP Phase-0 checkbox, HANDOFF §1/§8)
- [x] `scripts/public_safety_scan.py` implemented; full-history scan run (1 finding — old MASTER_PROMPT.md blob with local MT5 paths; user chose to ACCEPT, no history rewrite); `docs/PUBLIC_SAFETY.md`; `.gitignore` hardened
- [x] `scripts/backup.py` + `python -m tasks backup` works (last 10 zips, outside repo, verified with a real run)
- [x] §8 enforcement: `.githooks/` (pre-commit/commit-msg/pre-push, `core.hooksPath .githooks`), CI `.github/workflows/gate.yml`, plan-compliance in `python -m tasks check`, plan-hash guard, evidence file `docs/evidence/S0.md`
- [x] Gate demonstrated FAILING on a modified `docs/PLAN_V2.md` (plan-hash guard message), then reverted

## Predecessor phases (pre-re-plan; DoD evidence in HANDOFF/CHANGELOG)

| Phase | Goal | Status | Commit |
|---|---|---|---|
| 0 — Bootstrap & governance | Clean working skeleton, tooling, `brooks --version`, gate green | ✅ done | `4338faa` |
| 1 — Image inventory & ingestion | Manifest of all images, contact sheet | ✅ done | `917beb1` |
| 2 — Taxonomy, label schema, glossary | Controlled vocabulary + strict `DayLabel` schema v1, glossary draft | ✅ done | `04e4d97` |
| 3 — Vision extraction pipeline | One validated `DayLabel` JSON per image (5-image pilot first) | ✅ done | `0c3ac41` |
| 4 — Human review & gold set | Trusted ground truth (gold 32/33, taxonomy v1.2) | ✅ done | `c57967c` |
| 5a — Batch-1 intake + title mapping + calibration waves 0&1 + bulk wave 2 | Superseded by S2/S5 after the v2.6 re-plan | ✅ done | `2300fe7` |

## Backlog / Ideas

- Local-vision benchmark (small Ollama model) — only after S2 (never part of the default path).
- Fine-tuning revisit — only if measured errors + dataset size justify it (separate ADR).
- (Add ideas here; never implement without promoting to a phase.)
