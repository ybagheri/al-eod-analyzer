"""Clock port: injectable time source (domain stays free of wall-clock calls)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Port for current time. Inject fakes in tests for determinism."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware datetime."""
        ...


class SystemClock:
    """Production clock: real wall-clock time in UTC."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)
