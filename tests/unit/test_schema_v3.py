"""Unit tests: compact extraction schema v3 (parser + prompt builder)."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from brooks_lab.application.extraction import ExtractionPromptBuilder
from brooks_lab.application.schema_v3 import looks_like_v3, parse_v3_response
from brooks_lab.domain.labels import DayLabel
from brooks_lab.infrastructure.taxonomy import load_taxonomy

REPO = Path(__file__).resolve().parents[2]
TAXONOMY = load_taxonomy(REPO / "config" / "taxonomy.yaml")


def _v3_payload(image_id: str = "abc") -> dict[str, object]:
    return {
        "image_id": image_id,
        "scope_ok": True,
        "scope_note": "",
        "day_type": "trading_range",
        "day_type_conf": 0.7,
        "axis": {"style": "pt_0630_1300", "first_label": "06:35", "last_label": "12:55"},
        "anchors": {
            "open_dir_first_hour": "up",
            "day_close_vs_open": "above",
            "high_of_day_bar_index_hint": 55,
            "low_of_day_bar_index_hint": 12,
            "n_bars_visible": 78,
        },
        "events": [
            {
                "kind": "failed_breakout",
                "start_bar_index_hint": 20,
                "end_bar_index_hint": 26,
                "direction": "bull",
                "outcome": "success",
                "conf": 0.8,
                "raw_label": "bear trap",
            },
            {
                "kind": "unmapped",
                "start_bar_index_hint": 40,
                "direction": "neutral",
                "outcome": "unclear",
                "conf": 0.3,
                "raw_label": "2nd leg contracting TTR",
            },
        ],
    }


def _parse(payload: dict[str, object], image_id: str = "abc") -> DayLabel:
    return parse_v3_response(
        payload,
        image_id=image_id,
        provider="file",
        model_id="manual",
        taxonomy_version="1.3",
        date=datetime.date(2022, 7, 29),
    )


def test_looks_like_v3() -> None:
    assert looks_like_v3(_v3_payload()) is True
    assert looks_like_v3({"image_id": "x", "day_type_confidence": 0.5}) is False
    assert looks_like_v3("nope") is False


def test_parse_v3_full_payload() -> None:
    label = _parse(_v3_payload())
    assert isinstance(label, DayLabel)
    assert label.day_type.value == "trading_range"
    assert label.date == datetime.date(2022, 7, 29)
    assert label.scope_ok is True
    assert label.axis is not None and label.axis.style.value == "pt_0630_1300"
    assert label.anchors is not None
    assert label.anchors.day_close_vs_open.value == "above"
    assert label.anchors.high_of_day_bar_index_hint == 55
    assert label.extraction_meta.prompt_version == "extract_v3"
    assert label.extraction_meta.taxonomy_version == "1.3"
    first, second = label.events
    assert first.label is not None and first.label.value == "failed_breakout"
    assert first.direction.value == "bull"  # trap result, not the failed-down leg
    assert first.bar_index_hint == 20
    assert first.end_bar_index_hint == 26
    assert second.label is None
    assert second.raw_label == "2nd leg contracting TTR"
    assert second.needs_review is False


def test_parse_v3_day_only_payload() -> None:
    payload = _v3_payload()
    del payload["events"]
    label = _parse(payload)
    assert label.events == []


def test_parse_v3_rejects_bad_ids() -> None:
    good = _v3_payload()

    def bad(mutate: object) -> dict[str, object]:
        payload = dict(good)
        mutate(payload)  # type: ignore[operator]
        return payload

    cases = [
        lambda p: p.update(image_id="other"),  # scope mismatch via caller arg
        lambda p: p.update(scope_ok="yes"),
        lambda p: p.update(day_type="reversal_day"),
        lambda p: p.update(day_type_conf=1.5),
        lambda p: p.update(axis={"style": "nope"}),
        lambda p: p.update(anchors={"day_close_vs_open": "equal"}),
        lambda p: p.update(
            events=[{"kind": "no_such_pattern", "start_bar_index_hint": 1, "conf": 0.5}]
        ),
        lambda p: p.update(
            events=[{"kind": "unmapped", "start_bar_index_hint": 1, "conf": 0.5}]
        ),  # unmapped without raw_label
        lambda p: p.update(
            events=[{"kind": "h1", "start_bar_index_hint": "bar 12", "conf": 0.5}]
        ),  # bar hints are int-only
        lambda p: p.update(events=[{"kind": "h1", "start_bar_index_hint": -2, "conf": 0.5}]),
        lambda p: p.update(
            events=[{"kind": "h1", "start_bar_index_hint": 1, "conf": 0.5, "outcome": "win"}]
        ),
    ]
    for mutate in cases:
        with pytest.raises(ValueError):
            _parse(bad(mutate))


def test_parse_v3_image_id_mismatch() -> None:
    with pytest.raises(ValueError, match="image_id mismatch"):
        _parse(_v3_payload("other-id"))


def test_parse_v3_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        parse_v3_response(
            [1, 2],
            image_id="abc",
            provider="file",
            model_id="manual",
            taxonomy_version="1.3",
        )


def test_prompt_builder_v3_sections() -> None:
    builder = ExtractionPromptBuilder(REPO / "config" / "prompts" / "extract_v3.md", TAXONOMY)
    prompt = builder.build("abc", "2022-07-29", "file", "manual")
    assert "Taxonomy v1.3" in prompt
    assert "compact v3" in prompt
    assert "day_type_conf (0..1)" in prompt
    assert "synonyms" not in prompt.lower()
    assert builder.taxonomy_version == "1.3"

    day_builder = ExtractionPromptBuilder(
        REPO / "config" / "prompts" / "extract_day_v3.md", TAXONOMY
    )
    day_prompt = day_builder.build("abc", "2022-07-29", "file", "manual")
    assert "day-only" in day_prompt
    assert "omit in the day-only" in day_prompt


def test_prompt_builder_v1_unchanged() -> None:
    builder = ExtractionPromptBuilder(REPO / "config" / "prompts" / "extract_v1.md", TAXONOMY)
    prompt = builder.build("abc", "2022-07-29", "file", "manual")
    assert "DayLabel v1" in prompt
    assert "Day-type synonyms" in prompt
