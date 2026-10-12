"""Domain models for Phase 1 image inventory.

Pure metadata-level description of chart screenshots: identification, integrity,
dimensions, trading date, and ingestion status. No I/O here.
"""

from __future__ import annotations

import datetime
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MANIFEST_SCHEMA_VERSION = 1

_FILENAME_DATE_RE = re.compile(r"(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})")


class DateSource(StrEnum):
    """How the trading date of an image was determined."""

    FILENAME = "filename"
    OCR = "ocr"
    UNKNOWN = "unknown"


class RecordStatus(StrEnum):
    """Ingestion status of a single image."""

    OK = "ok"
    DUPLICATE = "duplicate"
    CORRUPT = "corrupt"
    TINY = "tiny"


class ImageRecord(BaseModel):
    """Validated metadata record for one chart screenshot."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=MANIFEST_SCHEMA_VERSION, ge=1)
    image_id: str = Field(min_length=1, description="Stable id: sha1(file bytes)[:12].")
    filename: str = Field(min_length=1, description="File name relative to the data dir.")
    sha256: str = Field(min_length=64, max_length=64)
    phash: str = Field(
        default="",
        description="Perceptual dHash (hex); empty when the image is unreadable.",
    )
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    format: str = Field(default="", description="Image format as reported by Pillow.")
    date: datetime.date | None = Field(default=None, description="Trading date (chart content).")
    date_source: DateSource = DateSource.UNKNOWN
    title_text: str | None = Field(
        default=None, description="OCR of the blue title bar; null without Tesseract."
    )
    status: RecordStatus = RecordStatus.OK
    duplicate_of: str | None = Field(
        default=None, description="image_id of the canonical copy when duplicated."
    )


class Manifest(BaseModel):
    """Validated ingestion manifest covering one scan of the data dir."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=MANIFEST_SCHEMA_VERSION, ge=1)
    generated_at: datetime.datetime | None = None
    records: list[ImageRecord] = Field(default_factory=list)


def parse_filename_date(filename: str) -> datetime.date | None:
    """Extract the trading date from names like ``S&P500_Emini_M5_2022_07_29.jpg``.

    Returns the first valid ``YYYY_MM_DD`` group, else ``None``. Never raises:
    out-of-range components (month 13, day 40, ...) yield ``None``.
    """
    match = _FILENAME_DATE_RE.search(filename)
    if match is None:
        return None
    try:
        return datetime.date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
    except ValueError:
        return None
