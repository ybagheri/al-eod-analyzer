"""Unit tests: extraction prompt builder (deterministic, versioned, complete)."""

from __future__ import annotations

from pathlib import Path

from brooks_lab.application.extraction import ExtractionPromptBuilder
from brooks_lab.infrastructure.taxonomy import load_taxonomy


def _builder(tmp_path: Path) -> ExtractionPromptBuilder:
    template = tmp_path / "extract_v1.md"
    template.write_text("# Template\n", encoding="utf-8")
    taxonomy = load_taxonomy(Path(__file__).resolve().parents[2] / "config" / "taxonomy.yaml")
    return ExtractionPromptBuilder(template, taxonomy)


def test_prompt_is_deterministic_and_versioned(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    assert builder.prompt_version == "extract_v1"
    first = builder.build("img-1", "2022-07-29", "file", "manual")
    second = builder.build("img-1", "2022-07-29", "file", "manual")
    assert first == second
    assert builder.build("img-2", "2022-07-29", "file", "manual") != first


def test_prompt_contains_taxonomy_schema_and_context(tmp_path: Path) -> None:
    prompt = _builder(tmp_path).build("img-1", "2022-07-29", "file", "manual")
    for marker in (
        "# Template",
        "spike_and_channel_bull",
        "buy_the_close",
        "lower_high_double_top",
        "DayLabel v1",
        "raw_label",
        "image_id: img-1",
        "date: 2022-07-29",
        "provider: file",
        "model_id: manual",
    ):
        assert marker in prompt


def test_repo_prompt_v2_has_reviewer_rules() -> None:
    template = Path(__file__).resolve().parents[2] / "config" / "prompts" / "extract_v2.md"
    text = template.read_text(encoding="utf-8")
    for rule in (
        "TIME/POSITION RULE",
        "EVIDENCE RULE",
        "STACKED-NOTES RULE",
        "CROSS-IMAGE TIME RULE",
        "QUALIFIED LABELS RULE",
        '"prompt_version": "extract_v2"',
    ):
        assert rule in text
