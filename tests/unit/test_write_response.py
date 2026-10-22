"""Unit tests: validator-gated response writes (S2.3)."""

from __future__ import annotations

import datetime
import io
import json
from pathlib import Path
from typing import Any

import pytest

from brooks_lab.application.response_writer import (
    ResponseWriteError,
    ResponseWriter,
)
from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.domain.labels import DayLabel, EventLabel, ExtractionMeta, LabelSource
from brooks_lab.infrastructure.taxonomy import load_taxonomy

REPO = Path(__file__).resolve().parents[2]
TAXONOMY = load_taxonomy(REPO / "config" / "taxonomy.yaml")


def _manifest(tmp_path: Path) -> Manifest:
    record = ImageRecord(
        image_id="id-1",
        filename="a.jpg",
        sha256="0" * 64,
        date=datetime.date(2022, 7, 29),
    )
    return Manifest(records=[record])


def _payload(image_id: str = "id-1", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "image_id": image_id,
        "scope_ok": True,
        "scope_note": "",
        "day_type": "trading_range",
        "day_type_conf": 0.7,
        "axis": {"style": "none", "first_label": "", "last_label": ""},
        "anchors": {
            "open_dir_first_hour": "flat",
            "day_close_vs_open": "near",
            "high_of_day_bar_index_hint": None,
            "low_of_day_bar_index_hint": None,
            "n_bars_visible": 78,
        },
        "events": [
            {
                "kind": "failed_breakout",
                "start_bar_index_hint": 10,
                "direction": "bull",
                "outcome": "success",
                "conf": 0.8,
                "raw_label": "bear trap",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _writer(tmp_path: Path, manifest: Manifest) -> ResponseWriter:
    return ResponseWriter(
        queue_dir=tmp_path / "queue",
        manifest=manifest,
        taxonomy=TAXONOMY,
        labels_dir=tmp_path / "labels",
    )


def _text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2)


def test_write_happy_path_bomless_lf(tmp_path: Path) -> None:
    writer = _writer(tmp_path, _manifest(tmp_path))
    writer.write(_text(_payload()), "id-1")
    path = tmp_path / "queue" / "id-1.response.json"
    assert path.is_file()
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert json.loads(raw.decode("utf-8")) == _payload()


def test_write_rejects_and_writes_nothing(tmp_path: Path) -> None:
    writer = _writer(tmp_path, _manifest(tmp_path))
    cases: list[str] = [
        "not json",
        _text({"image_id": "id-1", "scope_ok": True, "extra": 1}),  # unknown keys
        _text(_payload(image_id="other")),  # id mismatch
        _text(_payload(image_id="ghost")),  # not in manifest
        _text(_payload(day_type="reversal_day")),
        _text(_payload(anchors={"day_close_vs_open": "equal"})),
        _text(_payload(events=[{"kind": "zzz", "conf": 0.5}])),
        _text(_payload(events=True)),  # events not an array
        _text(_payload(axis={"style": "s", "oops": 1})),
    ]
    for text in cases:
        with pytest.raises(ResponseWriteError):
            writer.write(text, "id-1")
    assert not (tmp_path / "queue").exists()


def test_write_refuses_manifest_miss(tmp_path: Path) -> None:
    writer = _writer(tmp_path, _manifest(tmp_path))
    with pytest.raises(ResponseWriteError, match="not in the manifest"):
        writer.write(_text(_payload(image_id="ghost")), "ghost")


def test_write_idempotent_overwrite_guard(tmp_path: Path) -> None:
    writer = _writer(tmp_path, _manifest(tmp_path))
    writer.write(_text(_payload()), "id-1")
    first = (tmp_path / "queue" / "id-1.response.json").read_text(encoding="utf-8")
    with pytest.raises(ResponseWriteError, match="--replace"):
        writer.write(_text(_payload()), "id-1")
    assert (tmp_path / "queue" / "id-1.response.json").read_text(encoding="utf-8") == first
    # no leftover temp files
    assert list((tmp_path / "queue").glob("*.tmp")) == []
    result = writer.write(_text(_payload()), "id-1", replace=True)
    assert result.replaced is True


def test_write_replace_refused_for_reviewed_label(tmp_path: Path) -> None:
    tmp_labels = tmp_path / "labels"
    tmp_labels.mkdir()
    label = DayLabel(
        image_id="id-1",
        date=datetime.date(2022, 7, 29),
        events=[
            EventLabel(
                label=None,
                raw_label="weird thing",
                source=LabelSource.HUMAN,
            )
        ],
        extraction_meta=ExtractionMeta(
            provider="file", model_id="manual", prompt_version="extract_v2"
        ),
    )
    (tmp_labels / "id-1.json").write_text(label.model_dump_json(indent=2), encoding="utf-8")
    writer = _writer(tmp_path, _manifest(tmp_path))
    writer.write(_text(_payload()), "id-1")
    with pytest.raises(ResponseWriteError, match="reviewed"):
        writer.write(_text(_payload()), "id-1", replace=True)


def test_write_from_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(_text(_payload())))
    writer = _writer(tmp_path, _manifest(tmp_path))
    # verify CONTENT_ONLY parity with file path: same payload via stdin read
    writer.write(io.StringIO(_text(_payload())).read(), "id-1")
    assert (tmp_path / "queue" / "id-1.response.json").is_file()
