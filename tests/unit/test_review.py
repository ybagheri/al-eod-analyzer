"""Unit tests: review service (apply, history, gold, stratified, stats)."""

from __future__ import annotations

import datetime
from pathlib import Path

from brooks_lab.application.review import (
    CorrectionsFile,
    ReviewService,
    compute_label_stats,
    stratified_candidates,
)
from brooks_lab.domain.clock import Clock
from brooks_lab.domain.imaging import ImageRecord, Manifest
from brooks_lab.domain.labels import DayLabel, DayType, EventKind, EventLabel, ExtractionMeta


class FixedClock(Clock):
    """Deterministic clock."""

    def now(self) -> datetime.datetime:
        """Return a fixed instant."""
        return datetime.datetime(2026, 10, 12, tzinfo=datetime.UTC)


def _meta() -> ExtractionMeta:
    return ExtractionMeta(provider="file", model_id="m", prompt_version="extract_v1")


def _label(image_id: str, day_type: DayType = DayType.TRADING_RANGE) -> DayLabel:
    return DayLabel(
        image_id=image_id,
        date=datetime.date(2022, 8, 4),
        day_type=day_type,
        events=[EventLabel(label=EventKind.WEDGE, raw_label="Wedge")],
        extraction_meta=_meta(),
    )


def _service(tmp_path: Path, *labels: DayLabel) -> ReviewService:
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    for label in labels:
        (labels_dir / f"{label.image_id}.json").write_text(
            label.model_dump_json(indent=2), encoding="utf-8"
        )
    return ReviewService(
        labels_dir=labels_dir,
        history_dir=tmp_path / "history",
        gold_path=tmp_path / "gold.json",
        clock=FixedClock(),
        reviewer="tester",
    )


def test_apply_corrections_archives_history_and_marks_human(tmp_path: Path) -> None:
    service = _service(tmp_path, _label("id-1"))
    result = service.apply_corrections(
        CorrectionsFile(
            image_id="id-1",
            day_type="spike_and_channel_bull",
            events=[EventLabel(label=EventKind.SPIKE, raw_label="Spike")],
            mark_gold=True,
            reviewer="tester",
            note="looks right",
        )
    )
    assert result.applied and result.revision == 1 and result.gold
    revised = service.load_label("id-1")
    assert revised.day_type is DayType.SPIKE_AND_CHANNEL_BULL
    assert revised.events[0].source.value == "human"
    history = list((tmp_path / "history").glob("id-1.rev*.json"))
    assert len(history) == 1
    assert service.history_revisions("id-1") == [1]
    gold = service.load_gold()
    assert gold.image_ids == ["id-1"]
    assert gold.notes["id-1"] == "looks right"
    assert gold.updated_at == datetime.datetime(2026, 10, 12, tzinfo=datetime.UTC)
    second = service.apply_corrections(CorrectionsFile(image_id="id-1", mark_gold=True))
    assert second.revision == 2 and second.gold
    assert service.history_revisions("id-1") == [1, 2]


def test_apply_rejects_missing_label_and_invalid_values(tmp_path: Path) -> None:
    service = _service(tmp_path, _label("id-1"))
    missing = service.apply_corrections(CorrectionsFile(image_id="nope"))
    assert not missing.applied and missing.revision == 0
    bad = service.apply_corrections(CorrectionsFile(image_id="id-1", day_type="not_a_type"))
    assert not bad.applied
    assert (tmp_path / "labels" / "id-1.json").is_file()
    assert service.history_revisions("id-1") == []


def test_gold_flag_integrity(tmp_path: Path) -> None:
    service = _service(tmp_path, _label("a"), _label("b"))
    assert service.load_gold().image_ids == []
    service.apply_corrections(CorrectionsFile(image_id="b", mark_gold=True, reviewer="r"))
    reloaded = ReviewService(
        labels_dir=tmp_path / "labels",
        history_dir=tmp_path / "history",
        gold_path=tmp_path / "gold.json",
    )
    assert reloaded.load_gold().image_ids == ["b"]


def test_stratified_candidates_deterministic() -> None:
    labels = [
        _label("id-1", DayType.TRADING_RANGE),
        _label("id-2", DayType.TRADING_RANGE),
        _label("id-3", DayType.SPIKE_AND_CHANNEL_BULL),
    ]
    first = stratified_candidates(labels, per_type=1, seed=7)
    assert stratified_candidates(labels, per_type=1, seed=7) == first
    assert len(first) == 2
    assert {i for i in first} <= {"id-1", "id-2", "id-3"}
    assert len(stratified_candidates(labels, per_type=5, seed=7)) == 3


def test_label_stats_math() -> None:
    labels = [
        _label("id-1", DayType.TRADING_RANGE),
        _label("id-2", DayType.SPIKE_AND_CHANNEL_BULL),
    ]
    stats = compute_label_stats(labels, {"id-1"})
    assert stats.total == 2
    assert stats.day_type_counts == {"spike_and_channel_bull": 1, "trading_range": 1}
    assert stats.events_per_day_mean == 1.0
    assert stats.event_counts == {"wedge": 2}
    assert stats.top_pairs == []
    assert stats.gold_count == 1
    assert compute_label_stats([], set()).events_per_day_mean == 0.0


def test_manifest_helper_loads_only_existing(tmp_path: Path) -> None:
    from brooks_lab.application.review import load_labels_for_manifest

    service = _service(tmp_path, _label("id-1"))
    manifest = Manifest(
        records=[
            ImageRecord(image_id="id-1", filename="a.jpg", sha256="0" * 64),
            ImageRecord(image_id="id-9", filename="b.jpg", sha256="1" * 64),
        ]
    )
    loaded = load_labels_for_manifest(manifest, service.labels_dir)
    assert [label.image_id for label in loaded] == ["id-1"]


def test_manifest_helper_dedups_hash_alias_rows(tmp_path: Path) -> None:
    from brooks_lab.application.review import load_labels_for_manifest

    service = _service(tmp_path, _label("id-1"))
    manifest = Manifest(
        records=[
            ImageRecord(image_id="id-1", filename="a.jpg", sha256="0" * 64),
            ImageRecord(
                image_id="id-1", filename="a-alias.jpg", sha256="0" * 64, duplicate_of="id-1"
            ),
        ]
    )
    loaded = load_labels_for_manifest(manifest, service.labels_dir)
    assert [label.image_id for label in loaded] == ["id-1"]


def _remap_label() -> DayLabel:
    meta = ExtractionMeta(provider="file", model_id="m", prompt_version="extract_v1")
    return DayLabel(
        image_id="id-1",
        date=datetime.date(2022, 8, 4),
        extraction_meta=meta,
        events=[
            EventLabel(label=None, raw_label="OO"),
            EventLabel(label=EventKind.GAP, raw_label="Measuring Gap"),
            EventLabel(label=EventKind.WEDGE, raw_label="Wedge"),
        ],
    )


def test_remap_events_only_touches_matches(tmp_path: Path) -> None:
    from brooks_lab.application.review import EventRemap
    from brooks_lab.domain.labels import Direction

    service = _service(tmp_path, _remap_label())
    result = service.remap_events(
        "id-1",
        [
            EventRemap(
                raw_label="OO",
                new_label=EventKind.OUTSIDE_OUTSIDE,
                direction=Direction.NEUTRAL,
            ),
            EventRemap(raw_label="Wedge", new_label=EventKind.TRIANGLE),
        ],
        reviewer="tester",
    )
    assert result.applied and result.revision == 1
    revised = service.load_label("id-1")
    by_raw = {e.raw_label: e for e in revised.events}
    assert by_raw["OO"].label is EventKind.OUTSIDE_OUTSIDE
    assert by_raw["OO"].source.value == "human"
    assert by_raw["OO"].direction is Direction.NEUTRAL
    # Already-mapped Wedge is skipped by default; Gap untouched entirely.
    assert by_raw["Wedge"].label is EventKind.WEDGE
    assert by_raw["Wedge"].source.value == "vision"
    assert by_raw["Measuring Gap"].label is EventKind.GAP
    assert service.history_revisions("id-1") == [1]


def test_remap_include_mapped_demotes(tmp_path: Path) -> None:
    from brooks_lab.application.review import EventRemap

    service = _service(tmp_path, _remap_label())
    result = service.remap_events(
        "id-1",
        [EventRemap(raw_label="Measuring Gap", new_label=None, include_mapped=True)],
    )
    assert result.applied
    revised = service.load_label("id-1")
    gap = next(e for e in revised.events if e.raw_label == "Measuring Gap")
    assert gap.label is None
    assert gap.source.value == "human"
    # Re-running the same rules is a no-op (no spurious new revision).
    rerun = service.remap_events(
        "id-1",
        [EventRemap(raw_label="Measuring Gap", new_label=None, include_mapped=True)],
    )
    assert not rerun.applied
    assert service.history_revisions("id-1") == [1]


def test_remap_no_match_and_missing(tmp_path: Path) -> None:
    service = _service(tmp_path, _remap_label())
    assert not service.remap_events("id-1", []).applied
    assert "no matches" in service.remap_events("id-1", []).message
    assert not service.remap_events("absent", []).applied


def test_apply_date_explicit_null_vs_absent(tmp_path: Path) -> None:
    service = _service(tmp_path, _label("id-1"))
    assert service.load_label("id-1").date == datetime.date(2022, 8, 4)
    cleared = service.apply_corrections(
        CorrectionsFile.model_validate({"image_id": "id-1", "date": None})
    )
    assert cleared.applied
    assert service.load_label("id-1").date is None
    kept = service.apply_corrections(CorrectionsFile(image_id="id-1"))
    assert kept.applied
    assert service.load_label("id-1").date is None
    reset = service.apply_corrections(
        CorrectionsFile(image_id="id-1", date=datetime.date(2022, 8, 4))
    )
    assert reset.applied
    assert service.load_label("id-1").date == datetime.date(2022, 8, 4)
