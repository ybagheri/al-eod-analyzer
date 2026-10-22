"""Unit tests for overnight clock-time normalization (24:00 -> 00:00)."""

from __future__ import annotations

from brooks_lab.application.extraction import normalize_overnight_times


def test_malformed_overnight_hours_are_normalized() -> None:
    payload = {
        "events": [
            {
                "label": "channel",
                "start_time": {"time": "24:00", "tz": "America/Los_Angeles"},
                "end_time": {"time": "02:40", "tz": "America/Los_Angeles"},
            },
            {
                "label": "range",
                "start_time": {"time": "23:20", "tz": "America/Los_Angeles"},
                "end_time": {"time": "25:15", "tz": "America/Los_Angeles"},
            },
        ]
    }
    fixed = normalize_overnight_times(payload)
    assert fixed["events"][0]["start_time"]["time"] == "00:00"
    assert fixed["events"][0]["end_time"]["time"] == "02:40"
    assert fixed["events"][1]["start_time"]["time"] == "23:20"
    assert fixed["events"][1]["end_time"]["time"] == "01:15"


def test_input_payload_is_not_mutated() -> None:
    payload = {"events": [{"label": "x", "start_time": {"time": "24:00", "tz": "ET"}}]}
    normalize_overnight_times(payload)
    assert payload["events"][0]["start_time"]["time"] == "24:00"


def test_payload_without_events_or_v3_is_untouched() -> None:
    assert normalize_overnight_times({"scope_ok": True}) == {"scope_ok": True}
    assert normalize_overnight_times("legacy") == "legacy"
