"""Vision-client port and implementations (Phase 3).

The pipeline never assumes an online model: ``FileExchangeVisionClient`` works
with any image-capable chat model (including the coding agent itself) via
request/response JSON files, and ``FakeVisionClient`` keeps tests offline.
``AnthropicVisionClient`` is optional and needs an API key; it is never used
by tests or the quality gate.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class VisionError(Exception):
    """Base error for vision extraction failures."""


class MissingResponseError(VisionError):
    """No human/agent response is available yet (file-exchange pending)."""


class VisionClient(Protocol):
    """Port: turn one chart image + prompt into a raw label dict."""

    @property
    def model_id(self) -> str:
        """Provider/model identifier recorded in every extraction."""
        ...

    def extract(self, image_bytes: bytes, prompt: str, *, image_id: str = "") -> dict[str, Any]:
        """Return the model's raw JSON object for one image. May raise VisionError."""
        ...


@dataclass
class FakeVisionClient:
    """Deterministic canned client for tests and offline demos."""

    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_response: dict[str, Any] = field(default_factory=dict)
    failures_before_success: int = 0
    model_id: str = "fake"
    attempts: int = 0

    def extract(self, image_bytes: bytes, prompt: str, *, image_id: str = "") -> dict[str, Any]:
        """Return a canned response, optionally failing first to test retries."""
        _ = (image_bytes, prompt)
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise VisionError(f"injected flaky failure #{self.attempts}")
        if image_id and image_id in self.responses:
            return dict(self.responses[image_id])
        return dict(self.default_response)


@dataclass
class FileExchangeVisionClient:
    """Agent-in-the-loop client: request/response JSON files, no API key.

    ``extract()`` (idempotently) writes ``<image_id>.request.json`` into the
    queue dir, then loads ``<image_id>.response.json`` if a human/agent wrote
    one, else raises :class:`MissingResponseError` so the service marks the
    image pending instead of failing it.
    """

    queue_dir: Path
    model_id: str = "manual"

    def write_request(self, image_id: str, prompt: str) -> Path:
        """Persist ``<image_id>.request.json`` (idempotent). Returns its path."""
        if not image_id:
            raise VisionError("FileExchangeVisionClient needs image_id=")
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        request_path = self.queue_dir / f"{image_id}.request.json"
        request_path.write_text(
            json.dumps(
                {"image_id": image_id, "prompt": prompt, "model_hint": self.model_id},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return request_path

    def extract(self, image_bytes: bytes, prompt: str, *, image_id: str = "") -> dict[str, Any]:
        """Write the request file, then load the response or raise pending."""
        _ = image_bytes
        if not image_id:
            raise VisionError("FileExchangeVisionClient.extract needs image_id=")
        self.write_request(image_id, prompt)
        response_path = self.queue_dir / f"{image_id}.response.json"
        if not response_path.is_file():
            raise MissingResponseError(f"awaiting response for {image_id}")
        try:
            payload = json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise VisionError(f"response for {image_id} is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise VisionError(f"response for {image_id} must be a JSON object")
        return payload


@dataclass
class AnthropicVisionClient:
    """Optional online client for the Anthropic Messages API (image input)."""

    api_key: str = ""
    model_id: str = ""
    timeout_s: float = 60.0
    max_tokens: int = 2000

    def __post_init__(self) -> None:
        """Resolve credentials from args or environment (never logged)."""
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise VisionError("AnthropicVisionClient needs ANTHROPIC_API_KEY (or api_key=)")
        self.api_key = key
        if not self.model_id:
            env_model = os.environ.get("BROOKS_VISION_MODEL", "")
            if not env_model:
                raise VisionError("AnthropicVisionClient needs a model id (--model-id)")
            self.model_id = env_model

    def extract(self, image_bytes: bytes, prompt: str, *, image_id: str = "") -> dict[str, Any]:
        """Call the Messages API once and parse the JSON object from the reply."""
        _ = image_id
        try:
            import httpx
        except ModuleNotFoundError as exc:
            raise VisionError(
                'httpx is not installed; run `pip install -e ".[vision]"` '
                "or use the offline file-exchange provider"
            ) from exc

        encoded = base64.standard_b64encode(image_bytes).decode("ascii")
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_id,
                    "max_tokens": self.max_tokens,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": encoded,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                },
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            blocks = response.json().get("content", [])
            text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        # Any transport/API failure becomes a VisionError with no secret content.
        except Exception as exc:
            raise VisionError(f"anthropic call failed: {type(exc).__name__}") from exc
        return _parse_json_object(text)


def _parse_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from model text (fences tolerated once)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VisionError(f"model reply is not a JSON object: {exc}") from exc
    if not isinstance(payload, dict):
        raise VisionError("model reply must be a JSON object")
    return payload
