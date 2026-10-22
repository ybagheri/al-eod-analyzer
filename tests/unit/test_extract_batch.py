"""Unit tests: extraction batch tooling (S2.4)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from brooks_lab.application.extraction import BatchService, ExtractionPromptBuilder
from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.domain.labels import DayLabel, ExtractionMeta
from brooks_lab.infrastructure.taxonomy import load_taxonomy

REPO = Path(__file__).resolve().parents[2]
TAXONOMY = load_taxonomy(REPO / "config" / "taxonomy.yaml")
BUILDER = ExtractionPromptBuilder(REPO / "config" / "prompts" / "extract_v3.md", TAXONOMY)


def _record(image_id: str, filename: str, date: str = "2022-07-29") -> ImageRecord:
    return ImageRecord(
        image_id=image_id,
        filename=filename,
        sha256="0" * 64,
        date=datetime.date.fromisoformat(date),
    )


def _manifest(count: int = 4) -> Manifest:
    records = [_record(f"id-{i}", f"{chr(ord('a') + i)}.jpg") for i in range(count)]
    return Manifest(records=records)


def _label(image_id: str) -> DayLabel:
    return DayLabel(
        image_id=image_id,
        extraction_meta=ExtractionMeta(
            provider="file", model_id="manual", prompt_version="extract_v3"
        ),
    )


def _service(tmp_path: Path, manifest: Manifest, sample_file: Path | None = None) -> BatchService:
    return BatchService(
        manifest=manifest,
        labels_dir=tmp_path / "labels",
        queue_dir=tmp_path / "queue",
        history_dir=tmp_path / "history",
        sample_file=sample_file,
        prompt_builder=BUILDER,
        model_id="my-model",
    )


def test_candidates_manifest_order(tmp_path: Path) -> None:
    batch = _service(tmp_path, _manifest()).candidates()
    assert [b.image_id for b in batch] == ["id-0", "id-1", "id-2", "id-3"]
    assert batch[0].date_iso == "2022-07-29"
    assert "compact v3" in batch[0].prompt


def test_candidates_skips_labels_history_and_responses(tmp_path: Path) -> None:
    (tmp_path / "labels").mkdir()
    (tmp_path / "labels" / "id-0.json").write_text(
        _label("id-0").model_dump_json(), encoding="utf-8"
    )
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "id-1.rev1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "queue").mkdir()
    (tmp_path / "queue" / "id-2.response.json").write_text("{}", encoding="utf-8")
    batch = _service(tmp_path, _manifest()).candidates()
    assert [b.image_id for b in batch] == ["id-3"]


def test_candidates_sample_order(tmp_path: Path) -> None:
    sample = tmp_path / "silver_dev.json"
    sample.write_text(
        json.dumps({"items": [{"image_id": "id-2"}, {"image_id": "id-0"}, {"image_id": "ghost"}]}),
        encoding="utf-8",
    )
    batch = _service(tmp_path, _manifest(), sample).candidates()
    assert [b.image_id for b in batch] == ["id-2", "id-0"]  # ghost and tail dropped


def test_candidates_txt_sample_order(tmp_path: Path) -> None:
    sample = tmp_path / "silver_dev.txt"
    sample.write_text("id-1\nid-3\n", encoding="utf-8")
    batch = _service(tmp_path, _manifest(), sample).candidates()
    assert [b.image_id for b in batch] == ["id-1", "id-3"]


def test_missing_sample_falls_back_to_manifest(tmp_path: Path) -> None:
    batch = _service(tmp_path, _manifest(), tmp_path / "nope.json").candidates()
    assert [b.image_id for b in batch] == ["id-0", "id-1", "id-2", "id-3"]


def test_pending_responses(tmp_path: Path) -> None:
    service = _service(tmp_path, _manifest())
    (tmp_path / "queue").mkdir()
    (tmp_path / "labels").mkdir()
    (tmp_path / "queue" / "id-1.request.json").write_text("{}", encoding="utf-8")
    (tmp_path / "queue" / "id-2.request.json").write_text("{}", encoding="utf-8")
    (tmp_path / "queue" / "id-2.response.json").write_text("{}", encoding="utf-8")
    (tmp_path / "labels" / "id-3.json").write_text(
        _label("id-3").model_dump_json(), encoding="utf-8"
    )
    assert service.pending_responses() == ["id-1"]
