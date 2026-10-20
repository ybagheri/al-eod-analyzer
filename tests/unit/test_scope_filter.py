"""Unit tests: P11 scope filter (stats exclusion + scope report, S2.7)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from typer.testing import CliRunner

from brooks_lab.application.review import (
    compute_label_stats,
    compute_scope_report,
    in_scope,
)
from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.domain.labels import DayLabel, ExtractionMeta
from brooks_lab.interfaces.cli import app


def _label(image_id: str, scope_ok: bool | None = None) -> DayLabel:
    return DayLabel(
        image_id=image_id,
        day_type="trading_range",
        events=[],
        scope_ok=scope_ok,
        scope_note="" if scope_ok is not False else "crop screenshot",
        extraction_meta=ExtractionMeta(
            provider="file", model_id="manual", prompt_version="extract_v3"
        ),
    )


def test_in_scope_and_stats_exclusion() -> None:
    labels = [_label("a", True), _label("b", False), _label("c", True), _label("d", None)]
    assert [label.image_id for label in in_scope(labels)] == ["a", "c", "d"]
    stats = compute_label_stats(labels, set())
    assert stats.total == 3
    assert stats.out_of_scope == 1
    assert stats.day_type_counts == {"trading_range": 3}
    assert stats.events_per_day_mean == 0.0


def test_scope_report() -> None:
    labels = [_label("a", True), _label("b", False), _label("c", None), _label("d", False)]
    report = compute_scope_report(labels)
    assert report.total == 4
    assert report.in_scope == 1
    assert report.out_of_scope == 2
    assert report.unstamped == 1
    assert report.out_of_scope_ids == ["b", "d"]
    assert report.notes["b"] == "crop screenshot"


def test_scope_report_cli(tmp_path: Path) -> None:
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    for image_id, scope in (("a", True), ("b", False)):
        (labels_dir / f"{image_id}.json").write_text(
            _label(image_id, scope).model_dump_json(indent=2), encoding="utf-8"
        )
    record = ImageRecord(
        image_id="a", filename="a.jpg", sha256="0" * 64, date=datetime.date(2022, 7, 29)
    )
    record_b = ImageRecord(
        image_id="b", filename="b.jpg", sha256="1" * 64, date=datetime.date(2022, 7, 29)
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        Manifest(records=[record, record_b]).model_dump_json(indent=2), encoding="utf-8"
    )
    output = tmp_path / "scope_report.json"
    result = CliRunner().invoke(
        app,
        [
            "scope-report",
            "--manifest",
            str(manifest),
            "--labels-dir",
            str(labels_dir),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["total"] == 2
    assert payload["out_of_scope"] == 1
    assert payload["out_of_scope_ids"] == ["b"]
