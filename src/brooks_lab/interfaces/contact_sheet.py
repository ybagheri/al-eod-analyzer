"""Contact-sheet renderer: one HTML page to eyeball all ingested images."""

from __future__ import annotations

import html
import os
from pathlib import Path

from brooks_lab.application.ingestion import IngestionStats
from brooks_lab.domain.imaging import ImageRecord


def _card(record: ImageRecord, image_rel: str) -> str:
    safe_name = html.escape(record.filename)
    date_text = html.escape(record.date.isoformat() if record.date else "unknown date")
    meta = (
        f"{record.width}x{record.height} {html.escape(record.format or '?')} - "
        f"{date_text} · {html.escape(record.date_source.value)} · "
        f"id {html.escape(record.image_id)}"
    )
    status_class = {
        "ok": "ok",
        "duplicate": "dup",
        "corrupt": "bad",
        "tiny": "bad",
    }[record.status.value]
    dup_note = (
        f" — duplicate of {html.escape(record.duplicate_of or '')}" if record.duplicate_of else ""
    )
    return (
        f'<figure class="card {status_class}">'
        f'<a href="{html.escape(image_rel, quote=True)}">'
        f'<img loading="lazy" src="{html.escape(image_rel, quote=True)}" alt="{safe_name}">'
        f"</a>"
        f"<figcaption><strong>{safe_name}</strong>"
        f'<span class="badge">{html.escape(record.status.value)}{dup_note}</span>'
        f"<br>{meta}</figcaption></figure>"
    )


def render_contact_sheet(
    records: list[ImageRecord],
    stats: IngestionStats,
    html_path: Path,
    data_dir: Path,
) -> Path:
    """Render the contact sheet to ``html_path``. Returns the path written."""
    cards: list[str] = []
    for record in records:
        image_rel = os.path.relpath(str(data_dir / record.filename), str(html_path.parent))
        image_rel = image_rel.replace(os.sep, "/")
        cards.append(_card(record, image_rel))
    summary = (
        f"total {stats.total} · ok {stats.ok} · duplicates {stats.duplicates} · "
        f"corrupt {stats.corrupt} · tiny {stats.tiny} · "
        f"range {stats.date_min}…{stats.date_max} · "
        f"missing dates {len(stats.missing_dates)}"
    )
    page = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>al-eod-analyzer contact sheet</title>"
        "<style>body{font-family:sans-serif;margin:16px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}"
        ".card{border:1px solid #ccc;border-radius:8px;padding:8px;margin:0}"
        ".card img{width:100%;height:auto;display:block}"
        ".badge{display:inline-block;margin-left:8px;padding:1px 8px;border-radius:10px;"
        "background:#eee;font-size:12px}"
        ".ok{border-left:6px solid #2a2}.dup{border-left:6px solid #da0}"
        ".bad{border-left:6px solid #d33}</style></head><body>"
        f"<h1>Contact sheet</h1><p>{html.escape(summary)}</p>"
        f"<div class='grid'>{''.join(cards)}</div></body></html>"
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(page, encoding="utf-8")
    return html_path
