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
