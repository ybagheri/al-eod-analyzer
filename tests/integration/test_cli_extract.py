"""Integration tests: extract / extract-status CLI end to end."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.interfaces.cli import app


def _manifest(path: Path, image_id: str, filename: str) -> Path:
    record = ImageRecord(
        image_id=image_id,
        filename=filename,
        sha256="0" * 64,
        date=datetime.date(2022, 7, 29),
    )
    manifest = Manifest(records=[record])
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def _label(image_id: str, model: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "image_id": image_id,
        "date": "2022-07-29",
        "day_type": "trading_range",
        "day_type_confidence": 0.6,
        "session_summary": "chop",
        "events": [],
        "extraction_meta": {
            "provider": "file",
            "model_id": model,
            "prompt_version": "extract_v1",
        },
    }


def _base_args(tmp_path: Path, data: Path) -> list[str]:
    return [
        "--data-dir",
        str(data),
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--labels-dir",
        str(tmp_path / "labels"),
        "--queue-dir",
        str(tmp_path / "queue"),
        "--failed-dir",
        str(tmp_path / "failed"),
        "--prompt-file",
        str(Path(__file__).resolve().parents[2] / "config" / "prompts" / "extract_v1.md"),
        "--taxonomy-file",
        str(Path(__file__).resolve().parents[2] / "config" / "taxonomy.yaml"),
    ]


def test_file_provider_two_pass_flow(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.jpg").write_bytes(b"bytes")
    _manifest(tmp_path / "manifest.json", "id-1", "a.jpg")
    runner = CliRunner()

    first = runner.invoke(app, ["extract", "--provider", "file", *_base_args(tmp_path, data)])
    assert first.exit_code == 0, first.output
    assert "pending=1" in first.output
    assert (tmp_path / "queue" / "id-1.request.json").is_file()

    (tmp_path / "queue" / "id-1.response.json").write_text(
        json.dumps(_label("id-1", "manual")), encoding="utf-8"
    )
    second = runner.invoke(app, ["extract", "--provider", "file", *_base_args(tmp_path, data)])
    assert second.exit_code == 0, second.output
    assert "labeled=1" in second.output
    assert (tmp_path / "labels" / "id-1.json").is_file()

    status = runner.invoke(
        app,
        [
            "extract-status",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--labels-dir",
            str(tmp_path / "labels"),
            "--queue-dir",
            str(tmp_path / "queue"),
            "--failed-dir",
            str(tmp_path / "failed"),
        ],
    )
    assert status.exit_code == 0, status.output
    assert "manifest=1 labeled=1" in status.output


def test_fake_provider_quarantines_invalid(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.jpg").write_bytes(b"bytes")
    _manifest(tmp_path / "manifest.json", "id-1", "a.jpg")
    result = CliRunner().invoke(app, ["extract", "--provider", "fake", *_base_args(tmp_path, data)])
    assert result.exit_code == 0, result.output
    assert "quarantined=1" in result.output
    assert (tmp_path / "failed" / "id-1.error.json").is_file()


def test_unknown_provider_rejected(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["extract", "--provider", "nope"])
    assert result.exit_code != 0


def _init_repo(work: Path) -> None:
    import subprocess

    identity = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(
        [*identity, "commit", "--allow-empty", "-q", "-m", "init"],
        cwd=work,
        check=True,
    )


def test_guard_refuses_dirty_queue(tmp_path: Path) -> None:
    """Inside a real repo, uncommitted queue changes block extract (S2.4)."""
    import json as _json
    import subprocess

    work = tmp_path / "repo"
    (work / "queue").mkdir(parents=True)
    _init_repo(work)
    data = work / "data"
    data.mkdir()
    (data / "a.jpg").write_bytes(b"bytes")
    _manifest(work / "manifest.json", "id-1", "a.jpg")
    (work / "queue" / "id-1.response.json").write_text(
        _json.dumps(_label("id-1", "manual")), encoding="utf-8"
    )
    args = _base_args(work, data)
    runner = CliRunner()
    blocked = runner.invoke(app, ["extract", "--provider", "file", *args])
    assert blocked.exit_code == 1, blocked.output
    assert "refusing to run" in blocked.output
    # --allow-dirty overrides the guard.
    allowed = runner.invoke(app, ["extract", "--provider", "file", *args, "--allow-dirty"])
    assert allowed.exit_code == 0, allowed.output
    # Once committed, the guard opens (resume skips the already-converted label).
    identity = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run([*identity, "commit", "-q", "-m", "queue"], cwd=work, check=True)
    clean = runner.invoke(app, ["extract", "--provider", "file", *args])
    assert clean.exit_code == 0, clean.output
    assert "valid_rate=1.00" in clean.output
