"""Compact response schema v3 parser (plan step S2.2).

Vision responses for ``extract_v3`` are compact, bar-index-first objects; the
parser validates them strictly against the taxonomy and converts to the
canonical ``DayLabel`` storage form. Invalid ids never force a wrong enum:
unknown event wording must use ``kind: "unmapped"`` with ``raw_label``.
"""

from __future__ import annotations

import datetime
from typing import Any

from brooks_lab.domain.labels import (
    Anchors,
    AxisInfo,
    AxisStyle,
    CloseVsOpen,
    DayLabel,
    DayType,
    Direction,
    EventKind,
    EventLabel,
    ExtractionMeta,
    OpenDir,
    Outcome,
)

V3_PROMPT_VERSION = "extract_v3"

_DIRECTION_VALUES = {item.value for item in Direction}
_OUTCOME_VALUES = {item.value for item in Outcome}


def looks_like_v3(payload: Any) -> bool:
    """Heuristic: compact v3 payloads carry ``anchors`` or ``day_type_conf``."""
    return isinstance(payload, dict) and (
        "anchors" in payload or "day_type_conf" in payload or "scope_ok" in payload
    )


def _int_or_none(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an int or null (got {value!r})")
    if value < 0:
        raise ValueError(f"{field} must be >= 0 (got {value!r})")
    return value


def _conf(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number in [0,1] (got {value!r})")
    conf = float(value)
    if not 0.0 <= conf <= 1.0:
        raise ValueError(f"{field} must be in [0,1] (got {conf!r})")
    return conf


def _enum(value: Any, choices: set[str], field: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{field} {value!r} is not one of {sorted(choices)}")
    return value


def _parse_axis(raw: Any) -> AxisInfo:
    if not isinstance(raw, dict):
        raise ValueError("axis must be an object")
    return AxisInfo(
        style=AxisStyle(_enum(raw.get("style"), {s.value for s in AxisStyle}, "axis.style")),
        first_label=str(raw.get("first_label", "")),
        last_label=str(raw.get("last_label", "")),
    )


def _parse_anchors(raw: Any) -> Anchors:
    if not isinstance(raw, dict):
        raise ValueError("anchors must be an object")
    return Anchors(
        open_dir_first_hour=OpenDir(
            _enum(
                raw.get("open_dir_first_hour"),
                {s.value for s in OpenDir},
                "anchors.open_dir_first_hour",
            )
        ),
        day_close_vs_open=CloseVsOpen(
            _enum(
                raw.get("day_close_vs_open"),
                {s.value for s in CloseVsOpen},
                "anchors.day_close_vs_open",
            )
        ),
        high_of_day_bar_index_hint=_int_or_none(
            raw.get("high_of_day_bar_index_hint"), "anchors.high_of_day_bar_index_hint"
        ),
        low_of_day_bar_index_hint=_int_or_none(
            raw.get("low_of_day_bar_index_hint"), "anchors.low_of_day_bar_index_hint"
        ),
        n_bars_visible=_int_or_none(raw.get("n_bars_visible"), "anchors.n_bars_visible"),
    )


def _parse_event(raw: Any, index: int) -> EventLabel:
    name = f"events[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError(f"{name}.kind must be a non-empty string")
    raw_label = str(raw.get("raw_label", "")).strip()
    if kind == "unmapped":
        if not raw_label:
            raise ValueError(f"{name}: kind 'unmapped' requires a non-empty raw_label")
        label: EventKind | None = None
    elif kind in {item.value for item in EventKind}:
        label = EventKind(kind)
    else:
        raise ValueError(f"{name}.kind {kind!r} is not a canonical event id (use 'unmapped')")
    if not raw_label:
        raw_label = kind
    end_hint = raw.get("end_bar_index_hint")
    outcome_raw = raw.get("outcome", "unclear")
    direction_raw = raw.get("direction", "neutral")
    return EventLabel(
        label=label,
        raw_label=raw_label,
        direction=Direction(_enum(direction_raw, _DIRECTION_VALUES, f"{name}.direction")),
        bar_index_hint=_int_or_none(
            raw.get("start_bar_index_hint"), f"{name}.start_bar_index_hint"
        ),
        end_bar_index_hint=(
            None if end_hint is None else _int_or_none(end_hint, f"{name}.end_bar_index_hint")
        ),
        outcome=Outcome(_enum(outcome_raw, _OUTCOME_VALUES, f"{name}.outcome")),
        confidence=_conf(raw.get("conf"), f"{name}.conf"),
    )


def parse_v3_response(
    payload: Any,
    *,
    image_id: str,
    provider: str,
    model_id: str,
    taxonomy_version: str,
    date: datetime.date | None = None,
) -> DayLabel:
    """Validate a compact v3 response and convert it to a ``DayLabel``.

    Raises ``ValueError`` on any schema/taxonomy violation so the caller can
    quarantine or reject the response before it ever reaches disk.
    """
    if not isinstance(payload, dict):
        raise ValueError("response must be a JSON object")
    payload_image_id = payload.get("image_id")
    if not isinstance(payload_image_id, str) or not payload_image_id:
        raise ValueError("response needs a non-empty image_id")
    if payload_image_id != image_id:
        raise ValueError(f"image_id mismatch: response {payload_image_id!r} != {image_id!r}")
    scope_ok = payload.get("scope_ok")
    if not isinstance(scope_ok, bool):
        raise ValueError("scope_ok must be a boolean")
    day_type_value = payload.get("day_type")
    if not isinstance(day_type_value, str) or day_type_value not in {
        item.value for item in DayType
    }:
        raise ValueError(f"day_type {day_type_value!r} is not a canonical day type")
    events_raw = payload.get("events", [])
    if events_raw is None:
        events_raw = []
    if not isinstance(events_raw, list):
        raise ValueError("events must be an array")
    if len(events_raw) > 200:
        raise ValueError("day labels carry at most 200 events")
    events = [_parse_event(raw, index) for index, raw in enumerate(events_raw)]
    return DayLabel(
        schema_version=1,
        image_id=image_id,
        date=date,
        day_type=DayType(day_type_value),
        day_type_confidence=_conf(payload.get("day_type_conf", 0.5), "day_type_conf"),
        session_summary="",
        scope_ok=scope_ok,
        scope_note=str(payload.get("scope_note", "")),
        axis=_parse_axis(payload.get("axis")),
        anchors=_parse_anchors(payload.get("anchors")),
        events=events,
        extraction_meta=ExtractionMeta(
            provider=provider,
            model_id=model_id,
            prompt_version=V3_PROMPT_VERSION,
            taxonomy_version=taxonomy_version,
        ),
    )
