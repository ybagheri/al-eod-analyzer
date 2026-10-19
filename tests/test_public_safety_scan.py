"""Tests for scripts/public_safety_scan.py (public-safety rules)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import public_safety_scan as pss  # noqa: E402


def test_env_example_placeholder_not_flagged() -> None:
    blob = (
        b"# Copy to `.env` and fill in.\n"
        b"ANTHROPIC_API_KEY=\nOPENAI_API_KEY=\nBROOKS_VISION_PROVIDER=file\n"
    )
    assert pss.scan_blob(blob, ".env.example") == []


def test_real_api_key_value_flagged() -> None:
    blob = b"ANTHROPIC_API_KEY=sk-ant-abcdef0123456789abcdef\n"
    assert "secret_pattern:generic_api_key" in pss.scan_blob(blob, ".env")


def test_private_key_block_flagged() -> None:
    blob = b"-----BEGIN RSA PRIVATE KEY-----\nabc\n"
    assert "secret_pattern:private_key_block" in pss.scan_blob(blob, "k.pem")


def test_personal_path_flagged() -> None:
    blob = b"terminal: C:\\Users\\johndoe\\AppData\\q\n"
    assert "personal_path" in pss.scan_blob(blob, "notes.md")


def test_request_prompt_field_exempt(monkeypatch: pytest.MonkeyPatch) -> None:
    prompt = '"' + "x" * 3000 + '"'
    blob = b'{"prompt": ' + prompt.encode() + b', "model": "gpt-v"}\n'
    assert pss.scan_blob(blob, "artifacts/extraction_queue/abc123.request.json") == []


def test_long_json_string_flagged_even_minified() -> None:
    wall = '"' + "chart text " * 200 + '"'  # ~2200 chars in one JSON string
    blob = b'{"response": {"image_note": ' + wall.encode() + b"}}\n"
    assert "long_json_string" in pss.scan_blob(blob, "abc.response.json")


def test_pretty_json_long_string_also_flagged() -> None:
    blob = ('{\n  "image_note": "' + "x" * 2100 + '"\n}\n').encode()
    assert "long_json_string" in pss.scan_blob(blob, "abc.response.json")


def test_minified_json_with_short_values_clean() -> None:
    blob = b'{"date": "2022-08-04", "day_type": "trading_range", "confidence": 0.9}\n'
    assert pss.scan_blob(blob, "abc.response.json") == []


def test_base64_image_in_queue_file_flagged() -> None:
    import base64

    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 4096).decode()
    blob = ('{"image_bytes": "' + png + '"}\n').encode()
    assert "embedded_base64_image" in pss.scan_blob(blob, "abc.request.json")


def test_path_rules() -> None:
    assert "image_video_archive_file" in pss.scan_path("data/x.png", 100)
    assert "under_data_dir" in pss.scan_path("data/x.csv", 100)
    assert "local_config_or_env" in pss.scan_path("config/local.yaml", 10)
    assert "local_config_or_env" in pss.scan_path(".env", 10)
    assert "mt5_history_file" in pss.scan_path("b2/US500.hcc", 10)
    assert f"blob_over_1mb({pss.BLOB_LIMIT + 1})" in pss.scan_path("big.bin", pss.BLOB_LIMIT + 1)
    assert f"csv_over_200kb({pss.CSV_SIZE_LIMIT + 1})" in pss.scan_path(
        "x.csv", pss.CSV_SIZE_LIMIT + 1
    )


def test_allowlist_strips_documented_exceptions() -> None:
    findings = ["under_data_dir", "blob_over_1mb(1050151)"]
    assert pss._allowlist("data/README.md", findings) == ["blob_over_1mb(1050151)"]
    assert pss._allowlist("artifacts/manifest_batch1.json", findings) == ["under_data_dir"]
    # allowlist applies only to the exact allowlisted paths
    assert pss._allowlist("data/other.md", findings) == ["under_data_dir", "blob_over_1mb(1050151)"]


def test_accepted_history_finding_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    sha = next(iter(pss.ACCEPTED_HISTORY))[0]
    name = next(iter(pss.ACCEPTED_HISTORY))[1]
    assert pss._allowlist(name, ["personal_path"]) == ["personal_path"]  # tree mode still flags
    # simulate the history loop's acceptance step
    findings = ["personal_path"]
    accepted = {f for f in findings if (sha, name, f) in pss.ACCEPTED_HISTORY}
    assert accepted == {"personal_path"}
    assert [f for f in findings if f not in accepted] == []
