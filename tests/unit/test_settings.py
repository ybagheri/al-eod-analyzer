"""Unit tests: ingestion settings loader fallbacks."""

from __future__ import annotations

from pathlib import Path

from brooks_lab.infrastructure.settings import (
    DEFAULT_MIN_HEIGHT,
    DEFAULT_MIN_WIDTH,
    load_ingestion_settings,
)


def test_no_config_gives_defaults() -> None:
    settings = load_ingestion_settings(None)
    assert (settings.min_width, settings.min_height) == (
        DEFAULT_MIN_WIDTH,
        DEFAULT_MIN_HEIGHT,
    )


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    settings = load_ingestion_settings(tmp_path / "absent.yaml")
    assert (settings.min_width, settings.min_height) == (
        DEFAULT_MIN_WIDTH,
        DEFAULT_MIN_HEIGHT,
    )


def test_repo_default_config(tmp_path: Path) -> None:
    repo_config = Path(__file__).resolve().parents[2] / "config" / "default.yaml"
    settings = load_ingestion_settings(repo_config)
    assert settings.min_width == 400
    assert settings.min_height == 300


def test_partial_and_bad_configs_fall_back(tmp_path: Path) -> None:
    partial = tmp_path / "partial.yaml"
    partial.write_text("ingestion:\n  min_width: 100\n", encoding="utf-8")
    assert load_ingestion_settings(partial).min_width == 100
    assert load_ingestion_settings(partial).min_height == DEFAULT_MIN_HEIGHT

    bad = tmp_path / "bad.yaml"
    bad.write_text("ingestion:\n  min_width: wide\n", encoding="utf-8")
    assert load_ingestion_settings(bad) == load_ingestion_settings(None)

    not_mapping = tmp_path / "flat.yaml"
    not_mapping.write_text("- just\n- a\n- list\n", encoding="utf-8")
    assert load_ingestion_settings(not_mapping) == load_ingestion_settings(None)
