"""Integration tests: schema-export CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from brooks_lab.interfaces.cli import app


def test_schema_export_writes_valid_schema(tmp_path: Path) -> None:
    output = tmp_path / "label_schema.json"
    result = CliRunner().invoke(app, ["schema-export", "--output", str(output)])
    assert result.exit_code == 0, result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["day_label"]["title"] == "DayLabel"
    assert "day_type" in payload["day_label"]["properties"]
