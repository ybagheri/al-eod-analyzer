"""Application layer: human-review workflow (corrections, history, gold set, stats).

Labels are never overwritten silently: every applied correction archives the
previous version under ``history_dir`` and marks touched content ``source=human``.
Gold status lives in a separate registry (no label-schema migration needed).
"""

from __future__ import annotations

import datetime
import itertools
import json
import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydField

from brooks_lab.domain.clock import Clock, SystemClock
from brooks_lab.domain.imaging import Manifest
from brooks_lab.domain.labels import (
    LABEL_SCHEMA_VERSION,
    DayLabel,
    Direction,
    EventKind,
    EventLabel,
    LabelSource,
)

logger = logging.getLogger(__name__)


class GoldSet(BaseModel):
    """Registry of human-reviewed gold labels (separate from the label schema)."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = PydField(default=LABEL_SCHEMA_VERSION, ge=1)
    reviewer: str = ""
    updated_at: datetime.datetime | None = None
    image_ids: list[str] = PydField(default_factory=list)
    notes: dict[str, str] = PydField(default_factory=dict)


class CorrectionsFile(BaseModel):
    """User corrections for one label. Omitted fields stay untouched.

    ``date`` uses explicit-null semantics: present-with-null clears the date,
    absent leaves it alone (checked via ``model_fields_set``).
    """

    model_config = ConfigDict(frozen=True)

    image_id: str = PydField(min_length=1)
    date: datetime.date | None = None
    day_type: str | None = None
    day_type_confidence: float | None = PydField(default=None, ge=0.0, le=1.0)
    session_summary: str | None = None
    events: list[EventLabel] | None = None
    mark_gold: bool = False
    reviewer: str = ""
    note: str = ""


class ApplyResult(BaseModel):
    """Outcome of applying one corrections file."""

    model_config = ConfigDict(frozen=True)

    image_id: str
    applied: bool
    revision: int = 0
    gold: bool = False
    message: str = ""


class EventRemap(BaseModel):
    """One taxonomy-migration rule: match by verbatim raw label, set a canonical id.

    Only events that are currently unmapped are touched, unless
    ``include_mapped`` is set (for demotions such as Measuring Gap → unmapped).
    """

    model_config = ConfigDict(frozen=True)

    raw_label: str = PydField(min_length=1)
    new_label: EventKind | None = None
    direction: Direction | None = None
    include_mapped: bool = False


class LabelStats(BaseModel):
    """Frequency and co-occurrence statistics over a label batch."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = PydField(default=LABEL_SCHEMA_VERSION, ge=1)
    total: int = 0
    day_type_counts: dict[str, int] = PydField(default_factory=dict)
    events_per_day_mean: float = 0.0
    event_counts: dict[str, int] = PydField(default_factory=dict)
    top_pairs: list[dict[str, Any]] = PydField(default_factory=list)
    gold_count: int = 0


def compute_label_stats(labels: list[DayLabel], gold_ids: set[str]) -> LabelStats:
    """Compute frequency/co-occurrence stats (pure function)."""
    day_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for label in labels:
        day_counts[label.day_type.value] += 1
        names = sorted({e.label.value if e.label else f"raw:{e.raw_label}" for e in label.events})
        for name in names:
            event_counts[name] += 1
        for first, second in itertools.combinations(names, 2):
            pair_counts[(first, second)] += 1
    top_pairs = [{"a": a, "b": b, "count": count} for (a, b), count in pair_counts.most_common(15)]
    total_events = sum(len(label.events) for label in labels)
    return LabelStats(
        total=len(labels),
        day_type_counts=dict(sorted(day_counts.items())),
        events_per_day_mean=(total_events / len(labels)) if labels else 0.0,
        event_counts=dict(sorted(event_counts.items())),
        top_pairs=top_pairs,
        gold_count=len(gold_ids & {label.image_id for label in labels}),
    )


def stratified_candidates(labels: list[DayLabel], per_type: int, seed: int = 7) -> list[str]:
    """Deterministically sample up to ``per_type`` image ids per day type.

    Same inputs + seed always give the same order (round-robin over day types).
    Used to propose an ordered gold-review queue.
    """
    groups: dict[str, list[str]] = {}
    for label in sorted(labels, key=lambda item: item.image_id):
        groups.setdefault(label.day_type.value, []).append(label.image_id)
    rng = random.Random(seed)
    for ids in groups.values():
        rng.shuffle(ids)
    picked: list[str] = []
    for round_robin in range(per_type):
        for day_type in sorted(groups):
            if round_robin < len(groups[day_type]):
                picked.append(groups[day_type][round_robin])
    return picked


@dataclass
class ReviewService:
    """Review workflow over a labels dir with history + gold registry."""

    labels_dir: Path
    history_dir: Path
    gold_path: Path
    clock: Clock = field(default_factory=SystemClock)
    reviewer: str = ""

    def label_path(self, image_id: str) -> Path:
        """Return the label file path for ``image_id``."""
        return self.labels_dir / f"{image_id}.json"

    def load_label(self, image_id: str) -> DayLabel:
        """Load and validate one label (raises on missing/invalid files)."""
        return DayLabel.model_validate_json(self.label_path(image_id).read_text(encoding="utf-8"))

    def load_gold(self) -> GoldSet:
        """Load the gold registry (empty when never created)."""
        if not self.gold_path.is_file():
            return GoldSet(reviewer=self.reviewer)
        return GoldSet.model_validate_json(self.gold_path.read_text(encoding="utf-8"))

    def _save_gold(self, gold: GoldSet) -> None:
        self.gold_path.parent.mkdir(parents=True, exist_ok=True)
        self.gold_path.write_text(
            json.dumps(gold.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _next_revision(self, image_id: str) -> int:
        existing = list(self.history_dir.glob(f"{image_id}.rev*.json"))
        return len(existing) + 1

    def apply_corrections(self, corrections: CorrectionsFile) -> ApplyResult:
        """Apply corrections: archive history, write new label, update gold.

        Never overwrites silently: the previous version is always archived first.
        Replaced events are marked ``source=human``.
        """
        path = self.label_path(corrections.image_id)
        if not path.is_file():
            return ApplyResult(
                image_id=corrections.image_id, applied=False, message="label not found"
            )
        current = DayLabel.model_validate_json(path.read_text(encoding="utf-8"))
        update: dict[str, Any] = {}
        if "date" in corrections.model_fields_set:
            update["date"] = corrections.date
        if corrections.day_type is not None:
            update["day_type"] = corrections.day_type
        if corrections.day_type_confidence is not None:
            update["day_type_confidence"] = corrections.day_type_confidence
        if corrections.session_summary is not None:
            update["session_summary"] = corrections.session_summary
        if corrections.events is not None:
            update["events"] = [
                event.model_copy(update={"source": LabelSource.HUMAN})
                for event in corrections.events
            ]
        try:
            # Validate the merged mapping directly: model_copy(update=...) would
            # store raw strings in enum fields and trip serializer warnings.
            merged: dict[str, Any] = current.model_dump(mode="python")
            merged.update(update)
            revised = DayLabel.model_validate(merged)
        except ValueError as exc:
            return ApplyResult(
                image_id=corrections.image_id, applied=False, message=f"invalid: {exc}"
            )
        revision = self._commit(corrections.image_id, revised)
        gold = self.load_gold()
        is_gold = corrections.image_id in gold.image_ids
        if corrections.mark_gold and not is_gold:
            notes = dict(gold.notes)
            if corrections.note:
                notes[corrections.image_id] = corrections.note
            gold = gold.model_copy(
                update={
                    "image_ids": sorted([*gold.image_ids, corrections.image_id]),
                    "notes": notes,
                    "reviewer": corrections.reviewer or gold.reviewer or self.reviewer,
                    "updated_at": self.clock.now(),
                }
            )
            self._save_gold(gold)
            is_gold = True
        logger.info("Applied corrections for %s (rev %d).", corrections.image_id, revision)
        return ApplyResult(
            image_id=corrections.image_id,
            applied=True,
            revision=revision,
            gold=is_gold,
            message=f"archived rev{revision}",
        )

    def _commit(self, image_id: str, revised: DayLabel) -> int:
        """Archive the current version and write ``revised``. Returns revision."""
        path = self.label_path(image_id)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        revision = self._next_revision(image_id)
        (self.history_dir / f"{image_id}.rev{revision}.json").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        path.write_text(
            json.dumps(revised.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return revision

    def remap_events(
        self, image_id: str, remaps: list[EventRemap], reviewer: str = ""
    ) -> ApplyResult:
        """Migrate matched events to new canonical ids (taxonomy updates).

        Only events whose ``raw_label`` matches a rule are touched (and only
        unmapped ones unless the rule sets ``include_mapped``); touched events
        are marked ``source=human`` because the canonical assignment is a human
        decision. Untouched events keep their source. No match → not applied.
        """
        path = self.label_path(image_id)
        if not path.is_file():
            return ApplyResult(image_id=image_id, applied=False, message="label not found")
        current = DayLabel.model_validate_json(path.read_text(encoding="utf-8"))
        table = {rule.raw_label: rule for rule in remaps}
        changed = 0
        kept: list[EventLabel] = []
        for event in current.events:
            rule = table.get(event.raw_label)
            if rule is None or (event.label is not None and not rule.include_mapped):
                kept.append(event)
                continue
            if event.label == rule.new_label and (
                rule.direction is None or event.direction == rule.direction
            ):
                kept.append(event)  # Already migrated: re-runs stay no-ops.
                continue
            update: dict[str, Any] = {"label": rule.new_label, "source": LabelSource.HUMAN}
            if rule.direction is not None:
                update["direction"] = rule.direction
            kept.append(event.model_copy(update=update))
            changed += 1
        if changed == 0:
            return ApplyResult(image_id=image_id, applied=False, message="no matches")
        try:
            merged: dict[str, Any] = current.model_dump(mode="python")
            merged["events"] = kept
            revised = DayLabel.model_validate(merged)
        except ValueError as exc:
            return ApplyResult(image_id=image_id, applied=False, message=f"invalid: {exc}")
        revision = self._commit(image_id, revised)
        logger.info("Remapped %d events for %s (rev %d).", changed, image_id, revision)
        return ApplyResult(
            image_id=image_id,
            applied=True,
            revision=revision,
            message=f"remapped {changed} events",
        )

    def history_revisions(self, image_id: str) -> list[int]:
        """List archived revision numbers for ``image_id`` (ascending)."""
        numbers: list[int] = []
        for path in self.history_dir.glob(f"{image_id}.rev*.json"):
            try:
                numbers.append(int(path.suffixes[0].replace(".rev", "")))
            except (ValueError, IndexError):
                continue
        return sorted(numbers)


def load_labels_for_manifest(manifest: Manifest, labels_dir: Path) -> list[DayLabel]:
    """Load validated labels for every manifest record that has one."""
    labels: list[DayLabel] = []
    for record in sorted(manifest.records, key=lambda r: r.filename):
        path = labels_dir / f"{record.image_id}.json"
        if path.is_file():
            labels.append(DayLabel.model_validate_json(path.read_text(encoding="utf-8")))
    return labels
