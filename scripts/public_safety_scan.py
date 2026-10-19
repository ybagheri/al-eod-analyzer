"""Public-safety scan (plan v2.6 S0 item 3; AGENTS.md rule 11).

The repo is PUBLIC by the user's decision. This script makes "safe to be
public" an automated, enforced property: it scans (a) the tracked working
tree and (b) optionally the entire git history and flags:

- image/video/archive files (jpg, png, mp4, zip, ...)
- anything under data/
- market data: *.csv larger than 200 KB, MT5 history files
- config/local.yaml, .env
- secrets (API keys, tokens, private keys, -----BEGIN blocks)
- absolute personal paths such as C:\\Users\\<name>\\
- blobs larger than 1 MB
- extraction-queue files embedding image bytes (base64) or long verbatim
  transcriptions of on-chart text

Usage:
    python scripts/public_safety_scan.py            # tracked working tree
    python scripts/public_safety_scan.py --history  # full git history
    python scripts/public_safety_scan.py --json     # machine-readable report

Exit code 0 = clean; 1 = violations found.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

IMAGE_VIDEO_ARCHIVE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".wmv",
    ".zip",
    ".rar",
    ".7z",
    ".gz",
    ".tgz",
    ".tar",
    ".cab",
}
MT5_HISTORY_EXTS = {".hcc", ".hc5", ".hcc5", ".dat"}

SECRET_PATTERNS = {
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_api_key": re.compile(
        r"(api[_-]?key|apikey|secret|token|passwd|password)\s*[:=][ \t]*['\"]?[A-Za-z0-9_\-]{16,}",
        re.IGNORECASE,
    ),
    "ssh_url_with_password": re.compile(r"https?://[^/\s]*:[^@\s/]+@"),
}

PERSONAL_PATH_PATTERN = re.compile(
    r"[A-Za-z]:\\Users\\(?!<)[A-Za-z0-9_.\- ]+\\|/home/[A-Za-z0-9_.\-]+/"
)

# Raw magic bytes of common image formats (checked on base64-decoded data).
IMAGE_BIN_SIGNATURES = (
    b"\xff\xd8\xff",  # jpeg
    b"\x89PNG\r\n\x1a\n",  # png
    b"GIF89a",
    b"GIF87a",  # gif
)

MAX_TEXT_BYTES = 2_000_000  # do not scan binaries as text beyond 2 MB
BLOB_LIMIT = 1_000_000
CSV_SIZE_LIMIT = 200_000
LONG_TRANSCRIPTION_CHARS = 2000

# Documented, content-inspected exceptions (see docs/PUBLIC_SAFETY.md):
# - artifacts/manifest_batch1.json: metadata-only manifest (sha256/phash per
#   ingested image, filenames, dimensions). No images, no market data.
# - data/README.md: documentation only; the only tracked file under data/.
ALLOWED_BLOB_SIZE = {
    "artifacts/manifest_batch1.json",
}
ALLOWED_DATA_DIR = {
    "data/README.md",
}
# The scanner's own unit tests legitimately contain fake keys/patterns.
ALLOWED_CONTENT = {
    "tests/test_public_safety_scan.py",
}
# Findings the user explicitly ACCEPTED after review (docs/PUBLIC_SAFETY.md,
# decision 2026-10-19: local MT5 paths in the pre-redaction MASTER_PROMPT.md
# blob; no history rewrite). History scan skips exactly these tuples.
ACCEPTED_HISTORY = {
    ("07f0f9c4a0f939ecb67f1c8776be0931aec365ba", "docs/MASTER_PROMPT.md", "personal_path"),
}


def _git(args: list[str]) -> str:
    out = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO,
        check=True,
    )
    return out.stdout


def tracked_files() -> list[str]:
    out = _git(["ls-files"])
    return [line for line in out.splitlines() if line.strip()]


def parse_ls_tree(out: str) -> list[tuple[str, str]]:
    """Parse `git ls-tree -r -z --full-tree <ref>` zero-padded output."""
    entries: list[tuple[str, str]] = []
    for chunk in out.split("\0"):
        if not chunk:
            continue
        meta, _, path = chunk.partition("\t")
        parts = meta.split()
        if len(parts) >= 4:
            entries.append((parts[2], path))
    return entries


def _read_text(blobs: bytes) -> str:
    if len(blobs) > MAX_TEXT_BYTES:
        return ""
    if b"\x00" in blobs[:8000]:
        return ""
    try:
        return blobs.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _iter_json_strings(obj: Any, skip_keys: set[str]) -> Generator[str, None, None]:
    """Yield every string value in a parsed JSON document."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip_keys:
                continue
            yield from _iter_json_strings(v, skip_keys)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_json_strings(v, skip_keys)
    elif isinstance(obj, str):
        yield obj


def scan_blob(blob: bytes, path: str) -> list[str]:
    """Content-level findings for one blob."""
    findings: list[str] = []
    suffix = Path(path).suffix.lower()
    text = _read_text(blob)

    # 1. Base64-embedded image bytes (queue files must not carry images).
    if text:
        for m in re.finditer(r"[A-Za-z0-9+/=]{2000,}", text):
            chunk = m.group(0)
            try:
                raw = base64.b64decode(chunk[:2048], validate=True)
            except Exception:
                continue
            if raw.startswith(IMAGE_BIN_SIGNATURES):
                findings.append("embedded_base64_image")
                break

    # 2. Long verbatim transcription of on-chart text (queue/label JSONs):
    #    titles/annotations are fine; a wall of chart text is not. For JSON
    #    documents the check is on string VALUES (formatting-independent);
    #    the `"prompt"` field of *.request.json is the committed extraction
    #    prompt template and is exempted.
    if suffix in {".json", ".md", ".txt"} and text:
        if suffix == ".json":
            try:
                doc = json.loads(text)
            except ValueError:
                doc = None
            if doc is None:
                longest = max((len(line) for line in text.splitlines() if line), default=0)
                if longest > LONG_TRANSCRIPTION_CHARS:
                    findings.append("long_verbatim_line")
            else:
                skip = {"prompt"} if Path(path).name.endswith(".request.json") else set()
                if any(len(s) > LONG_TRANSCRIPTION_CHARS for s in _iter_json_strings(doc, skip)):
                    findings.append("long_json_string")
        else:
            longest = max((len(line) for line in text.splitlines() if line), default=0)
            if longest > LONG_TRANSCRIPTION_CHARS:
                findings.append("long_verbatim_line")

    # 3. Secrets.
    if text:
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"secret_pattern:{name}")

    # 4. Absolute personal paths.
    if text and PERSONAL_PATH_PATTERN.search(text):
        findings.append("personal_path")

    return findings


def scan_path(path: str, size: int | None) -> list[str]:
    findings: list[str] = []
    suffix = Path(path).suffix.lower()
    norm = path.replace("\\", "/")
    if suffix in IMAGE_VIDEO_ARCHIVE_EXTS:
        findings.append("image_video_archive_file")
    if norm == "data/" or norm.startswith("data/"):
        findings.append("under_data_dir")
    if suffix in MT5_HISTORY_EXTS:
        findings.append("mt5_history_file")
    if Path(norm).name in {"config/local.yaml", ".env", "local.yaml"}:
        findings.append("local_config_or_env")
    if size is not None and size > BLOB_LIMIT:
        findings.append(f"blob_over_1mb({size})")
    if suffix == ".csv" and size is not None and size > CSV_SIZE_LIMIT:
        findings.append(f"csv_over_200kb({size})")
    return findings


def _allowlist(path: str, findings: list[str]) -> list[str]:
    """Drop allowlisted findings (documented exceptions, see ALLOWED_* above)."""
    kept: list[str] = []
    for f in findings:
        if f.startswith("under_data_dir") and path in ALLOWED_DATA_DIR:
            continue
        if f.startswith("blob_over_1mb") and path in ALLOWED_BLOB_SIZE:
            continue
        if path in ALLOWED_CONTENT and (f.startswith("secret_pattern") or f.startswith("long_")):
            continue
        kept.append(f)
    return kept


def scan_working_tree() -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for path in tracked_files():
        findings = scan_path(path, None)
        blob_path = REPO / path
        if blob_path.exists():
            blob = blob_path.read_bytes()
            findings += scan_path(path, len(blob))
            findings += scan_blob(blob, path)
        findings = _allowlist(path, findings)
        if findings:
            violations.append({"path": path, "findings": sorted(set(findings))})
    return violations


def scan_history() -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    out = _git(["rev-list", "--objects", "--all"])
    seen: set[str] = set()
    entries: dict[str, str] = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, _, name = line.partition(" ")
        if sha not in seen:
            seen.add(sha)
            if name:
                entries[sha] = name
    for sha, name in entries.items():
        findings = scan_path(name, None)
        size_raw = _git(["cat-file", "-s", sha]).strip()
        size = int(size_raw) if size_raw.isdigit() else None
        findings += scan_path(name, size)
        if size is None or size > MAX_TEXT_BYTES:
            pass
        else:
            out_type = _git(["cat-file", "-t", sha]).strip()
            if out_type == "blob":
                raw = _git(["cat-file", "blob", sha]).encode("utf-8", errors="replace")
                findings += scan_blob(raw, name)
        findings = _allowlist(name, findings)
        accepted = {f for f in findings if (sha, name, f) in ACCEPTED_HISTORY}
        if accepted:
            findings = [f for f in findings if f not in accepted]
            print(
                f"accepted (user-approved, see docs/PUBLIC_SAFETY.md): "
                f"{sha[:12]} {name}: {','.join(sorted(accepted))}"
            )
        if findings:
            violations.append({"blob": sha, "path": name, "findings": sorted(set(findings))})
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="scan full git history")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    violations = scan_history() if args.history else scan_working_tree()
    report = {
        "mode": "history" if args.history else "working_tree",
        "violations": violations,
        "count": len(violations),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    elif violations:
        for v in violations:
            print(f"FLAG {v['path']}: {', '.join(v['findings'])}")
    else:
        print("public-safety scan clean")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
