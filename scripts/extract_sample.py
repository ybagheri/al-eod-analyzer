"""Stratified calibration-extraction runner for batch-1 images (ADR-010 waves).

Usage:
  python scripts/extract_sample.py --build-sample 12 --sample-file artifacts/calibration_sample.txt
  python scripts/extract_sample.py --sample-file artifacts/calibration_sample.txt

Sample build is deterministic: one image per largest title day-type stratum
(spread across vintages by even index), plus unmapped/undated/weekend-dated
special strata. The run filters the batch-1 manifest to sample ids, writes
file-exchange request files, and expects responses in the queue dir; re-run
after responses are written to validate labels.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BATCH_MANIFEST = REPO / "artifacts" / "manifest_batch1.json"
TITLE_MAP = REPO / "artifacts" / "title_map_batch1.json"
CAL_REPORT = REPO / "artifacts" / "calibration_report.json"

sys.path.insert(0, str(REPO))

from brooks_lab.application.extraction import (  # noqa: E402
    ExtractionPromptBuilder,
    ExtractionService,
)
from brooks_lab.domain.imaging import Manifest  # noqa: E402
from brooks_lab.infrastructure.taxonomy import load_taxonomy  # noqa: E402
from brooks_lab.infrastructure.vision import FileExchangeVisionClient  # noqa: E402


def _pick_even(items: list, count: int) -> list:
    """Pick ``count`` evenly spaced items from a sorted list (deterministic)."""
    if count >= len(items):
        return list(items)
    if count == 1:
        return [items[len(items) // 2]]
    step = (len(items) - 1) / (count - 1)
    return [items[round(i * step)] for i in range(count)]


def _meta_entry(key: str, record: dict, title_by_id: dict) -> dict[str, object]:
    entry = title_by_id[record["image_id"]]
    return {
        "image_id": record["image_id"],
        "stratum": key,
        "filename": record["filename"],
        "date": entry["date"],
        "title_day_type": entry["day_type"],
    }


def build_sample(size: int, out_path: Path) -> list[str]:
    """Append ``size`` more image ids, round-robin across strata (deterministic).

    IDs already listed in ``out_path`` are never re-picked; each round adds one
    further representative per stratum (spread across vintages via _pick_even).
    """
    payload = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    title_payload = json.loads(TITLE_MAP.read_text(encoding="utf-8"))
    title_by_id = {r["image_id"]: r for r in title_payload["records"]}

    ok_records = [r for r in payload["records"] if r.get("status") == "ok"]
    strata: dict[str, list] = {}
    for record in ok_records:
        entry = title_by_id[record["image_id"]]
        record_date = record.get("date")
        if record_date is None:
            key = "_undated"
        else:
            if isinstance(record_date, str) and "_" in record_date:
                record_date = record_date.replace("_", "-")
            if isinstance(record_date, str):
                record_date = datetime.date.fromisoformat(record_date)
            if record_date.weekday() >= 5:
                key = "_weekend_dated"
            elif entry["day_type"] is None:
                key = "_unmapped"
            else:
                key = f"day:{entry['day_type']}"
        strata.setdefault(key, []).append(record)

    # Deterministic order: day strata by size desc then name, specials after.
    day_keys = sorted(
        (k for k in strata if k.startswith("day:")),
        key=lambda k: (-len(strata[k]), k),
    )
    special_keys = sorted(k for k in strata if k.startswith("_"))
    previous = (
        {
            line.strip()
            for line in out_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        if out_path.is_file()
        else set()
    )
    picked_ids: set[str] = set(previous)
    all_meta: list[dict[str, object]] = []
    if previous and out_path.with_suffix(".json").is_file():
        all_meta = json.loads(out_path.with_suffix(".json").read_text(encoding="utf-8"))[
            "selection"
        ]
    fresh: list[str] = []
    while len(fresh) < size:
        progressed = False
        for key in day_keys + special_keys:
            if len(fresh) >= size:
                break
            pool = sorted(strata[key], key=lambda r: r["filename"])
            free = [r for r in pool if r["image_id"] not in picked_ids]
            if not free:
                continue
            taken = len(pool) - len(free)
            candidates = [r for r in _pick_even(pool, taken + 1) if r in free]
            pick = candidates[0] if candidates else free[0]
            picked_ids.add(pick["image_id"])
            fresh.append(pick["image_id"])
            all_meta.append(_meta_entry(key, pick, title_by_id))
            progressed = True
        if not progressed:
            break
    out_path.write_text("\n".join(sorted(picked_ids)) + "\n", encoding="utf-8")
    sample_json = out_path.with_suffix(".json")
    sample_json.write_text(
        json.dumps(
            {
                "purpose": "calibration wave (ADR-010, appends)",
                "size": len(picked_ids),
                "appendix": len(fresh),
                "selection": all_meta,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    counts = Counter(m["stratum"] for m in all_meta if m["image_id"] in fresh)
    print(f"sample appended: {len(fresh)} new ids (total {len(picked_ids)}) -> {out_path}")
    print("new per stratum:", dict(counts))
    return fresh


def run_sample(sample_file: Path, report_out: Path | None = CAL_REPORT) -> None:
    sample_ids = {
        line.strip()
        for line in sample_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    payload = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    kept = [
        r for r in payload["records"] if r.get("image_id") in sample_ids and r.get("status") == "ok"
    ]
    missing = sample_ids - {r["image_id"] for r in kept}
    if missing:
        raise SystemExit(f"sample ids missing from batch manifest: {sorted(missing)}")
    sample_manifest = Manifest.model_validate({**payload, "records": kept})

    taxonomy = load_taxonomy(REPO / "config" / "taxonomy.yaml")
    builder = ExtractionPromptBuilder(REPO / "config" / "prompts" / "extract_v2.md", taxonomy)
    client = FileExchangeVisionClient(
        queue_dir=REPO / "artifacts" / "extraction_queue", model_id="muse-spark-opencode"
    )
    service = ExtractionService(
        manifest=sample_manifest,
        data_dir=REPO / "data" / "raw_batch1",
        labels_dir=REPO / "artifacts" / "labels",
        failed_dir=REPO / "artifacts" / "labels_failed",
        client=client,
        prompt_builder=builder,
        provider="file",
        history_dir=REPO / "artifacts" / "labels_history",
        gold_path=REPO / "artifacts" / "gold_set.json",
    )
    report = service.run(resume=True)
    print(
        f"extract sample: labeled={report.labeled} skipped={report.skipped} "
        f"pending={report.pending} failed={report.quarantined}"
    )

    title_payload = json.loads(TITLE_MAP.read_text(encoding="utf-8"))
    title_by_id = {r["image_id"]: r for r in title_payload["records"]}
    comparison = []
    for image_id in sorted(sample_ids):
        label_path = REPO / "artifacts" / "labels" / f"{image_id}.json"
        extracted_day = extracted_events = None
        if label_path.is_file():
            label = json.loads(label_path.read_text(encoding="utf-8"))
            extracted_day = label.get("day_type")
            extracted_events = len(label.get("events", []))
        title_entry = title_by_id.get(image_id)
        title_day = title_entry["day_type"] if title_entry else None
        agree = None if extracted_day is None or title_day is None else extracted_day == title_day
        comparison.append(
            {
                "image_id": image_id,
                "title_day_type": title_day,
                "extracted_day_type": extracted_day,
                "day_match": agree,
                "extracted_event_count": extracted_events,
            }
        )
    matched = [c for c in comparison if c["day_match"] is not None]
    agreement = (
        round(sum(1 for c in matched if c["day_match"]) / len(matched), 3) if matched else None
    )
    result = {"comparison": comparison, "day_type_agreement": agreement, "n": len(matched)}
    out = report_out or REPO / "artifacts" / "calibration_report.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if agreement is not None:
        print(f"day_type agreement vs title: {agreement} ({len(matched)} comparable)")
    for c in comparison:
        print(
            f"  {c['image_id']}  title={c['title_day_type']}  extracted={c['extracted_day_type']}  "
            f"events={c['extracted_event_count']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-file", type=Path, required=True)
    parser.add_argument("--build-sample", type=int, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    if args.build_sample:
        fresh = build_sample(args.build_sample, args.sample_file)
        if not fresh:
            print("no new sample ids (pool exhausted)")
            return
    run_sample(args.sample_file, args.report)


if __name__ == "__main__":
    main()
