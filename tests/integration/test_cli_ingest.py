"""Integration tests: ingest and manifest-stats CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from brooks_lab.interfaces.cli import app


def _make_chart(path: Path) -> None:
    image = Image.new("RGB", (1280, 720), color="white")
    image.save(path, format="JPEG")


def test_ingest_then_stats(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _make_chart(data / "S&P500_Emini_M5_2022_07_29.jpg")
    config = tmp_path / "config.yaml"
    config.write_text("ingestion:\n  min_width: 400\n  min_height: 300\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    review = tmp_path / "review"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ingest",
            "--data-dir",
            str(data),
            "--manifest",
            str(manifest),
            "--config",
            str(config),
            "--review-dir",
            str(review),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "ingested 1 images" in result.output
    assert manifest.is_file()
    assert (review / "contact_sheet.html").is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["records"][0]["date"] == "2022-07-29"

    stats_out = tmp_path / "stats.json"
    result = runner.invoke(
        app, ["manifest-stats", "--manifest", str(manifest), "--output", str(stats_out)]
    )
    assert result.exit_code == 0, result.output
    assert "total=1 ok=1" in result.output
    assert stats_out.is_file()
