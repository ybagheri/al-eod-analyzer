# DECISIONS (ADR log)

## ADR-001 — Tech stack and quality gate (2026-10-11, accepted)

- Context: Phase 0 must fix the stack so later phases (extraction → engine → MQL5)
  share one toolchain on Windows with restricted internet.
- Decision: Python 3.11+ (PEP 621 `pyproject.toml`, `src` layout, `brooks` console
  script); domain-driven layers; Pydantic v2 schemas; Typer CLI + Rich output;
  ruff (lint+format), mypy `--strict`, pytest + coverage (fail-under 85) +
  Hypothesis; `python -m tasks check` as the canonical gate on Windows
  (`make check` delegates to it); offline-first, network optional/pluggable.
- Alternatives: Poetry (rejected: extra installer, restricted net); Click (rejected:
  Typer gives types + docs with less code); flake8/black split (rejected: ruff does
  both, faster, offline wheel).
- Consequences: every commit must pass the gate; tests never touch paid/online APIs;
  all thresholds live in `config/*.yaml`.

## ADR-002 — Implementation strategy: file-exchange vision first (2026-10-11, accepted)

- Context: coding-agent hosts are not guaranteed free vision models; laptop GPU is
  weak (MX 355 2 GB); no API keys on this machine.
- Decision: Phase 3 starts with `FileExchangeVisionClient` (request/response JSON
  files, agent-in-the-loop), pluggable provider interface, model id recorded per
  extraction; 5-image pilot reviewed before full run; no training/fine-tuning in the
  initial plan; local vision only as a later benchmarked experiment.
- Consequences: extraction works with zero keys; provider/model must be verified at
  use time, never assumed.

## ADR-003 — HANDOFF self-reference convention (2026-10-12, accepted)

- Context: the protocol demands a truthful, current `HANDOFF.md` in every commit,
  but updating HANDOFF itself changes the repo, risking an endless commit loop.
- Decision: `HANDOFF.md` names the phase commit hash and the docs-sync commit hash
  (both already pushed); docs-sync commits are self-describing (`docs: ...`) and need
  no further follow-up. A one-behind header that names pushed commits is valid.
- Consequences: max one docs-sync commit per phase; headers stay truthful without
  regress.

## ADR-004 — Taxonomy v1 frozen; Pacific axis time; review-queue design (2026-10-12, accepted)

- Context: extraction (Phase 3) needs a controlled vocabulary and strict schema
  before any label is produced; Brooks chart axes show US Pacific time.
- Decision: freeze `config/taxonomy.yaml` as v1 (14 day types incl. `other`,
  38 event kinds, 4 outcomes, 3 directions, curated synonym maps). Times are stored
  as `HH:MM` plus `tz`, default `America/Los_Angeles`. Unmapped wording is kept in
  `raw_label` with `label=None` (validated: unmapped events require a raw label)
  and surfaced via a counted review queue with difflib merge suggestions.
- Alternatives: free-text labels (rejected: unmeasurable); forcing every wording
  into a canonical id (rejected: silent information loss).
- Consequences: taxonomy changes need a new schema version + ADR; `migrate_day_label`
  handles the pre-v1 camelCase stub shape only.

## ADR-005 — Pilot extraction by the coding agent via file exchange (2026-10-12, accepted)

- Context: no paid vision API is configured; the coding agent (Muse Spark via
  opencode) can view images directly, so it acted as the file-exchange reader for
  the 5-image pilot (model id `muse-spark-opencode`, prompt `extract_v1`).
- Decision: pilot labels are first-pass extractions by the agent, recorded with
  full provenance in `extraction_meta`; they are NOT yet human-reviewed ground
  truth (review + gold set are Phase 4). Standalone "Bear Surprise" with large
  bars was mapped to `major_bear_surprise` with moderated confidence (judgment
  call, raw wording preserved); genuinely novel wording (Triangle, HST, MTR, …)
  went to the review queue unmapped.
- Consequences: Phase 4 must independently review all 5 pilot labels; future
  extractions record their own provider/model ids for comparability.

## ADR-006 — Taxonomy v1.1: user-approved patterns (2026-10-12, accepted)

- Context: the 45-item review queue held real Brooks vocabulary (OO, ii, Triangle,
  TTR, HST, MTR, LLDB, traps). The user supplied definitions and approved merges.
- Decision: add 8 canonical ids (`outside_outside`, `inside_inside`, `triangle`,
  `tight_trading_range`, `head_and_shoulders_top`, `major_trend_reversal`,
  `lower_low_double_bottom`, `midday_reversal`) + synonyms; map traps to
  `failed_breakout` and trend-resumption to `breakout` (direction set by labeller:
  bear/bull from the wording); keep TBTL, Minor reversal, Midpoint of day,
  Measuring Gap, Minor LL/HL, H4/L4, Failed High 2, Late-test-of-Open unmapped.
  `HH DT` confirmed as Higher-High DT → interim parent `double_top`
  (dedicated id deferred to v1.2). Label schema stays v1 (additive, compatible);
  vocabulary tracked as `taxonomy_version: "1.1"`. Existing labels remapped via
  `review-apply` with reviewer "ybagheri (taxonomy v1.1)" — source=human is
  accurate because the canonical assignments are human decisions.
- Consequences: normaliser now also strips dots/parens (`Ext. Triangle` matches);
  engine Phase 6 must cover the new ids (esp. ii/oo/triangle/MTR detection).
