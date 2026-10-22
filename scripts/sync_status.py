"""Render docs/STATUS.yaml into the status blocks of README.md, ROADMAP.md
and HANDOFF.md (plan-of-record v2.6 S0 item 2).

Usage:
    python scripts/sync_status.py [--check]

--check fails with exit code 1 when any rendered block differs from STATUS.yaml
(the quality gate runs it in check mode).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

import yaml

REPO = Path(__file__).resolve().parents[1]
STATUS_FILE = REPO / "docs" / "STATUS.yaml"

BEGIN = "<!-- STATUS:BEGIN (generated from docs/STATUS.yaml; do not edit) -->"
END = "<!-- STATUS:END -->"


def load_status(path: Path = STATUS_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return cast(dict[str, Any], yaml.safe_load(fh))


def render_readme_block(status: dict[str, Any]) -> str:
    lines = [BEGIN, "", "### Status (auto-generated from docs/STATUS.yaml)", ""]
    cur = status["current_step"]
    steps = status["steps"]
    lines.append(f"- **Current step:** {cur} - {steps[cur]['name']} ({steps[cur]['status']})")
    done = [k for k, v in steps.items() if v["status"] == "done"]
    prog = [k for k, v in steps.items() if v["status"] == "in_progress"]
    lines.append(f"- **Steps done:** {', '.join(done) if done else 'none'}")
    lines.append(f"- **Steps in progress:** {', '.join(prog) if prog else 'none'}")
    gate = status["last_gate"]
    lines.append(f"- **Last gate:** {gate['result']} ({gate['when']}): {gate['details']}")
    c = status["counts"]
    lines.append(
        f"- **Data:** {c['batch1_unique_ok']} unique batch-1 charts; "
        f"{c['extraction_queue_pairs']} filled queue pairs "
        f"({c['extraction_queue_request_only']} pending); "
        f"{c['labels_active']} labels; gold {c['gold_set']}"
    )
    cov = status["coverage"]
    lines.append(f"- **Market-data coverage:** {cov['market_data']}")
    lines.append(f"- Updated: {status['updated_at']}")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def render_roadmap_block(status: dict[str, Any]) -> str:
    lines = [BEGIN, ""]
    for key, step in status["steps"].items():
        mark = {"done": "✅", "in_progress": "🟨", "pending": "⬜", "blocked": "⛔"}[step["status"]]
        commit = step["commit"] or "—"
        lines.append(f"| {key} | {step['name']} | {mark} {step['status']} | `{commit}` |")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def render_handoff_block(status: dict[str, Any]) -> str:
    lines = [BEGIN, ""]
    sha12 = status["plan"]["sha256"][:12]
    ver = status["plan"]["method_version"]
    lines.append(f"Plan of record: docs/PLAN_V2.md (sha256 {sha12}…, method v{ver})")
    lines.append(
        f"Current step: {status['current_step']}; STATUS.yaml updated: {status['updated_at']}"
    )
    lines.append(f"Last gate: {status['last_gate']['result']} - {status['last_gate']['details']}")
    c = status["counts"]
    lines.append(
        "Counts: queue pairs "
        f"{c['extraction_queue_pairs']}/"
        f"{c['extraction_queue_pairs'] + c['extraction_queue_request_only']}, "
        f"labels {c['labels_active']}, quarantined {c['labels_quarantined']}, "
        f"gold {c['gold_set']}, gold open items {c['gold_open_items']}, "
        f"calibration sample {c['calibration_sample']}"
    )
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


TARGETS = {
    "README.md": render_readme_block,
    "ROADMAP.md": render_roadmap_block,
    "HANDOFF.md": render_handoff_block,
}


def sync_file(path: Path, status: dict[str, Any]) -> tuple[str, str]:
    """Return (old_block, new_block) for one doc; old_block '' if missing."""
    text = path.read_text(encoding="utf-8")
    new_block = TARGETS[path.name](status)
    start = text.find(BEGIN)
    if start == -1:
        return "", new_block
    end = text.find(END, start)
    if end == -1:
        msg = f"unterminated status block in {path}"
        raise ValueError(msg)
    end += len(END)
    return text[start:end], new_block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if blocks are stale")
    args = parser.parse_args(argv)
    status = load_status()
    drift: list[str] = []
    for rel, _render in TARGETS.items():
        path = REPO / rel
        old, new = sync_file(path, status)
        if old != new:
            drift.append(rel)
            if not args.check:
                text = path.read_text(encoding="utf-8")
                text = text.replace(old, new) if old else text.rstrip("\n") + "\n\n" + new + "\n"
                path.write_text(text, encoding="utf-8")
                print(f"updated {rel}")
    if args.check:
        if drift:
            print(json.dumps({"stale_blocks": drift}))
            return 1
        print("status blocks in sync")
        return 0
    if drift:
        print(f"synced {len(drift)} of {len(TARGETS)} docs; rerun to verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
