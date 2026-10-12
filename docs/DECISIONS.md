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
