"""HTML review pages: image left, label right, low-confidence items first."""

from __future__ import annotations

import html
import os
from pathlib import Path

from brooks_lab.domain.labels import DayLabel, EventLabel


def _event_row(event: EventLabel) -> str:
    label = html.escape(event.label.value if event.label else "(unmapped)")
    raw = html.escape(event.raw_label)
    times = " / ".join(t.time for t in (event.start_time, event.end_time) if t is not None) or "—"
    low = " class='low'" if event.confidence < 0.6 else ""
    return (
        f"<tr{low}><td>{label}</td><td>{raw}</td>"
        f"<td>{html.escape(event.direction.value)}</td><td>{html.escape(times)}</td>"
        f"<td>{html.escape(event.outcome.value)}</td><td>{event.confidence:.2f}</td>"
        f"<td>{html.escape(event.source.value)}</td>"
        f"<td>{html.escape(event.evidence)}</td></tr>"
    )


def render_review_page(
    label: DayLabel,
    image_rel: str,
    out_path: Path,
    gold: bool,
    revisions: list[int],
) -> Path:
    """Render one review page. Events are sorted by confidence (lowest first)."""
    rows = "".join(_event_row(e) for e in sorted(label.events, key=lambda e: e.confidence))
    badge = " <span class='gold'>GOLD</span>" if gold else ""
    rev_text = ", ".join(f"rev{n}" for n in revisions) if revisions else "none yet"
    page = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>review {html.escape(label.image_id)}</title>"
        "<style>body{font-family:sans-serif;margin:16px}"
        ".wrap{display:grid;grid-template-columns:minmax(420px,3fr) minmax(320px,2fr);gap:16px}"
        "img{width:100%;height:auto;border:1px solid #ccc}"
        "table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:4px}"
        ".low{background:#fff3cd}.gold{background:#ffd700;padding:1px 8px;border-radius:10px}"
        ".meta{color:#555;font-size:13px}</style></head><body>"
        f"<h1>{html.escape(label.image_id)}{badge}</h1>"
        f"<p class='meta'>date {label.date} · day_type {html.escape(label.day_type.value)} "
        f"({label.day_type_confidence:.2f}) · history: {html.escape(rev_text)}</p>"
        "<div class='wrap'><div>"
        f"<img src='{html.escape(image_rel, quote=True)}' alt='{html.escape(label.image_id)}'>"
        f"<p>{html.escape(label.session_summary)}</p></div>"
        "<div><table><tr><th>label</th><th>raw</th><th>dir</th><th>times</th>"
        "<th>outcome</th><th>conf</th><th>src</th><th>evidence</th></tr>"
        f"{rows}</table>"
        f"<p class='meta'>extraction: {html.escape(label.extraction_meta.provider)}/"
        f"{html.escape(label.extraction_meta.model_id)}/"
        f"{html.escape(label.extraction_meta.prompt_version)}</p>"
        "</div></div></body></html>"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def render_review_index(
    labels: list[DayLabel],
    gold_ids: set[str],
    out_path: Path,
) -> Path:
    """Render the index page linking every review page (lowest day-confidence first)."""
    items = "".join(
        f"<li><a href='{html.escape(label.image_id)}.html'>{html.escape(label.image_id)}</a> "
        f"{html.escape(label.date.isoformat())} {html.escape(label.day_type.value)} "
        f"{label.day_type_confidence:.2f}"
        f"{' GOLD' if label.image_id in gold_ids else ''}</li>"
        for label in sorted(labels, key=lambda item: item.day_type_confidence)
    )
    page = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>review index</title></head><body>"
        f"<h1>Review queue ({len(labels)} labels, lowest confidence first)</h1>"
        f"<ol>{items}</ol></body></html>"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def image_rel_for_page(page_path: Path, data_dir: Path, filename: str) -> str:
    """Compute the relative image path from a review page (forward slashes)."""
    return os.path.relpath(str(data_dir / filename), str(page_path.parent)).replace(os.sep, "/")
