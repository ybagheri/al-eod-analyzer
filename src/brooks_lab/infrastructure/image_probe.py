"""Image probing port and Pillow implementation.

Reads integrity, dimensions, hashes, and format from image files. OCR stays out:
title/axis reading needs Tesseract (optional, later phase).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

#: File suffixes scanned by ingestion (lower-cased comparison).
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"})


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Outcome of probing one file."""

    ok: bool
    width: int = 0
    height: int = 0
    format: str = ""
    sha256: str = ""
    image_id: str = ""
    phash: str = ""
    error: str = ""


class ImageProber(Protocol):
    """Port: probe one image file without side effects."""

    def probe(self, path: Path) -> ProbeResult:
        """Return integrity, dimensions, and hashes for ``path``."""
        ...


def dhash_hex(image: Image.Image, hash_size: int = 8) -> str:
    """Compute a difference-hash (dHash) hex digest using Pillow only.

    Deterministic for identical pixels; near-identical charts usually collide,
    which is why exact-sha matches (not phash) decide duplicate status.
    """
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = list(gray.tobytes())
    value = 0
    for row in range(hash_size):
        base = row * (hash_size + 1)
        for col in range(hash_size):
            left = pixels[base + col]
            right = pixels[base + col + 1]
            value = (value << 1) | int(left > right)
    return f"{value:0{hash_size * hash_size // 4}x}"


class PillowProber:
    """Production prober built on Pillow. Never raises for corrupt files."""

    def probe(self, path: Path) -> ProbeResult:
        """Probe ``path``; corrupt/unreadable files yield ``ok=False``."""
        try:
            data = path.read_bytes()
        except OSError as exc:
            return ProbeResult(ok=False, error=f"unreadable file: {exc.strerror or exc}")
        digest = hashlib.sha256(data).hexdigest()
        image_id = hashlib.sha1(data).hexdigest()[:12]
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                image_format = image.format or ""
                phash = dhash_hex(image)
        # Any Pillow failure means a corrupt image: never let it escape probing.
        except Exception as exc:
            return ProbeResult(
                ok=False, sha256=digest, image_id=image_id, error=f"corrupt image: {exc}"
            )
        return ProbeResult(
            ok=True,
            width=width,
            height=height,
            format=image_format,
            sha256=digest,
            image_id=image_id,
            phash=phash,
        )
