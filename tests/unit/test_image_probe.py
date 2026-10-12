"""Unit tests: Pillow prober and dHash behaviour on generated images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from brooks_lab.infrastructure.image_probe import PillowProber, dhash_hex


def _save(path: Path, size: tuple[int, int], color: str) -> Path:
    image = Image.new("RGB", size, color=color)
    image.save(path, format="JPEG")
    return path


def _pattern(path: Path, horizontal: bool) -> Path:
    """Two asymmetric splits: vertical (left/right) vs horizontal (top/bottom)."""
    image = Image.new("L", (64, 64), color=0)
    pixels = image.load()
    assert pixels is not None
    for y in range(64):
        for x in range(64):
            if (x < 32 and not horizontal) or (y < 32 and horizontal):
                pixels[x, y] = 255
    image.save(path, format="PNG")
    return path


def test_probe_valid_image(tmp_path: Path) -> None:
    target = _save(tmp_path / "day_2022_07_29.jpg", (1280, 720), "white")
    result = PillowProber().probe(target)
    assert result.ok
    assert (result.width, result.height) == (1280, 720)
    assert result.format == "JPEG"
    assert len(result.sha256) == 64
    assert len(result.image_id) == 12
    assert len(result.phash) == 16
    assert result.error == ""


def test_probe_identical_bytes_identical_hashes(tmp_path: Path) -> None:
    first = _save(tmp_path / "a.jpg", (640, 480), "red")
    second = tmp_path / "b.jpg"
    second.write_bytes(first.read_bytes())
    prober = PillowProber()
    assert prober.probe(first) == prober.probe(second)


def test_probe_corrupt_image(tmp_path: Path) -> None:
    target = tmp_path / "broken.jpg"
    target.write_bytes(b"\x00\x01\x02not-an-image\xff\xfe")
    result = PillowProber().probe(target)
    assert not result.ok
    assert result.error != ""
    assert len(result.sha256) == 64


def test_probe_missing_file(tmp_path: Path) -> None:
    result = PillowProber().probe(tmp_path / "absent.jpg")
    assert not result.ok
    assert result.error != ""


def test_dhash_differs_for_different_patterns(tmp_path: Path) -> None:
    with Image.open(_pattern(tmp_path / "p1.png", horizontal=False)) as first:
        first_hash = dhash_hex(first)
    with Image.open(_pattern(tmp_path / "p2.png", horizontal=True)) as second:
        second_hash = dhash_hex(second)
    assert len(first_hash) == 16
    assert first_hash != second_hash
