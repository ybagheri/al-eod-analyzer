"""Label persistence with taxonomy migrations (P6, plan step S2; ADR-013).

The loader auto-migrates legacy taxonomy ids on read so enum changes never
invalidate stored label files. Migration rules live in
``config/taxonomy_migrations.yaml``; three qualities exist:

- ``exact``: meaning fully preserved; ``mapped_from``/``rule_id`` recorded.
- ``lossy`` (no handler): generic lossy rule -> needs_review + enumerated
  ``needs_review_reason`` (default ``lossy_migration``).
- handler-backed (``handler: <name>``): the rule is applied by code that can
  resolve compound ids from title/summary text per ADR-013.

Hard guarantees for every rule (ADR-013): ``raw_label`` is never dropped,
``mapped_from`` + ``rule_id`` are recorded and logged, and ``direction`` /
``outcome`` of a row are never changed.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from brooks_lab.domain.labels import (
    DayLabel,
    DayType,
    EventKind,
    NeedsReviewReason,
    SessionStartSource,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MigrationRule:
    """One old-id -> new-id mapping, optionally handler-backed."""

    to: str | None
    quality: str
    note: str = ""
    handler: str = ""
    section: str = "events"


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Outcome of migrating one id (``None`` value = unmapped, keep raw)."""

    value: str | None
    quality: str
    changed: bool


@dataclass(frozen=True, slots=True)
class HandlerContext:
    """Input a handler works on (the row plus migration provenance)."""

    rule: MigrationRule
    old_id: str
    rule_id: str
    taxonomy_version: str
    image_id: str
    day_text: str


DayHandler = Callable[[HandlerContext, dict[str, Any]], None]
EventFactory = Callable[[HandlerContext, dict[str, Any]], list[dict[str, Any]]]


def _mark(row: dict[str, Any], old_id: str, rule_id: str) -> None:
    """Record migration provenance on a row (ADR-013: mapped_from + rule_id)."""
    row["mapped_from"] = old_id
    row["rule_id"] = rule_id


def _add_modifier(row: dict[str, Any], modifier: str) -> None:
    modifiers = row.get("modifiers")
    if not isinstance(modifiers, list):
        modifiers = []
    if modifier not in modifiers:
        modifiers.append(modifier)
    row["modifiers"] = modifiers


def _flag(row: dict[str, Any], reason: NeedsReviewReason) -> None:
    row["needs_review"] = True
    row["needs_review_reason"] = reason.value


# --- day-type handlers -------------------------------------------------------


def _h_day_bull_channel(ctx: HandlerContext, payload: dict[str, Any]) -> None:
    """bull_channel: resolve style from title/summary text (ADR-013 D1)."""
    text = ctx.day_text.lower()
    if re.search(r"\bbroad\b", text):
        payload["day_type"] = DayType.BROAD_BULL_CHANNEL.value
    elif re.search(r"(?:\btight\b|small\s+pullback)", text):
        payload["day_type"] = DayType.SMALL_PULLBACK_BULL_TREND.value
    else:
        payload["day_type"] = DayType.BULL_CHANNEL.value
        _add_modifier(payload, "width_unspecified")
        _flag(payload, NeedsReviewReason.WIDTH_UNSPECIFIED)


def _h_day_from_open(ctx: HandlerContext, payload: dict[str, Any]) -> None:
    """small_pullback_*_trend_from_open: drop the id qualifier, keep the info."""
    target = ctx.rule.to
    payload["day_type"] = target if target is not None else DayType.OTHER.value
    if re.search(r"from\s+the\s+open", ctx.day_text, flags=re.IGNORECASE):
        payload["starts_at_session_open"] = True
        payload["starts_at_session_open_source"] = SessionStartSource.TITLE.value
    else:
        payload["starts_at_session_open"] = None
        payload["starts_at_session_open_source"] = SessionStartSource.NONE.value
        _flag(payload, NeedsReviewReason.MISSING_EVIDENCE)


def _h_day_direction_null(ctx: HandlerContext, payload: dict[str, Any]) -> None:
    """trending_trading_range: day regime direction unknowable from the id."""
    payload["day_type"] = DayType.OTHER.value
    _flag(payload, NeedsReviewReason.DIRECTION_MISSING)


def _h_day_regime_null(ctx: HandlerContext, payload: dict[str, Any]) -> None:
    """reversal_day: replaced by direction-specific ids (v1.3); PM regime unknown."""
    payload["day_type"] = DayType.OTHER.value
    _flag(payload, NeedsReviewReason.REGIME_DIRECTION_MISSING)


def _h_day_lossy_default(ctx: HandlerContext, payload: dict[str, Any]) -> None:
    """Any other lossy day rule: other + needs_review + enumerated reason."""
    payload["day_type"] = DayType.OTHER.value
    _flag(payload, NeedsReviewReason.LOSSY_MIGRATION)


# --- event handlers ----------------------------------------------------------


def _h_ev_low_2_top(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """low_2_top -> l2 + at_top (+ expectation noted in provenance)."""
    event["label"] = EventKind.L2.value
    _add_modifier(event, "at_top")
    if not str(event.get("outcome_reason") or "").strip():
        event["outcome_reason"] = "legacy id implied an expectation (low 2 at top); verify on chart"
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


def _h_ev_wedge_bull_channel(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """wedge_bull_channel -> channel + with_wedges (width kept as modifier)."""
    event["label"] = EventKind.CHANNEL.value
    _add_modifier(event, "with_wedges")
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


def _h_ev_triple_top(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """triple_top -> double_top + third touch; range-resistance alternative noted."""
    event["label"] = EventKind.DOUBLE_TOP.value
    _add_modifier(event, "third_touch")
    _flag(event, NeedsReviewReason.ALTERNATIVE_MAPPING)
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


def _h_ev_parabolic_wedge(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """parabolic_wedge -> wedge + parabolic; at_top/at_bottom by direction."""
    event["label"] = EventKind.WEDGE.value
    _add_modifier(event, "parabolic")
    if event.get("direction") == "bear":
        _add_modifier(event, "at_top")
    elif event.get("direction") == "bull":
        _add_modifier(event, "at_bottom")
    else:
        _flag(event, NeedsReviewReason.AMBIGUOUS_DIRECTION)
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


def _split_phase(base: dict[str, Any], phase: str, rule_id: str) -> dict[str, Any]:
    row = {k: v for k, v in base.items() if k not in ("mapped_from", "rule_id", "linked_to")}
    row["modifiers"] = list(base.get("modifiers") or [])
    row["label"] = EventKind.SPIKE.value if phase == "spike" else EventKind.CHANNEL.value
    counterpart = f"{rule_id}:{'channel' if phase == 'spike' else 'spike'}"
    row["linked_to"] = counterpart
    _add_modifier(row, f"{phase}_phase")
    _flag(row, NeedsReviewReason.AMBIGUOUS_BOUNDARY)
    return row


def _h_ev_spike_and_channel(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """spike_and_channel: split into spike + channel phases when title evidences it."""
    rule_id = f"{ctx.taxonomy_version}:spike_and_channel"
    if re.search(r"spike\s+(?:and|to|into)\s+channel", ctx.day_text, flags=re.IGNORECASE):
        spike = _split_phase(event, "spike", rule_id)
        channel = _split_phase(event, "channel", rule_id)
        _mark(spike, ctx.old_id, ctx.rule_id)
        _mark(channel, ctx.old_id, ctx.rule_id)
        return [spike, channel]
    event["label"] = None
    _flag(event, NeedsReviewReason.MISSING_EVIDENCE)
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


def _h_ev_day_type_as_event(ctx: HandlerContext, event: dict[str, Any]) -> list[dict[str, Any]]:
    """Day-type id used as an event: unmap but keep raw + enumerate the reason."""
    event["label"] = None
    _flag(event, NeedsReviewReason.DAY_TYPE_USED_AS_EVENT)
    _mark(event, ctx.old_id, ctx.rule_id)
    return [event]


handlers_by_name: dict[str, Callable[..., Any]] = {
    "day_bull_channel": _h_day_bull_channel,
    "day_from_open": _h_day_from_open,
    "day_direction_null": _h_day_direction_null,
    "day_regime_null": _h_day_regime_null,
    "day_lossy_default": _h_day_lossy_default,
    "ev_low_2_top": _h_ev_low_2_top,
    "ev_wedge_bull_channel": _h_ev_wedge_bull_channel,
    "ev_triple_top": _h_ev_triple_top,
    "ev_parabolic_wedge": _h_ev_parabolic_wedge,
    "ev_spike_and_channel": _h_ev_spike_and_channel,
    "ev_day_type_as_event": _h_ev_day_type_as_event,
}

# Attributes a migration must never touch or lose (ADR-013).
PROTECTED_EVENT_ATTRS = (
    "direction",
    "outcome",
    "outcome_reason",
    "start_time",
    "end_time",
    "bar_index_hint",
    "price_hint",
    "confidence",
    "label_explicit",
    "placement",
    "x_px",
    "evidence",
    "source",
)


@dataclass(frozen=True, slots=True)
class TaxonomyMigrations:
    """Migration table for one taxonomy version bump."""

    taxonomy_version: str
    day_types: dict[str, MigrationRule] = field(default_factory=dict)
    events: dict[str, MigrationRule] = field(default_factory=dict)

    def migrate_day_type(self, raw: str) -> MigrationResult:
        """Return the migration outcome for a day-type id."""
        rule = self.day_types.get(raw)
        if rule is not None:
            return MigrationResult(value=rule.to, quality=rule.quality, changed=True)
        if raw in {item.value for item in DayType}:
            return MigrationResult(value=raw, quality="exact", changed=False)
        logger.warning("Unknown day_type %r; demoting to 'other' with needs_review.", raw)
        return MigrationResult(value=None, quality="lossy", changed=True)

    def migrate_event(self, raw: str) -> MigrationResult:
        """Return the migration outcome for an event id."""
        rule = self.events.get(raw)
        if rule is not None:
            return MigrationResult(value=rule.to, quality=rule.quality, changed=True)
        if raw in {item.value for item in EventKind}:
            return MigrationResult(value=raw, quality="exact", changed=False)
        logger.warning("Unknown event id %r; demoting to unmapped with needs_review.", raw)
        return MigrationResult(value=None, quality="lossy", changed=True)

    def _apply_day_rule(self, rule: MigrationRule, old_id: str, payload: dict[str, Any]) -> None:
        rule_id = f"{self.taxonomy_version}:{old_id}"
        ctx = HandlerContext(
            rule=rule,
            old_id=old_id,
            rule_id=rule_id,
            taxonomy_version=self.taxonomy_version,
            image_id=str(payload.get("image_id") or ""),
            day_text=str(payload.get("session_summary") or "")
            + " "
            + str(payload.get("scope_note") or ""),
        )
        if rule.handler:
            handlers_by_name[rule.handler](ctx, payload)
        else:
            result = rule.to
            payload["day_type"] = result if result is not None else DayType.OTHER.value
            if rule.quality == "lossy":
                _flag(payload, NeedsReviewReason.LOSSY_MIGRATION)
        _mark(payload, old_id, rule_id)
        logger.info(
            "day_type %s -> %s via %s (image %s)",
            old_id,
            payload.get("day_type"),
            rule_id,
            ctx.image_id,
        )

    def _apply_event_rule(
        self, rule: MigrationRule, old_id: str, event: dict[str, Any], ctx: HandlerContext
    ) -> list[dict[str, Any]]:
        rule_id = f"{self.taxonomy_version}:{old_id}"
        before = {k: event.get(k) for k in PROTECTED_EVENT_ATTRS}
        if rule.handler:
            fn = handlers_by_name[rule.handler]
            rows = list(fn(ctx, event))
        else:
            event["label"] = rule.to
            if rule.quality == "lossy":
                _flag(event, NeedsReviewReason.LOSSY_MIGRATION)
            _mark(event, old_id, rule_id)
            rows = [event]
        for row in rows:
            for attr, old_value in before.items():
                if row.get(attr) != old_value and attr not in (
                    "label",
                    "outcome_reason",
                ):
                    logger.warning(
                        "migration %s changed protected attribute %s on %s",
                        rule_id,
                        attr,
                        ctx.image_id,
                    )
                    row[attr] = old_value
        logger.info(
            "event %s -> %s via %s (image %s)",
            old_id,
            event["label"],
            rule_id,
            ctx.image_id,
        )
        return rows

    def apply_to_label(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Rewrite legacy ids inside a raw label dict (never drops raw_label)."""
        migrated = dict(payload)
        day_raw = migrated.get("day_type")
        if isinstance(day_raw, str):
            rule = self.day_types.get(day_raw)
            if rule is not None:
                self._apply_day_rule(rule, day_raw, migrated)
            elif day_raw not in {item.value for item in DayType}:
                logger.warning(
                    "Unknown day_type %r; demoting to 'other' with needs_review.",
                    day_raw,
                )
                migrated["day_type"] = DayType.OTHER.value
                _flag(migrated, NeedsReviewReason.UNKNOWN_ID)
                _mark(migrated, day_raw, f"{self.taxonomy_version}:unknown_day_type")
        day_text = (
            str(migrated.get("session_summary") or "") + " " + str(migrated.get("scope_note") or "")
        )
        image_id = str(migrated.get("image_id") or "")
        events: list[dict[str, Any]] = []
        for event in migrated.get("events") or []:
            if not isinstance(event, dict):
                events.append(event)
                continue
            event = dict(event)
            label_raw = event.get("label")
            if isinstance(label_raw, str):
                rule = self.events.get(label_raw)
                if rule is not None:
                    ctx = HandlerContext(
                        rule=rule,
                        old_id=label_raw,
                        rule_id=f"{self.taxonomy_version}:{label_raw}",
                        taxonomy_version=self.taxonomy_version,
                        image_id=image_id,
                        day_text=day_text,
                    )
                    events.extend(self._apply_event_rule(rule, label_raw, event, ctx))
                    continue
                if label_raw not in {item.value for item in EventKind}:
                    logger.warning(
                        "Unknown event id %r; demoting to unmapped with needs_review.",
                        label_raw,
                    )
                    event["label"] = None
                    _flag(event, NeedsReviewReason.UNKNOWN_ID)
                    _mark(event, label_raw, f"{self.taxonomy_version}:unknown_event")
                    events.append(event)
                    continue
            events.append(event)
        migrated["events"] = events
        meta = dict(migrated.get("extraction_meta") or {})
        if not meta.get("taxonomy_version"):
            meta["taxonomy_version"] = self.taxonomy_version
        migrated["extraction_meta"] = meta
        return migrated


def load_migrations(path: Path) -> TaxonomyMigrations:
    """Load the migration table; raises on malformed entries."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"migrations {path} must be a mapping")
    if not str(raw.get("taxonomy_version", "")).strip():
        raise ValueError(f"migrations {path} needs a taxonomy_version")
    tables: dict[str, dict[str, MigrationRule]] = {}
    for section in ("day_types", "events"):
        rules: dict[str, MigrationRule] = {}
        entries = raw.get(section)
        if entries is None:
            entries = {}
        elif not isinstance(entries, dict):
            raise ValueError(f"migrations {path}: {section} must be a mapping")
        for old_id, spec in entries.items():
            if not isinstance(spec, dict) or "quality" not in spec:
                raise ValueError(f"migrations {path}: {section}/{old_id} needs a quality")
            quality = str(spec["quality"])
            if quality not in ("exact", "lossy"):
                raise ValueError(f"migrations {path}: {section}/{old_id} bad quality {quality!r}")
            handler = str(spec.get("handler", ""))
            if handler and handler not in handlers_by_name:
                raise ValueError(
                    f"migrations {path}: {section}/{old_id} unknown handler {handler!r}"
                )
            rules[str(old_id)] = MigrationRule(
                to=None if spec.get("to") is None else str(spec["to"]),
                quality=quality,
                note=str(spec.get("note", "")),
                handler=handler,
                section=section,
            )
        tables[section] = rules
    return TaxonomyMigrations(
        taxonomy_version=str(raw.get("taxonomy_version", "")),
        day_types=tables["day_types"],
        events=tables["events"],
    )


def load_day_label(path: Path, migrations: TaxonomyMigrations | None = None) -> DayLabel:
    """Load one label file, auto-migrating legacy ids when a table is given."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if migrations is not None:
        payload = migrations.apply_to_label(payload)
    return DayLabel.model_validate(payload)


def load_labels_dir(
    labels_dir: Path, migrations: TaxonomyMigrations | None = None
) -> list[DayLabel]:
    """Load every ``*.json`` label in a directory (migration-aware)."""
    if not labels_dir.is_dir():
        return []
    labels: list[DayLabel] = []
    for path in sorted(labels_dir.glob("*.json")):
        try:
            labels.append(load_day_label(path, migrations))
        except ValueError as exc:
            logger.warning("Skipping unreadable label %s: %s", path, exc)
    return labels
