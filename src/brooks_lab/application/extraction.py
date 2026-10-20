"""Application layer: extraction prompt building, batch service, and reporting."""

from __future__ import annotations

import datetime
import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydField

from brooks_lab.application.schema_v3 import looks_like_v3, parse_v3_response
from brooks_lab.domain.imaging import Manifest
from brooks_lab.domain.labels import LABEL_SCHEMA_VERSION, DayLabel, ExtractionMeta
from brooks_lab.infrastructure.label_store import TaxonomyMigrations, load_day_label
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

    @property
    def taxonomy_version(self) -> str:
        """Vocabulary version carried by the attached taxonomy."""
        return self._taxonomy.taxonomy_version

    def _is_v3(self) -> bool:
        """True for the compact schema prompts (extract_v3, extract_day_v3)."""
        return self.prompt_version in ("extract_v3", "extract_day_v3")

    def _taxonomy_section(self) -> str:
        version = self._taxonomy.taxonomy_version or "1"
        section = (
            f"## Taxonomy v{version} (canonical ids only)\n\n"
            f"Day types: {', '.join(sorted(self._taxonomy.day_types))}\n\n"
            f"Events: {', '.join(sorted(self._taxonomy.events))}\n\n"
        )
        if self._is_v3():
            return section  # v3 responses use enum ids only, never synonyms.
        return (
            section
            + "Day-type synonyms: "
            + ", ".join(f"{k} -> {v}" for k, v in sorted(self._taxonomy.day_type_synonyms.items()))
            + "\n\nEvent synonyms: "
            + ", ".join(f"{k} -> {v}" for k, v in sorted(self._taxonomy.event_synonyms.items()))
            + "\n"
        )

    def _schema_section(self) -> str:
        if self._is_v3():
            return (
                "## Output schema (compact v3, strict)\n\n"
                "Object: image_id, scope_ok (bool), scope_note, day_type (enum id), "
                "day_type_conf (0..1), axis {style: pt_0630_1300|et_style_0900_1500|"
                "other|none, first_label, last_label}, anchors {open_dir_first_hour: "
                "up|down|flat, day_close_vs_open: above|below|near, "
                "high_of_day_bar_index_hint: int|null, low_of_day_bar_index_hint: "
                "int|null, n_bars_visible: int|null}, events[] (omit in the day-only "
                "pass). Bar indices count from the first bar of the shown session.\n"
                'Event: kind (enum id, or "unmapped" + non-empty raw_label), '
                "start_bar_index_hint (int >= 0), end_bar_index_hint (int|null), "
                "direction (bull|bear|neutral), outcome "
                "(success|fail|partial|unclear), conf (0..1), raw_label.\n"
            )
        return (
            "## Output schema (DayLabel v1, strict)\n\n"
            "Top-level: schema_version=1, image_id, date (YYYY-MM-DD), day_type, "
            "day_type_confidence (0..1), session_summary, events[], extraction_meta.\n"
            "Event: label (canonical event id or null) + raw_label (verbatim, required "
            "when label is null), direction (bull|bear|neutral), start_time/end_time "
            "({time HH:MM, tz}), bar_index_hint, price_hint, outcome "
            "(success|fail|partial|unclear), outcome_reason, confidence (0..1), "
            "evidence, source (vision|human|engine).\n"
        )

    def build(self, image_id: str, date_iso: str, provider: str, model_id: str) -> str:
        """Render a deterministic prompt for one image (pure function of inputs)."""
        context = (
            f"## This image\n\nimage_id: {image_id}\ndate: {date_iso}\n"
            f"provider: {provider}\nmodel_id: {model_id}\n"
        )
        return (
            f"{self._template}\n\n{self._taxonomy_section()}\n{self._schema_section()}\n{context}"
        )


class ExtractionReport(BaseModel):
    """Batch extraction outcome: counts, quality signals, and warnings."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = PydField(default=LABEL_SCHEMA_VERSION, ge=1)
    prompt_version: str = PROMPT_VERSION
    taxonomy_version: str = ""
    scanned: int = 0
    labeled: int = 0
    skipped: int = 0
    pending: int = 0
    quarantined: int = 0
    valid_rate: float = 0.0
    mean_day_confidence: float = 0.0
    mean_event_confidence: float = 0.0
    out_of_scope: int = PydField(
        default=0, description="Converted labels with scope_ok=False (not in stats)."
    )
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
    migrations: TaxonomyMigrations | None = None
    taxonomy_version: str = ""

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
            return load_day_label(path, self.migrations)
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

    def _validate(self, raw: Any, image_id: str, date: datetime.date | None = None) -> DayLabel:
        if not isinstance(raw, dict):
            raise VisionError("response must be a JSON object")
        payload: Any = raw
        if not looks_like_v3(raw) and self.migrations is not None:
            payload = self.migrations.apply_to_label(raw)
        try:
            if looks_like_v3(raw):
                label = parse_v3_response(
                    payload,
                    image_id=image_id,
                    provider=self.provider,
                    model_id=self.client.model_id,
                    taxonomy_version=self.taxonomy_version,
                    date=date,
                )
            else:
                label = DayLabel.model_validate(payload)
        except ValueError as exc:
            raise VisionError(f"schema validation failed: {exc}") from exc
        if label.image_id != image_id:
            raise VisionError(f"image_id mismatch: response {label.image_id!r} != {image_id!r}")
        if not label.extraction_meta.taxonomy_version:
            meta: ExtractionMeta = label.extraction_meta.model_copy(
                update={"taxonomy_version": self.taxonomy_version}
            )
            label = label.model_copy(update={"extraction_meta": meta})
        return label

    def _extract_one(
        self,
        image_id: str,
        filename: str,
        date_iso: str,
        date: datetime.date | None = None,
    ) -> DayLabel | None:
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
                return self._validate(raw, image_id, date)
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
        labeled = skipped = pending = out_of_scope = 0
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
                out_of_scope += self._accumulate(
                    existing, day_confs, event_confs, day_counts, event_counts
                )
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
                out_of_scope += self._accumulate(
                    existing, day_confs, event_confs, day_counts, event_counts
                )
                continue
            if existing is not None and not self.clobber_reviewed and record.image_id in gold_ids:
                skipped += 1
                warnings.append(
                    f"{record.image_id}: gold label kept (pass clobber_reviewed to re-extract)"
                )
                out_of_scope += self._accumulate(
                    existing, day_confs, event_confs, day_counts, event_counts
                )
                continue
            date_iso = record.date.isoformat() if record.date else "unknown"
            try:
                label = self._extract_one(record.image_id, record.filename, date_iso, record.date)
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
            out_of_scope += self._accumulate(
                label, day_confs, event_confs, day_counts, event_counts
            )
        quarantined = len(self.quarantine_reasons)
        done = labeled + skipped
        return ExtractionReport(
            prompt_version=self.prompt_builder.prompt_version,
            taxonomy_version=self.taxonomy_version,
            scanned=len(records),
            labeled=labeled,
            skipped=skipped,
            pending=pending,
            quarantined=quarantined,
            valid_rate=(done / len(records)) if records else 0.0,
            mean_day_confidence=_mean(day_confs),
            mean_event_confidence=_mean(event_confs),
            out_of_scope=out_of_scope,
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
    ) -> int:
        """Accumulate in-scope stats; returns 1 when the label is out-of-scope."""
        if label.scope_ok is False:
            return 1
        day_confs.append(label.day_type_confidence)
        day_counts[label.day_type.value] += 1
        for event in label.events:
            event_confs.append(event.confidence)
            event_counts[event.label.value if event.label else "unmapped"] += 1
        return 0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True, slots=True)
class BatchRequest:
    """A printable column prompt for one candidate chart of an extraction wave."""

    image_id: str
    filename: str
    date_iso: str
    prompt: str


@dataclass
class BatchService:
    """Pick the next N charts for the agent to label in one turn (S2.4).

    Order comes from the tier sample file (stratified, when present: a `.txt`
    of ids or a `.json` with an ``items``/``records`` list carrying
    ``image_id``); otherwise manifest order. Charts with an existing valid
    label, review history, or an already-filled response are never re-printed.
    """

    manifest: Manifest
    labels_dir: Path
    queue_dir: Path
    history_dir: Path | None = None
    sample_file: Path | None = None
    prompt_builder: ExtractionPromptBuilder | None = None
    provider: str = "file"
    model_id: str = "manual"

    def _sample_order(self) -> list[str] | None:
        if self.sample_file is None or not self.sample_file.is_file():
            return None
        text = self.sample_file.read_text(encoding="utf-8")
        if self.sample_file.suffix == ".json":
            payload = json.loads(text)
            entries: Any
            if isinstance(payload, dict):
                entries = payload.get("items", payload.get("records", []))
            else:
                entries = payload
            ids: list[str] = []
            for entry in entries:
                if isinstance(entry, dict) and entry.get("image_id"):
                    ids.append(str(entry["image_id"]))
                elif isinstance(entry, str):
                    ids.append(entry)
            return ids if ids else None
        ids = [line.strip() for line in text.splitlines() if line.strip()]
        return ids if ids else None

    def _has_label_skip(self, image_id: str) -> bool:
        path = self.labels_dir / f"{image_id}.json"
        return path.is_file()

    def _has_history(self, image_id: str) -> bool:
        if self.history_dir is None:
            return False
        return any(self.history_dir.glob(f"{image_id}.rev*.json"))

    def candidates(self) -> list[BatchRequest]:
        """All charts that still need a response, in wave order."""
        records = {r.image_id: r for r in self.manifest.records}
        order = self._sample_order()
        ordered_ids: list[str] = []
        if order is not None:
            known = [i for i in order if i in records]
            ordered_ids = known
        else:
            ordered_ids = [r.image_id for r in sorted(records.values(), key=lambda r: r.filename)]
        requests: list[BatchRequest] = []
        if self.prompt_builder is None:
            return requests
        for image_id in ordered_ids:
            record = records[image_id]
            if self._has_label_skip(image_id) or self._has_history(image_id):
                continue
            response_path = self.queue_dir / f"{image_id}.response.json"
            if response_path.is_file():
                continue  # filled; conversion is `brooks extract`'s job
            date_iso = record.date.isoformat() if record.date else "unknown"
            requests.append(
                BatchRequest(
                    image_id=image_id,
                    filename=record.filename,
                    date_iso=date_iso,
                    prompt=self.prompt_builder.build(
                        image_id, date_iso, self.provider, self.model_id
                    ),
                )
            )
        return requests

    def pending_responses(self) -> list[str]:
        """Ids with a request file but no label yet."""
        ids: list[str] = []
        for request_path in sorted(self.queue_dir.glob("*.request.json")):
            image_id = request_path.name.replace(".request.json", "")
            if (
                not (self.queue_dir / f"{image_id}.response.json").is_file()
                and not (self.labels_dir / f"{image_id}.json").is_file()
            ):
                ids.append(image_id)
        return ids
