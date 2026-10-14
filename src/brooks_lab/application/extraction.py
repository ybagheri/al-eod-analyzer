"""Application layer: extraction prompt building, batch service, and reporting."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydField

from brooks_lab.domain.imaging import Manifest
from brooks_lab.domain.labels import LABEL_SCHEMA_VERSION, DayLabel
from brooks_lab.infrastructure.taxonomy import Taxonomy
from brooks_lab.infrastructure.vision import (
    MissingResponseError,
    VisionClient,
    VisionError,
)

logger = logging.getLogger(__name__)

PROMPT_VERSION = "extract_v1"


class ExtractionPromptBuilder:
    """Build the versioned extraction prompt (template + taxonomy + schema)."""

    def __init__(self, template_path: Path, taxonomy: Taxonomy) -> None:
        """Load the prompt template and attach the frozen taxonomy."""
        self._template = template_path.read_text(encoding="utf-8")
        self._taxonomy = taxonomy
        self.prompt_version = template_path.stem

    def build(self, image_id: str, date_iso: str, provider: str, model_id: str) -> str:
        """Render a deterministic prompt for one image (pure function of inputs)."""
        taxonomy_section = (
            "## Taxonomy v1 (canonical ids only)\n\n"
            f"Day types: {', '.join(sorted(self._taxonomy.day_types))}\n\n"
            f"Events: {', '.join(sorted(self._taxonomy.events))}\n\n"
            "Day-type synonyms: "
            + ", ".join(f"{k} -> {v}" for k, v in sorted(self._taxonomy.day_type_synonyms.items()))
            + "\n\nEvent synonyms: "
            + ", ".join(f"{k} -> {v}" for k, v in sorted(self._taxonomy.event_synonyms.items()))
            + "\n"
        )
        schema_section = (
            "## Output schema (DayLabel v1, strict)\n\n"
            "Top-level: schema_version=1, image_id, date (YYYY-MM-DD), day_type, "
            "day_type_confidence (0..1), session_summary, events[], extraction_meta.\n"
            "Event: label (canonical event id or null) + raw_label (verbatim, required "
            "when label is null), direction (bull|bear|neutral), start_time/end_time "
            "({time HH:MM, tz}), bar_index_hint, price_hint, outcome "
            "(success|fail|partial|unclear), outcome_reason, confidence (0..1), "
            "evidence, source (vision|human|engine).\n"
        )
        context = (
            f"## This image\n\nimage_id: {image_id}\ndate: {date_iso}\n"
            f"provider: {provider}\nmodel_id: {model_id}\n"
        )
        return f"{self._template}\n\n{taxonomy_section}\n{schema_section}\n{context}"


class ExtractionReport(BaseModel):
    """Batch extraction outcome: counts, quality signals, and warnings."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = PydField(default=LABEL_SCHEMA_VERSION, ge=1)
    prompt_version: str = PROMPT_VERSION
    scanned: int = 0
    labeled: int = 0
    skipped: int = 0
    pending: int = 0
    quarantined: int = 0
    valid_rate: float = 0.0
    mean_day_confidence: float = 0.0
    mean_event_confidence: float = 0.0
    day_type_counts: dict[str, int] = PydField(default_factory=dict)
    event_counts: dict[str, int] = PydField(default_factory=dict)
    quarantined_files: list[str] = PydField(default_factory=list)
    warnings: list[str] = PydField(default_factory=list)


@dataclass
class ExtractionService:
    """Batch extraction over a manifest: resumable, retried, strictly validated."""

    manifest: Manifest
    data_dir: Path
    labels_dir: Path
    failed_dir: Path
    client: VisionClient
    prompt_builder: ExtractionPromptBuilder
    provider: str = "file"
    max_retries: int = 2
    backoff_base_s: float = 1.0
    quarantine_reasons: dict[str, str] = field(default_factory=dict)
    history_dir: Path | None = None
    gold_path: Path | None = None
    clobber_reviewed: bool = False

    def _label_path(self, image_id: str) -> Path:
        return self.labels_dir / f"{image_id}.json"

    def _has_history(self, image_id: str) -> bool:
        """True when a reviewed revision exists (never clobber by default)."""
        if self.history_dir is None:
            return False
        return any(self.history_dir.glob(f"{image_id}.rev*.json"))

    def _gold_ids(self) -> set[str]:
        """Load gold ids (empty when the registry is missing/invalid)."""
        if self.gold_path is None or not self.gold_path.is_file():
            return set()
        try:
            from brooks_lab.application.review import GoldSet

            return set(
                GoldSet.model_validate_json(self.gold_path.read_text(encoding="utf-8")).image_ids
            )
        except ValueError:
            logger.warning("Ignoring unreadable gold registry %s.", self.gold_path)
            return set()

    def _existing_label(self, image_id: str) -> DayLabel | None:
        path = self._label_path(image_id)
        if not path.is_file():
            return None
        try:
            return DayLabel.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def _sleep(self, attempt: int) -> None:
        delay = self.backoff_base_s * (2.0**attempt)
        if delay > 0:
            time.sleep(delay)

    def _quarantine(self, image_id: str, reason: str, raw: Any) -> None:
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        payload = {"image_id": image_id, "reason": reason, "response": raw}
        (self.failed_dir / f"{image_id}.error.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
        self.quarantine_reasons[image_id] = reason

    def _validate(self, raw: Any, image_id: str) -> DayLabel:
        if not isinstance(raw, dict):
            raise VisionError("response must be a JSON object")
        try:
            label = DayLabel.model_validate(raw)
        except ValueError as exc:
            raise VisionError(f"schema validation failed: {exc}") from exc
        if label.image_id != image_id:
            raise VisionError(f"image_id mismatch: response {label.image_id!r} != {image_id!r}")
        return label

    def _extract_one(self, image_id: str, filename: str, date_iso: str) -> DayLabel | None:
        """Extract one image; None means pending (file-exchange, response absent)."""
        prompt = self.prompt_builder.build(image_id, date_iso, self.provider, self.client.model_id)
        image_bytes = (self.data_dir / filename).read_bytes()
        last_error = "unknown"
        raw: Any = None
        for attempt in range(self.max_retries + 1):
            try:
                raw = self.client.extract(image_bytes, prompt, image_id=image_id)
            except MissingResponseError:
                return None
            except VisionError as exc:
                last_error = str(exc)
                self._sleep(attempt)
                continue
            try:
                return self._validate(raw, image_id)
            except VisionError as exc:
                last_error = f"{exc} (auto-repair: none available offline)"
                self._sleep(attempt)
        self._quarantine(image_id, last_error, raw)
        return None

    def run(self, limit: int | None = None, resume: bool = True) -> ExtractionReport:
        """Run the batch; returns a report and writes labels + quarantine files."""
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        records = sorted(self.manifest.records, key=lambda r: r.filename)
        if limit is not None:
            records = records[:limit]
        labeled = skipped = pending = 0
        warnings: list[str] = []
        gold_ids = self._gold_ids()
        day_confs: list[float] = []
        event_confs: list[float] = []
        day_counts: Counter[str] = Counter()
        event_counts: Counter[str] = Counter()
        for record in records:
            existing = self._existing_label(record.image_id) if resume else None
            if existing is not None and (
                existing.extraction_meta.prompt_version == self.prompt_builder.prompt_version
                and existing.extraction_meta.model_id == self.client.model_id
            ):
                skipped += 1
                self._accumulate(existing, day_confs, event_confs, day_counts, event_counts)
                continue
            if (
                existing is not None
                and not self.clobber_reviewed
                and self._has_history(record.image_id)
            ):
                skipped += 1
                warnings.append(
                    f"{record.image_id}: reviewed label kept "
                    "(history exists; pass clobber_reviewed to re-extract)"
                )
                self._accumulate(existing, day_confs, event_confs, day_counts, event_counts)
                continue
            if existing is not None and not self.clobber_reviewed and record.image_id in gold_ids:
                skipped += 1
                warnings.append(
                    f"{record.image_id}: gold label kept (pass clobber_reviewed to re-extract)"
                )
                self._accumulate(existing, day_confs, event_confs, day_counts, event_counts)
                continue
            date_iso = record.date.isoformat() if record.date else "unknown"
            try:
                label = self._extract_one(record.image_id, record.filename, date_iso)
            except OSError as exc:
                self._quarantine(record.image_id, f"unreadable image file: {exc}", None)
                continue
            if label is None:
                if record.image_id not in self.quarantine_reasons:
                    pending += 1
                continue
            if record.date is not None and label.date != record.date:
                warnings.append(
                    f"{record.image_id}: label date {label.date} != manifest {record.date}"
                )
            self._label_path(record.image_id).write_text(
                json.dumps(label.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            labeled += 1
            self._accumulate(label, day_confs, event_confs, day_counts, event_counts)
        quarantined = len(self.quarantine_reasons)
        done = labeled + skipped
        return ExtractionReport(
            prompt_version=self.prompt_builder.prompt_version,
            scanned=len(records),
            labeled=labeled,
            skipped=skipped,
            pending=pending,
            quarantined=quarantined,
            valid_rate=(done / len(records)) if records else 0.0,
            mean_day_confidence=_mean(day_confs),
            mean_event_confidence=_mean(event_confs),
            day_type_counts=dict(sorted(day_counts.items())),
            event_counts=dict(sorted(event_counts.items())),
            quarantined_files=sorted(self.quarantine_reasons),
            warnings=warnings,
        )

    @staticmethod
    def _accumulate(
        label: DayLabel,
        day_confs: list[float],
        event_confs: list[float],
        day_counts: Counter[str],
        event_counts: Counter[str],
    ) -> None:
        day_confs.append(label.day_type_confidence)
        day_counts[label.day_type.value] += 1
        for event in label.events:
            event_confs.append(event.confidence)
            event_counts[event.label.value if event.label else "unmapped"] += 1


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
