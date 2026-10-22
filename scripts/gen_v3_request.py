"""Generate a v3 file-exchange request for specific image ids (S2 closure step 1)."""

from __future__ import annotations

import sys
from pathlib import Path

from brooks_lab.application.ingestion import ImageIngestionService
from brooks_lab.infrastructure.taxonomy import load_taxonomy
from brooks_lab.infrastructure.vision import FileExchangeVisionClient

REPO = Path(__file__).resolve().parents[1]
QUEUE = REPO / "artifacts" / "extraction_queue"


PROVIDER = "file"
MODEL = "muse-spark-opencode"


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        raise SystemExit("usage: python scripts/gen_v3_request.py <image_id> [...]")
    taxonomy = load_taxonomy(REPO / "config" / "taxonomy.yaml")
    builder = ExtractionPromptBuilderV3(taxonomy)
    manifest = ImageIngestionService.read_manifest(REPO / "artifacts" / "manifest_batch1.json")
    client = FileExchangeVisionClient(queue_dir=QUEUE, model_id="muse-spark-opencode")
    wanted = set(ids)
    for record in manifest.records:
        if record.image_id not in wanted:
            continue
        date_iso = record.date.isoformat() if record.date else ""
        prompt = builder.build(record.image_id, date_iso, PROVIDER, MODEL)
        path = client.write_request(record.image_id, prompt)
        print(path)
        wanted.discard(record.image_id)
    if wanted:
        raise SystemExit(f"not found in manifest: {sorted(wanted)}")


def ExtractionPromptBuilderV3(taxonomy):  # local shim keeps the script short
    from brooks_lab.application.extraction import ExtractionPromptBuilder

    class _B(ExtractionPromptBuilder):
        def __init__(self, tax):
            super().__init__(REPO / "config" / "prompts" / "extract_v3.md", tax)

    return _B(taxonomy)


if __name__ == "__main__":
    main()
