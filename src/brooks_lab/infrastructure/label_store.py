"""Label persistence with taxonomy migrations (P6, plan step S2).

The loader auto-migrates legacy taxonomy ids on read so enum changes never
invalidate stored label files. Migration rules live in
``config/taxonomy_migrations.yaml``; lossy migrations set ``needs_review``
and keep the original wording in ``raw_label``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from brooks_lab.domain.labels import DayLabel, DayType, EventKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MigrationRule:
    """One old-id -> new-id mapping with its quality."""

    to: str | None
    quality: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Outcome of migrating one id (``None`` value = unmapped, keep raw)."""

    value: str | None
    quality: str
    changed: bool


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

    def apply_to_label(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Rewrite legacy ids inside a raw label dict (never drops raw_label)."""
        migrated = dict(payload)
        day_raw = migrated.get("day_type")
        if isinstance(day_raw, str):
            result = self.migrate_day_type(day_raw)
            if result.changed:
                migrated["day_type"] = result.value or "other"
                if result.quality == "lossy":
                    migrated["needs_review"] = True
        events: list[dict[str, Any]] = []
        for event in migrated.get("events") or []:
            if not isinstance(event, dict):
                events.append(event)
                continue
            event = dict(event)
            label_raw = event.get("label")
            if isinstance(label_raw, str):
                result = self.migrate_event(label_raw)
                if result.changed:
                    event["label"] = result.value
                    if result.quality == "lossy":
                        event["needs_review"] = True
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
            rules[str(old_id)] = MigrationRule(
                to=None if spec.get("to") is None else str(spec["to"]),
                quality=quality,
                note=str(spec.get("note", "")),
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
