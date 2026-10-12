"""Application service: scan a data dir into a validated manifest plus statistics."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from brooks_lab.domain.clock import Clock, SystemClock
from brooks_lab.domain.imaging import (
    MANIFEST_SCHEMA_VERSION,
    DateSource,
    ImageRecord,
    Manifest,
    RecordStatus,
    parse_filename_date,
)
from brooks_lab.infrastructure.image_probe import IMAGE_SUFFIXES, ImageProber, PillowProber
from brooks_lab.infrastructure.settings import IngestionSettings

logger = logging.getLogger(__name__)


class IngestionStats(BaseModel):
    """Aggregate report over one manifest. Persisted as JSON next to the manifest."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=MANIFEST_SCHEMA_VERSION, ge=1)
    total: int = 0
    ok: int = 0
    duplicates: int = 0
    corrupt: int = 0
    tiny: int = 0
    date_min: date | None = None
    date_max: date | None = None
    missing_dates: list[date] = Field(default_factory=list)
    formats: dict[str, int] = Field(default_factory=dict)
    width_buckets: dict[str, int] = Field(default_factory=dict)
    duplicate_files: list[str] = Field(default_factory=list)
    phash_collisions: list[list[str]] = Field(default_factory=list)


def _width_bucket(width: int) -> str:
    if width < 800:
        return "small<800"
    if width < 1600:
        return "medium<1600"
    return "large>=1600"


def compute_stats(manifest: Manifest) -> IngestionStats:
    """Compute aggregate statistics over ``manifest`` records (pure function)."""
    status_counts = Counter(r.status for r in manifest.records)
    dates = sorted(r.date for r in manifest.records if r.date is not None)
    missing: list[date] = []
    if dates:
        day = dates[0]
        known = set(dates)
        while day <= dates[-1]:
            if day not in known:
                missing.append(day)
            day += timedelta(days=1)
    phash_groups: dict[str, list[str]] = {}
    for record in manifest.records:
        if record.phash:
            phash_groups.setdefault(record.phash, []).append(record.filename)
    collisions = sorted(g for g in phash_groups.values() if len({f for f in g}) > 1)
    return IngestionStats(
        total=len(manifest.records),
        ok=status_counts.get(RecordStatus.OK, 0),
        duplicates=status_counts.get(RecordStatus.DUPLICATE, 0),
        corrupt=status_counts.get(RecordStatus.CORRUPT, 0),
        tiny=status_counts.get(RecordStatus.TINY, 0),
        date_min=dates[0] if dates else None,
        date_max=dates[-1] if dates else None,
        missing_dates=missing,
        formats=dict(sorted(Counter(r.format or "?" for r in manifest.records).items())),
        width_buckets=dict(
            sorted(Counter(_width_bucket(r.width) for r in manifest.records).items())
        ),
        duplicate_files=sorted(
            r.filename for r in manifest.records if r.status is RecordStatus.DUPLICATE
        ),
        phash_collisions=[sorted(g) for g in collisions],
    )


class ImageIngestionService:
    """Scan ``data_dir`` and build a validated :class:`Manifest`.

    Idempotent: identical inputs (plus an injected :class:`Clock`) produce
    byte-identical manifest JSON. Re-running never duplicates entries.
    """

    def __init__(
        self,
        settings: IngestionSettings | None = None,
        prober: ImageProber | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Wire dependencies (constructor injection; testable fakes welcome)."""
        self._settings = settings or IngestionSettings()
        self._prober = prober or PillowProber()
        self._clock: Clock = clock or SystemClock()

    def scan(self, data_dir: Path) -> Manifest:
        """Scan ``data_dir`` and return a manifest covering 100% of image files."""
        files = sorted(
            p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        )
        records: list[ImageRecord] = []
        seen_sha: dict[str, str] = {}
        for path in files:
            probe = self._prober.probe(path)
            parsed = parse_filename_date(path.name)
            date_source = DateSource.FILENAME if parsed is not None else DateSource.UNKNOWN
            if not probe.ok:
                records.append(
                    ImageRecord(
                        image_id=probe.image_id or f"unreadable-{path.name}",
                        filename=path.name,
                        sha256=probe.sha256 or ("0" * 64),
                        date=parsed,
                        date_source=date_source,
                        status=RecordStatus.CORRUPT,
                    )
                )
                continue
            duplicate_of = seen_sha.get(probe.sha256)
            if duplicate_of is not None:
                status = RecordStatus.DUPLICATE
            elif probe.width < self._settings.min_width or probe.height < self._settings.min_height:
                status = RecordStatus.TINY
            else:
                status = RecordStatus.OK
                seen_sha[probe.sha256] = probe.image_id
            records.append(
                ImageRecord(
                    image_id=probe.image_id,
                    filename=path.name,
                    sha256=probe.sha256,
                    phash=probe.phash,
                    width=probe.width,
                    height=probe.height,
                    format=probe.format,
                    date=parsed,
                    date_source=date_source,
                    title_text=None,
                    status=status,
                    duplicate_of=duplicate_of,
                )
            )
        return Manifest(generated_at=self._clock.now(), records=records)

    def scan_and_write(self, data_dir: Path, manifest_path: Path) -> Manifest:
        """Scan and atomically write the manifest JSON. Returns the manifest."""
        manifest = self.scan(data_dir)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True)
        payload += "\n"
        fd, tmp_name = tempfile.mkstemp(
            dir=str(manifest_path.parent), prefix=manifest_path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, manifest_path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                logger.warning("Could not remove temp manifest %s.", tmp_name)
            raise
        logger.info("Wrote manifest with %d records to %s.", len(manifest.records), manifest_path)
        return manifest

    @staticmethod
    def read_manifest(manifest_path: Path) -> Manifest:
        """Read and validate a manifest file (raises on schema violations)."""
        return Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def write_stats(stats: IngestionStats, output_path: Path) -> None:
        """Write stats JSON next to the manifest (atomic write)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(stats.model_dump(mode="json"), indent=2, sort_keys=True)
        payload += "\n"
        fd, tmp_name = tempfile.mkstemp(
            dir=str(output_path.parent), prefix=output_path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, output_path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                logger.warning("Could not remove temp stats %s.", tmp_name)
            raise
