"""Unit tests: vision clients (fake, file-exchange, anthropic guards)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brooks_lab.infrastructure.vision import (
    AnthropicVisionClient,
    FakeVisionClient,
    FileExchangeVisionClient,
    MissingResponseError,
    VisionError,
)


def test_fake_returns_default_and_counts_attempts() -> None:
    client = FakeVisionClient(default_response={"a": 1})
    assert client.extract(b"img", "prompt") == {"a": 1}
    assert client.attempts == 1
    assert client.model_id == "fake"


def test_fake_per_image_responses() -> None:
    client = FakeVisionClient(responses={"id-1": {"a": 1}}, default_response={"b": 2})
    assert client.extract(b"img", "p", image_id="id-1") == {"a": 1}
    assert client.extract(b"img", "p", image_id="id-9") == {"b": 2}


def test_fake_flaky_then_success() -> None:
    client = FakeVisionClient(default_response={"ok": True}, failures_before_success=2)
    with pytest.raises(VisionError):
        client.extract(b"i", "p")
    with pytest.raises(VisionError):
        client.extract(b"i", "p")
    assert client.extract(b"i", "p") == {"ok": True}
    assert client.attempts == 3


def test_file_exchange_round_trip(tmp_path: Path) -> None:
    client = FileExchangeVisionClient(queue_dir=tmp_path, model_id="tester")
    with pytest.raises(MissingResponseError):
        client.extract(b"img", "prompt text", image_id="img-1")
    request = json.loads((tmp_path / "img-1.request.json").read_text(encoding="utf-8"))
    assert request["image_id"] == "img-1"
    assert request["prompt"] == "prompt text"
    assert request["model_hint"] == "tester"
    (tmp_path / "img-1.response.json").write_text('{"label": "ok"}', encoding="utf-8")
    assert client.extract(b"img", "prompt text", image_id="img-1") == {"label": "ok"}


def test_file_exchange_bad_responses(tmp_path: Path) -> None:
    client = FileExchangeVisionClient(queue_dir=tmp_path)
    (tmp_path / "bad.response.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(VisionError):
        client.extract(b"i", "p", image_id="bad")
    (tmp_path / "lst.response.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(VisionError):
        client.extract(b"i", "p", image_id="lst")
    with pytest.raises(VisionError):
        client.extract(b"i", "p")


def test_anthropic_requires_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("BROOKS_VISION_MODEL", raising=False)
    with pytest.raises(VisionError):
        AnthropicVisionClient()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(VisionError):
        AnthropicVisionClient()
    client = AnthropicVisionClient(api_key="k", model_id="m")
    assert client.model_id == "m"
