"""Tiny typed settings loader (Phase 1: ingestion section only).

All engine/ingestion thresholds must be named parameters; this loader reads them
from ``config/default.yaml`` with safe built-in fallbacks so the CLI works even
when the config file is absent. Full env-override settings arrive in a later phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_MIN_WIDTH = 400
DEFAULT_MIN_HEIGHT = 300


@dataclass(frozen=True, slots=True)
class IngestionSettings:
    """Thresholds for image ingestion."""

    min_width: int = DEFAULT_MIN_WIDTH
    min_height: int = DEFAULT_MIN_HEIGHT


def load_ingestion_settings(config_path: Path | None = None) -> IngestionSettings:
    """Load ingestion thresholds; fall back to defaults when unavailable.

    Never raises for a missing/invalid file: logs a warning and returns defaults.
    """
    if config_path is None:
        return IngestionSettings()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Cannot read config %s (%s); using defaults.", config_path, exc)
        return IngestionSettings()
    if not isinstance(raw, dict):
        logger.warning("Config %s is not a mapping; using defaults.", config_path)
        return IngestionSettings()
    section = raw.get("ingestion", {})
    if not isinstance(section, dict):
        logger.warning("Config %s has no ingestion mapping; using defaults.", config_path)
        return IngestionSettings()
    try:
        min_width = int(section.get("min_width", DEFAULT_MIN_WIDTH))
        min_height = int(section.get("min_height", DEFAULT_MIN_HEIGHT))
    except (TypeError, ValueError) as exc:
        logger.warning("Bad ingestion values in %s (%s); using defaults.", config_path, exc)
        return IngestionSettings()
    return IngestionSettings(min_width=min_width, min_height=min_height)
