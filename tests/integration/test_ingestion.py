"""Integration tests: ingestion service end to end on temp data dirs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from PIL import Image

from brooks_lab.application.ingestion import (
    ImageIngestionService,
    compute_stats,
)
from brooks_lab.domain.clock import Clock
from brooks_lab.domain.imaging import Manifest, RecordStatus
from brooks_lab.infrastructure.image_probe import ProbeResult
from brooks_lab.infrastructure.settings import IngestionSettings
from brooks_lab.interfaces.contact_sheet import render_contact_sheet


class FakeClock(Clock):
    """Deterministic clock for idempotency tests."""

    def __init__(self, fixed: datetime) -> None:
        """Capture the fixed instant to return."""
        self._fixed = fixed

    def now(self) -> datetime:
        """Return the fixed instant."""
        return self._fixed


class FakeProber:
    """Canned prober keyed by file name (contract-compatible with ImageProber)."""

    def __init__(self, results: dict[str, ProbeResult]) -> None:
        """Capture canned results per file name."""
        self._results = results

    def probe(self, path: Path) -> ProbeResult:
        """Return the canned result for ``path.name``."""
        return self._results[path.name]


def _ok_result(image_id: str, sha: str, width: int = 1280) -> ProbeResult:
    return ProbeResult(
        ok=True,
        width=width,
        height=720,
        format="JPEG",
        sha256=sha,
        image_id=image_id,
        phash="abcd" * 4,
    )


def test_scan_classifies_ok_duplicate_tiny_corrupt(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    names = ["a.jpg", "b.jpg", "dup_of_a.jpg", "tiny.jpg", "broken.jpg", "notes.txt"]
    for name in names:
        (data / name).write_bytes(b"x")
    prober = FakeProber(
        {
            "a.jpg": _ok_result("id-a", "a" * 64),
            "b.jpg": _ok_result("id-b", "b" * 64),
            "dup_of_a.jpg": _ok_result("id-a", "a" * 64),
            "tiny.jpg": _ok_result("id-t", "t" * 64, width=100),
            "broken.jpg": ProbeResult(ok=False, error="corrupt"),
            "notes.txt": _ok_result("id-n", "n" * 64),
        }
    )
    service = ImageIngestionService(
        settings=IngestionSettings(),
        prober=prober,  # type: ignore[arg-type]
        clock=FakeClock(datetime(2026, 10, 12, tzinfo=UTC)),
    )
    manifest = service.scan(data)
    by_name = {r.filename: r for r in manifest.records}
    # notes.txt is not an image suffix -> excluded; 5 image files covered.
    assert sorted(by_name) == ["a.jpg", "b.jpg", "broken.jpg", "dup_of_a.jpg", "tiny.jpg"]
    assert by_name["a.jpg"].status is RecordStatus.OK
    assert by_name["b.jpg"].status is RecordStatus.OK
    assert by_name["dup_of_a.jpg"].status is RecordStatus.DUPLICATE
    assert by_name["dup_of_a.jpg"].duplicate_of == "id-a"
    assert by_name["tiny.jpg"].status is RecordStatus.TINY
    assert by_name["broken.jpg"].status is RecordStatus.CORRUPT


def test_scan_and_write_is_idempotent(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "chart_2022_07_29.jpg").write_bytes(b"img")
    service = ImageIngestionService(
        prober=FakeProber({"chart_2022_07_29.jpg": _ok_result("id-x", "x" * 64)}),  # type: ignore[arg-type]
        clock=FakeClock(datetime(2026, 1, 1, tzinfo=UTC)),
    )
    target = tmp_path / "artifacts" / "manifest.json"
    first = service.scan_and_write(data, target)
    before = target.read_bytes()
    second = service.scan_and_write(data, target)
    assert target.read_bytes() == before
    assert second == first
    assert ImageIngestionService.read_manifest(target) == first


def test_end_to_end_real_images_stats_and_sheet(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    big = Image.new("RGB", (1280, 720), color="white")
    big.save(data / "S&P500_Emini_M5_2022_07_29.jpg", format="JPEG")
    other = Image.new("RGB", (1280, 720), color="gray")
    other.save(data / "S&P500_Emini_M5_2022_08_02.jpg", format="JPEG")
    (data / "S&P500_Emini_M5_2022_08_02_copy.jpg").write_bytes(
        (data / "S&P500_Emini_M5_2022_08_02.jpg").read_bytes()
    )
    tiny = Image.new("RGB", (10, 10), color="black")
    tiny.save(data / "tiny_2022_08_03.jpg", format="JPEG")
    (data / "broken_2022_08_04.jpg").write_bytes(b"not an image")
    service = ImageIngestionService(clock=FakeClock(datetime(2026, 1, 1, tzinfo=UTC)))
    manifest = service.scan_and_write(data, tmp_path / "manifest.json")
    assert isinstance(manifest, Manifest)
    stats = compute_stats(manifest)
    assert (stats.total, stats.ok) == (5, 2)
    assert (stats.duplicates, stats.corrupt, stats.tiny) == (1, 1, 1)
    assert stats.date_min == date(2022, 7, 29)
    assert stats.date_max == date(2022, 8, 4)
    assert date(2022, 7, 30) in stats.missing_dates
    assert date(2022, 8, 1) in stats.missing_dates
    assert stats.duplicate_files == ["S&P500_Emini_M5_2022_08_02_copy.jpg"]
    service.write_stats(stats, tmp_path / "stats.json")
    sheet = render_contact_sheet(
        manifest.records, stats, tmp_path / "review" / "contact_sheet.html", data
    )
    assert sheet.is_file()
    page = sheet.read_text(encoding="utf-8")
    for record in manifest.records:
        assert record.image_id in page
