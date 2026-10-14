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

## ADR-007 — Reviewer-driven schema extension + conventions (2026-10-12, accepted)

- Context: deep human review of 10 labels exposed systematic needs: text-vs-position
  certainty split, base+modifier composition (instead of id explosion), claim-based
  outcomes, result-direction, per-image clock incomparability, dateless images.
- Decision: (1) additive optional fields only — `modifiers`, `role` (EventRole:
  pattern/entry_signal/expectation/day_part/structure/exit_signal/day_phase),
  `label_explicit`, `placement`, `x_px`; `date` becomes optional (null = unverified
  on-chart). Label schema stays v1 (backward compatible both directions).
  (2) Conventions: outcome = did the label's claim happen; direction = result
  direction; evidence from current image only; stacked notes = one row;
  position from structure never text; qualified notes scored per claim.
  (3) Feed-timezone theory (PT vs Central feeds) recorded but NOT applied:
  times stay as-printed with PT default + note; Phase 5 resolves per feed.
  (4) Prompt `extract_v2.md` carries the five reviewer rules; CLI default moved
  to v2 (v1 labels keep their provenance; resume distinguishes by version).
- Consequences: engine/eval phases must use the split confidences and modifiers;
  price-anchors beyond `price_hint` deferred to Phase 5; support/resistance ids
  deferred to v1.2.

## ADR-008 — Review round 2: roles, bare surprise, prompt rules (2026-10-12, accepted)

- Context: round-2 review fixed directions/outcomes across 7 labels, demanded the
  reviewer `kind` axis (pattern/entry/advice/context/...) and exposed model-added
  words ("major", template-placement evidence).
- Decision: add EventRoles CONTEXT/ADVICE/BAR_PATTERN and EventKinds
  `bear_surprise` (bare text only; "Major" stays major) + `trend_line`; remap the
  bare cases (08-03, 08-09). Day types stay canonical (broad_bull_channel and
  reversal_day already exist — no free strings needed). Prompt v2 gains 13 rules
  (compound-note replaces context-clause; + identity/UI/marker/abbreviation/target/
  outcome/day-quality/advice/scale/reuse/level-check/numbers) plus the approved
  pattern glossary; v2 unused by any extraction yet, so no version bump.
  `outcome: null` for advice rows REJECTED (breaks rate math): use unclear +
  "no testable claim" reason. session_bar_no/label_tz_group/linked_to deferred.
- Consequences: extract now also skips gold labels without --clobber-reviewed;
  engine must treat direction as result-direction and outcome as claim-based.

## ADR-009 — Review round 3: resumption regime, new ids, observed mapping (2026-10-12, accepted)

- Context: round-3 review reworked 8 labels, fixed numbers throughout, and vetoed
  the Measuring-Gap demotion (drawn levels must stay as structures).
- Decision: add DayType `bull_trend_resumption` (TR open -> breakout -> resumption)
  and EventKinds `low_4` (fourth-entry signal) + `measuring_gap` (breakout gap
  with MM marker); taxonomy v1.2 (still schema v1, additive). Reviewer outcome
  words map as: observed/confirmed -> success (structure seen, NOT profitability),
  unverified -> unclear + reason, failed -> fail, partial -> partial. Bare
  "Bear Surprise" demotions stand except where drawn target lines exist (aa65
  veto: keep as structures). HST stays parent-mapped (double_top + alt note).
  Support/resistance/open-of-day/session_bar_no/linked_to/breakout_dir/H3 ids
  deferred again.
- Consequences: success rates measure annotation-claim fulfilment, never edge;
  Phase 7 must state this; engine needs the new regime/id coverage.
