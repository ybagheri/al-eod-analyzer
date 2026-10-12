"""Review queue: collect unmapped raw labels with merge suggestions (pure logic)."""

from __future__ import annotations

import difflib
from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from brooks_lab.domain.labels import LABEL_SCHEMA_VERSION, DayLabel, normalise_wording


class ReviewItem(BaseModel):
    """One unmapped wording with occurrence counts and a merge suggestion."""

    model_config = ConfigDict(frozen=True)

    raw_label: str
    count: int = Field(ge=1)
    image_ids: list[str] = Field(default_factory=list)
    suggestion: str | None = Field(
        default=None, description="Closest canonical id, if similar enough."
    )


class ReviewQueue(BaseModel):
    """All unmapped wordings across a batch of day labels."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=LABEL_SCHEMA_VERSION, ge=1)
    items: list[ReviewItem] = Field(default_factory=list)


def suggest_canonical(raw: str, canonical_ids: list[str]) -> str | None:
    """Suggest the closest canonical id for ``raw`` (None when nothing is close).

    Comparison is on normalised wording so case/punctuation never blocks a match;
    the returned suggestion is the original canonical id.
    """
    lookup: dict[str, str] = {}
    for canonical in canonical_ids:
        lookup.setdefault(normalise_wording(canonical), canonical)
    matches = difflib.get_close_matches(normalise_wording(raw), list(lookup), n=1, cutoff=0.8)
    return lookup[matches[0]] if matches else None


def build_review_queue(
    labels: list[DayLabel], canonical_ids: list[str] | None = None
) -> ReviewQueue:
    """Collect events with ``label=None`` into a counted, suggested review queue."""
    canonical_ids = sorted(canonical_ids) if canonical_ids else []
    counts: Counter[str] = Counter()
    owners: dict[str, set[str]] = {}
    for day in labels:
        for event in day.events:
            if event.label is None and event.raw_label.strip():
                counts[event.raw_label] += 1
                owners.setdefault(event.raw_label, set()).add(day.image_id)
    items = [
        ReviewItem(
            raw_label=raw,
            count=count,
            image_ids=sorted(owners[raw]),
            suggestion=suggest_canonical(raw, canonical_ids),
        )
        for raw, count in sorted(counts.items())
    ]
    return ReviewQueue(items=items)
