"""Validator-gated response writes (plan step S2.3, P5).

Agents must not hand-write response JSON into the extraction queue; they pipe
the payload through this service. It strictly validates the compact v3
response against the taxonomy, checks the manifest membership, and writes
atomically as BOM-less UTF-8 with LF. Reviewed (human-sourced) labels are
never clobbered.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brooks_lab.application.schema_v3 import parse_v3_response
from brooks_lab.domain.imaging import Manifest
from brooks_lab.infrastructure.label_store import load_day_label
from brooks_lab.infrastructure.taxonomy import Taxonomy

logger = logging.getLogger(__name__)

#: Top-level keys accepted in a compact v3 response (strict, no extras).
V3_RESPONSE_KEYS = frozenset(
    {"image_id", "scope_ok", "scope_note", "day_type", "day_type_conf", "axis", "anchors", "events"}
)

AXIS_KEYS = frozenset({"style", "first_label", "last_label"})
ANCHORS_KEYS = frozenset(
    {
        "open_dir_first_hour",
        "day_close_vs_open",
        "high_of_day_bar_index_hint",
        "low_of_day_bar_index_hint",
        "n_bars_visible",
    }
)
EVENT_KEYS = frozenset(
    {
        "kind",
        "start_bar_index_hint",
        "end_bar_index_hint",
        "direction",
        "outcome",
        "conf",
        "raw_label",
    }
)


@dataclass(frozen=True, slots=True)
class WriteResult:
    """Outcome of one gated response write."""

    image_id: str
    path: Path
    replaced: bool
    warnings: list[str] = field(default_factory=list)


class ResponseWriteError(Exception):
    """The response was rejected: nothing was written."""


def _strict_keys(obj: Any, allowed: frozenset[str], what: str) -> None:
    if not isinstance(obj, dict):
        raise ResponseWriteError(f"{what} must be an object")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ResponseWriteError(f"{what}: unknown keys {unknown} (schema drift?)")


@dataclass
class ResponseWriter:
    """Parse, validate, and atomically persist one queue response."""

    queue_dir: Path
    manifest: Manifest
    taxonomy: Taxonomy
    labels_dir: Path | None = None

    @property
    def taxonomy_version(self) -> str:
        return self.taxonomy.taxonomy_version

    # -- validation ---------------------------------------------------------

    def validate(self, text: str, image_id: str) -> dict[str, Any]:
        """Parse + strictly validate; returns the payload on success."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ResponseWriteError(f"response is not valid JSON: {exc}") from exc
        _strict_keys(payload, V3_RESPONSE_KEYS, "response")
        if payload.get("axis") is not None:
            _strict_keys(payload["axis"], AXIS_KEYS, "axis")
        if payload.get("anchors") is not None:
            _strict_keys(payload["anchors"], ANCHORS_KEYS, "anchors")
        events = payload.get("events", [])
        if not isinstance(events, list):
            raise ResponseWriteError("events must be an array")
        for index, event in enumerate(events):
            _strict_keys(event, EVENT_KEYS, f"events[{index}]")
        try:
            parse_v3_response(
                payload,
                image_id=image_id,
                provider="file",
                model_id="pending",
                taxonomy_version=self.taxonomy_version,
            )
        except ValueError as exc:
            raise ResponseWriteError(f"schema validation failed: {exc}") from exc
        validated: dict[str, Any] = payload
        return validated

    def _manifest_has(self, image_id: str) -> bool:
        return any(record.image_id == image_id for record in self.manifest.records)

    def _reviewed_label(self, image_id: str) -> bool:
        """True when the stored label carries human-sourced (reviewed) events."""
        if self.labels_dir is None:
            return False
        path = self.labels_dir / f"{image_id}.json"
        if not path.is_file():
            return False
        try:
            label = load_day_label(path)
        except ValueError:
            return False
        return any(event.source.value == "human" for event in label.events)

    # -- writing ------------------------------------------------------------

    def write(self, text: str, image_id: str, *, replace: bool = False) -> WriteResult:
        """Validate then atomically write ``<image_id>.response.json``."""
        payload = self.validate(text, image_id)
        if not self._manifest_has(image_id):
            raise ResponseWriteError(
                f"image_id {image_id!r} not in the manifest; refusing to write"
            )
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        path = self.queue_dir / f"{image_id}.response.json"
        existed = path.is_file()
        if existed:
            if not replace:
                raise ResponseWriteError(f"{path.name} already exists; pass --replace to overwrite")
            if self._reviewed_label(image_id):
                raise ResponseWriteError(
                    f"{path.name} backs a reviewed (human-sourced) label; refusing to overwrite"
                )
        _atomic_write_json(path, payload)
        return WriteResult(image_id=image_id, path=path, replaced=existed)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write canonical JSON atomically: temp file -> rename, UTF-8 (no BOM), LF."""
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    os.replace(tmp_path, path)
