"""Integration tests: extraction service batch behaviour."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from brooks_lab.application.extraction import (
    ExtractionPromptBuilder,
    ExtractionService,
)
from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.infrastructure.taxonomy import Taxonomy, load_taxonomy
from brooks_lab.infrastructure.vision import FakeVisionClient, FileExchangeVisionClient


def _taxonomy() -> Taxonomy:
    return load_taxonomy(Path(__file__).resolve().parents[2] / "config" / "taxonomy.yaml")


def _builder(tmp_path: Path) -> ExtractionPromptBuilder:
    template = tmp_path / "extract_v1.md"
    template.write_text("# T\n", encoding="utf-8")
    return ExtractionPromptBuilder(template, _taxonomy())


def _manifest(*entries: tuple[str, str, str | None]) -> Manifest:
    records = [
        ImageRecord(
            image_id=image_id,
            filename=filename,
            sha256="0" * 64,
            date=datetime.date.fromisoformat(day) if day else None,
        )
        for image_id, filename, day in entries
    ]
    return Manifest(records=records)


def _label_dict(image_id: str, day: str = "2022-07-29") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "image_id": image_id,
        "date": day,
        "day_type": "spike_and_channel_bull",
        "day_type_confidence": 0.9,
        "session_summary": "s",
        "events": [
            {
                "label": "buy_the_close",
                "raw_label": "Buy The Close",
                "direction": "bull",
                "confidence": 0.8,
                "source": "vision",
            }
        ],
        "extraction_meta": {"provider": "fake", "model_id": "fake", "prompt_version": "extract_v1"},
    }


def _service(
    tmp_path: Path, manifest: Manifest, client: Any, builder: ExtractionPromptBuilder
) -> ExtractionService:
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    for record in manifest.records:
        (data / record.filename).write_bytes(b"fake-bytes")
    return ExtractionService(
        manifest=manifest,
        data_dir=data,
        labels_dir=tmp_path / "labels",
        failed_dir=tmp_path / "failed",
        client=client,
        prompt_builder=builder,
        provider="fake",
        backoff_base_s=0.0,
    )


def test_batch_success_resume_and_report(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a_2022_07_29.jpg", "2022-07-29"))
    builder = _builder(tmp_path)
    service = _service(
        tmp_path, manifest, FakeVisionClient(default_response=_label_dict("id-1")), builder
    )
    report = service.run()
    assert (report.scanned, report.labeled, report.skipped) == (1, 1, 0)
    assert report.pending == 0 and report.quarantined == 0
    assert report.valid_rate == 1.0
    assert report.mean_day_confidence == 0.9
    assert report.mean_event_confidence == 0.8
    assert report.day_type_counts == {"spike_and_channel_bull": 1}
    assert report.event_counts == {"buy_the_close": 1}
    assert (tmp_path / "labels" / "id-1.json").is_file()
    rerun = service.run()
    assert (rerun.labeled, rerun.skipped) == (0, 1)
    assert rerun.valid_rate == 1.0


def test_flaky_client_retries_then_succeeds(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a_2022_07_29.jpg", "2022-07-29"))
    client = FakeVisionClient(
        default_response=_label_dict("id-1"), failures_before_success=2, model_id="fake"
    )
    service = _service(tmp_path, manifest, client, _builder(tmp_path))
    report = service.run()
    assert report.labeled == 1 and report.quarantined == 0
    assert client.attempts == 3


def test_invalid_responses_quarantined_with_reason(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a.jpg", None))
    service = _service(
        tmp_path, manifest, FakeVisionClient(default_response={"nope": True}), _builder(tmp_path)
    )
    report = service.run()
    assert report.quarantined == 1 and report.labeled == 0
    assert report.quarantined_files == ["id-1"]
    error = json.loads((tmp_path / "failed" / "id-1.error.json").read_text(encoding="utf-8"))
    assert "schema validation failed" in error["reason"]


def test_image_id_mismatch_quarantined(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a.jpg", None))
    service = _service(
        tmp_path,
        manifest,
        FakeVisionClient(default_response=_label_dict("id-OTHER")),
        _builder(tmp_path),
    )
    report = service.run()
    assert report.quarantined == 1
    assert "mismatch" in (tmp_path / "failed" / "id-1.error.json").read_text(encoding="utf-8")


def test_date_mismatch_warns_but_labels(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a_2022-07-29.jpg", "2022-07-29"))
    response = _label_dict("id-1", day="2022-08-02")
    service = _service(
        tmp_path, manifest, FakeVisionClient(default_response=response), _builder(tmp_path)
    )
    report = service.run()
    assert report.labeled == 1
    assert len(report.warnings) == 1 and "id-1" in report.warnings[0]


def test_file_exchange_pending_then_collect(tmp_path: Path) -> None:
    manifest = _manifest(("id-1", "a_2022_07_29.jpg", "2022-07-29"))
    queue = tmp_path / "queue"
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "a_2022_07_29.jpg").write_bytes(b"fake-bytes")
    client = FileExchangeVisionClient(queue_dir=queue, model_id="tester")
    service = ExtractionService(
        manifest=manifest,
        data_dir=data,
        labels_dir=tmp_path / "labels",
        failed_dir=tmp_path / "failed",
        client=client,
        prompt_builder=_builder(tmp_path),
        provider="file",
        backoff_base_s=0.0,
    )
    first = service.run()
    assert (first.pending, first.labeled) == (1, 0)
    assert (queue / "id-1.request.json").is_file()
    response = _label_dict("id-1")
    response["extraction_meta"] = {
        "provider": "file",
        "model_id": "tester",
        "prompt_version": "extract_v1",
    }
    (queue / "id-1.response.json").write_text(json.dumps(response), encoding="utf-8")
    second = service.run()
    assert (second.labeled, second.pending) == (1, 0)
    assert (tmp_path / "labels" / "id-1.json").is_file()
