"""Integration tests: review-queue pages and review-apply CLI round trip."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from typer.testing import CliRunner

from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.domain.labels import DayLabel, DayType, EventKind, EventLabel, ExtractionMeta
from brooks_lab.interfaces.cli import app


def _write_label(labels_dir: Path, image_id: str) -> None:
    label = DayLabel(
        image_id=image_id,
        date=datetime.date(2022, 8, 4),
        day_type=DayType.TRADING_RANGE,
        day_type_confidence=0.4,
        events=[
            EventLabel(label=None, raw_label="Triangle", confidence=0.3),
            EventLabel(label=EventKind.WEDGE, raw_label="Wedge", confidence=0.9),
        ],
        extraction_meta=ExtractionMeta(provider="file", model_id="m", prompt_version="extract_v1"),
    )
    (labels_dir / f"{image_id}.json").write_text(label.model_dump_json(indent=2))


def test_review_queue_builds_pages_and_summary(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.jpg").write_bytes(b"x")
    manifest = Manifest(records=[ImageRecord(image_id="id-1", filename="a.jpg", sha256="0" * 64)])
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    _write_label(labels_dir, "id-1")
    taxonomy = Path(__file__).resolve().parents[2] / "config" / "taxonomy.yaml"
    result = CliRunner().invoke(
        app,
        [
            "review-queue",
            "--manifest",
            str(manifest_path),
            "--data-dir",
            str(data),
            "--labels-dir",
            str(labels_dir),
            "--taxonomy-file",
            str(taxonomy),
            "--gold-file",
            str(tmp_path / "gold.json"),
            "--review-dir",
            str(tmp_path / "review"),
            "--output",
            str(tmp_path / "review" / "summary.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "labels=1 gold=0 unmapped=1" in result.output
    page = tmp_path / "review" / "pages" / "id-1.html"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "Triangle" in text and "id-1" in text
    # Low-confidence items first: Triangle (0.3) precedes Wedge (0.9).
    assert text.index("Triangle") < text.index("Wedge")
    summary = json.loads((tmp_path / "review" / "summary.json").read_text())
    assert summary["stats"]["total"] == 1
    assert summary["review_queue"]["items"][0]["raw_label"] == "Triangle"


def test_review_apply_round_trip(tmp_path: Path) -> None:
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    _write_label(labels_dir, "id-1")
    corrections = tmp_path / "fix.json"
    corrections.write_text(
        json.dumps(
            {
                "image_id": "id-1",
                "day_type": "spike_and_channel_bull",
                "mark_gold": True,
                "reviewer": "tester",
            }
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        app,
        [
            "review-apply",
            str(corrections),
            "--labels-dir",
            str(labels_dir),
            "--history-dir",
            str(tmp_path / "history"),
            "--gold-file",
            str(tmp_path / "gold.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "applied=True" in result.output and "gold=True" in result.output
    revised = json.loads((labels_dir / "id-1.json").read_text())
    assert revised["day_type"] == "spike_and_channel_bull"
    assert (tmp_path / "history" / "id-1.rev1.json").is_file()
    gold = json.loads((tmp_path / "gold.json").read_text())
    assert gold["image_ids"] == ["id-1"]

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"image_id": "missing"}), encoding="utf-8")
    failed = CliRunner().invoke(app, ["review-apply", str(bad), "--labels-dir", str(labels_dir)])
    assert failed.exit_code == 1
