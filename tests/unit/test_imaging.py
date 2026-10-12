"""Unit tests: filename-date parsing and imaging domain models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from brooks_lab.domain.imaging import (
    DateSource,
    ImageRecord,
    Manifest,
    RecordStatus,
    parse_filename_date,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("S&P500_Emini_M5_2022_07_29.jpg", date(2022, 7, 29)),
        ("S_P500_Emini_M5_2022_07_29.jpg", date(2022, 7, 29)),
        ("S&P500_Emini_M5_2022_08_02.jpg", date(2022, 8, 2)),
        ("chart_1999_12_31.png", date(1999, 12, 31)),
        ("2022_07_29_first_2023_01_01.jpg", date(2022, 7, 29)),
    ],
)
def test_parse_filename_date_valid(filename: str, expected: date) -> None:
    assert parse_filename_date(filename) == expected


@pytest.mark.parametrize(
    "filename",
    [
        "chart.jpg",
        "no_date_here.png",
        "X_2022_13_01.jpg",  # month out of range
        "X_2022_00_10.jpg",  # month zero
        "X_2022_02_30.jpg",  # day out of range
        "X_2022_7_9.jpg",  # pattern needs zero-padded components
        "",
    ],
)
def test_parse_filename_date_invalid(filename: str) -> None:
    assert parse_filename_date(filename) is None


def _record() -> ImageRecord:
    return ImageRecord(
        image_id="abc123def456",
        filename="S&P500_Emini_M5_2022_07_29.jpg",
        sha256="0" * 64,
        phash="00ff00ff00ff00ff",
        width=1280,
        height=720,
        format="JPEG",
        date=date(2022, 7, 29),
        date_source=DateSource.FILENAME,
        status=RecordStatus.OK,
    )


def test_image_record_defaults() -> None:
    minimal = ImageRecord(image_id="abc123def456", filename="x.jpg", sha256="0" * 64)
    assert minimal.schema_version == 1
    assert minimal.date is None
    assert minimal.date_source is DateSource.UNKNOWN
    assert minimal.title_text is None
    assert minimal.status is RecordStatus.OK
    assert minimal.duplicate_of is None


def test_image_record_rejects_bad_sha() -> None:
    with pytest.raises(ValidationError):
        ImageRecord(image_id="abc123def456", filename="x.jpg", sha256="short")


def test_manifest_json_round_trip() -> None:
    manifest = Manifest(records=[_record()])
    restored = Manifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest
