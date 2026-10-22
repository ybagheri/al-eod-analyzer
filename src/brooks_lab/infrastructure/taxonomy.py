"""Taxonomy loader and normaliser (vocabulary v1, frozen by ADR-004).

Maps free-form annotator wording to canonical ids. Anything unmapped returns
``None`` so callers keep it in ``raw_label`` and route it to the review queue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from brooks_lab.domain.labels import (
    LABEL_SCHEMA_VERSION,
    DayType,
    EventKind,
    normalise_wording,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Taxonomy:
    """Frozen label vocabulary with synonym maps."""

    schema_version: int = LABEL_SCHEMA_VERSION
    taxonomy_version: str = ""
    day_types: frozenset[str] = field(default_factory=frozenset)
    events: frozenset[str] = field(default_factory=frozenset)
    day_type_synonyms: dict[str, str] = field(default_factory=dict)
    event_synonyms: dict[str, str] = field(default_factory=dict)

    def normalise_day_type(self, raw: str) -> DayType | None:
        """Map wording to a canonical day type, or ``None`` when unmapped."""
        key = normalise_wording(raw).replace(" ", "_")
        for candidate in (key, normalise_wording(raw)):
            if candidate in self.day_types:
                return DayType(candidate)
            if candidate in self.day_type_synonyms:
                return DayType(self.day_type_synonyms[candidate])
        return None

    def normalise_event(self, raw: str) -> EventKind | None:
        """Map wording to a canonical event, or ``None`` when unmapped."""
        key = normalise_wording(raw).replace(" ", "_")
        for candidate in (key, normalise_wording(raw)):
            if candidate in self.events:
                return EventKind(candidate)
            if candidate in self.event_synonyms:
                return EventKind(self.event_synonyms[candidate])
        return None


def _string_set(raw: object, field_name: str) -> frozenset[str]:
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return frozenset(raw)
    logger.warning("Taxonomy field %s is not a string list; ignoring.", field_name)
    return frozenset()


def _string_map(raw: object, field_name: str) -> dict[str, str]:
    if isinstance(raw, dict):
        clean = {
            normalise_wording(str(key)): str(value)
            for key, value in raw.items()
            if isinstance(value, str)
        }
        return clean
    logger.warning("Taxonomy field %s is not a mapping; ignoring.", field_name)
    return {}


def load_taxonomy(path: Path) -> Taxonomy:
    """Load and validate taxonomy v1. Raises on missing file or version mismatch."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"taxonomy {path} must be a mapping")
    version = raw.get("schema_version", 0)
    if version != LABEL_SCHEMA_VERSION:
        raise ValueError(f"taxonomy {path} schema_version {version} != {LABEL_SCHEMA_VERSION}")
    return Taxonomy(
        schema_version=version,
        taxonomy_version=str(raw.get("taxonomy_version", "")),
        day_types=_string_set(raw.get("day_types"), "day_types"),
        events=_string_set(raw.get("events"), "events"),
        day_type_synonyms=_string_map(raw.get("day_type_synonyms", {}), "day_type_synonyms"),
        event_synonyms=_string_map(raw.get("event_synonyms", {}), "event_synonyms"),
    )
