"""Command-line interface for Brooks Lab.

Phase 2 adds ``schema-export``; later phases add ``extract`` etc.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from brooks_lab import __version__
from brooks_lab.application.extraction import ExtractionPromptBuilder, ExtractionService
from brooks_lab.application.ingestion import ImageIngestionService, compute_stats
from brooks_lab.domain.labels import LABEL_SCHEMA_VERSION, DayLabel
from brooks_lab.infrastructure.settings import load_ingestion_settings
from brooks_lab.infrastructure.taxonomy import load_taxonomy
from brooks_lab.infrastructure.vision import (
    AnthropicVisionClient,
    FakeVisionClient,
    FileExchangeVisionClient,
    VisionClient,
)
from brooks_lab.interfaces.contact_sheet import render_contact_sheet

app = typer.Typer(
    name="brooks",
    help="Al EOD Analyzer: Brooks-style EOD chart labelling and pattern engine.",
    no_args_is_help=False,
)


def _print_version() -> None:
    typer.echo(f"brooks {__version__}")


@app.callback(invoke_without_command=True)
def _callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the version and exit.",
        is_eager=True,
    ),
) -> None:
    """Global options callback."""
    if version:
        _print_version()
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def version() -> None:
    """Show the version and exit."""
    _print_version()


@app.command()
def ingest(
    data_dir: Path = typer.Option(
        Path("data"), "--data-dir", help="Folder with chart screenshots."
    ),
    manifest: Path = typer.Option(
        Path("artifacts/manifest.json"), "--manifest", help="Manifest JSON to write."
    ),
    config_file: Path = typer.Option(
        Path("config/default.yaml"), "--config", help="YAML config with thresholds."
    ),
    review_dir: Path = typer.Option(
        Path("artifacts/review"), "--review-dir", help="Folder for the contact sheet."
    ),
) -> None:
    """Scan images, write the manifest, and regenerate the contact sheet."""
    settings = load_ingestion_settings(config_file)
    service = ImageIngestionService(settings=settings)
    result = service.scan_and_write(data_dir, manifest)
    stats = compute_stats(result)
    sheet = render_contact_sheet(result.records, stats, review_dir / "contact_sheet.html", data_dir)
    typer.echo(
        f"ingested {stats.total} images "
        f"(ok={stats.ok} duplicates={stats.duplicates} "
        f"corrupt={stats.corrupt} tiny={stats.tiny}) -> {manifest}"
    )
    typer.echo(f"contact sheet -> {sheet}")


@app.command(name="manifest-stats")
def manifest_stats(
    manifest: Path = typer.Option(
        Path("artifacts/manifest.json"), "--manifest", help="Manifest JSON to read."
    ),
    output: Path = typer.Option(
        Path("artifacts/ingestion_stats.json"),
        "--output",
        help="Stats JSON to write.",
    ),
) -> None:
    """Print and save aggregate statistics for an existing manifest."""
    service = ImageIngestionService()
    loaded = service.read_manifest(manifest)
    stats = compute_stats(loaded)
    service.write_stats(stats, output)
    typer.echo(
        f"total={stats.total} ok={stats.ok} duplicates={stats.duplicates} "
        f"corrupt={stats.corrupt} tiny={stats.tiny}"
    )
    typer.echo(f"date range: {stats.date_min}..{stats.date_max}")
    typer.echo(f"missing dates: {[d.isoformat() for d in stats.missing_dates]}")
    typer.echo(f"formats: {stats.formats} widths: {stats.width_buckets}")
    typer.echo(f"stats -> {output}")


@app.command(name="schema-export")
def schema_export(
    output: Path = typer.Option(
        Path("artifacts/label_schema.json"),
        "--output",
        help="JSON Schema file to write.",
    ),
) -> None:
    """Export the DayLabel JSON Schema (label schema v1)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": LABEL_SCHEMA_VERSION,
        "day_label": DayLabel.model_json_schema(),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    typer.echo(f"label schema v{LABEL_SCHEMA_VERSION} -> {output}")


@app.command()
def extract(
    provider: str = typer.Option(
        "file", "--provider", help="Vision provider: file|fake|anthropic."
    ),
    limit: int | None = typer.Option(None, "--limit", help="Max images to process."),
    resume: bool = typer.Option(True, "--resume/--no-resume", help="Skip valid existing labels."),
    model_id: str = typer.Option("manual", "--model-id", help="Model id recorded in extractions."),
    data_dir: Path = typer.Option(
        Path("data"), "--data-dir", help="Folder with chart screenshots."
    ),
    manifest: Path = typer.Option(
        Path("artifacts/manifest.json"), "--manifest", help="Manifest to read."
    ),
    labels_dir: Path = typer.Option(
        Path("artifacts/labels"), "--labels-dir", help="Labels to write."
    ),
    queue_dir: Path = typer.Option(
        Path("artifacts/extraction_queue"), "--queue-dir", help="File-exchange queue."
    ),
    failed_dir: Path = typer.Option(
        Path("artifacts/labels_failed"), "--failed-dir", help="Quarantine dir."
    ),
    prompt_file: Path = typer.Option(
        Path("config/prompts/extract_v1.md"), "--prompt-file", help="Prompt template."
    ),
    taxonomy_file: Path = typer.Option(
        Path("config/taxonomy.yaml"), "--taxonomy-file", help="Frozen taxonomy."
    ),
) -> None:
    """Extract DayLabels for manifest images (file-exchange needs two passes)."""
    loaded = ImageIngestionService.read_manifest(manifest)
    taxonomy = load_taxonomy(taxonomy_file)
    builder = ExtractionPromptBuilder(prompt_file, taxonomy)
    if provider == "file":
        client: VisionClient = FileExchangeVisionClient(queue_dir=queue_dir, model_id=model_id)
    elif provider == "fake":
        client = FakeVisionClient(model_id=model_id)
    elif provider == "anthropic":
        client = AnthropicVisionClient(model_id=model_id)
    else:
        raise typer.BadParameter(f"unknown provider: {provider}")
    service = ExtractionService(
        manifest=loaded,
        data_dir=data_dir,
        labels_dir=labels_dir,
        failed_dir=failed_dir,
        client=client,
        prompt_builder=builder,
        provider=provider,
    )
    report = service.run(limit=limit, resume=resume)
    report_path = Path("artifacts/review/extraction_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    typer.echo(
        f"scanned={report.scanned} labeled={report.labeled} skipped={report.skipped} "
        f"pending={report.pending} quarantined={report.quarantined} "
        f"valid_rate={report.valid_rate:.2f}"
    )
    typer.echo(f"day types: {report.day_type_counts}")
    typer.echo(f"events: {report.event_counts}")
    if report.warnings:
        typer.echo(f"warnings: {report.warnings}")
    typer.echo(f"report -> {report_path}")


@app.command(name="extract-status")
def extract_status(
    manifest: Path = typer.Option(
        Path("artifacts/manifest.json"), "--manifest", help="Manifest to read."
    ),
    labels_dir: Path = typer.Option(Path("artifacts/labels"), "--labels-dir", help="Labels dir."),
    queue_dir: Path = typer.Option(
        Path("artifacts/extraction_queue"), "--queue-dir", help="File-exchange queue."
    ),
    failed_dir: Path = typer.Option(
        Path("artifacts/labels_failed"), "--failed-dir", help="Quarantine dir."
    ),
) -> None:
    """Show extraction progress across manifest, labels, queue, and failures."""
    loaded = ImageIngestionService.read_manifest(manifest)
    manifest_ids = {r.image_id for r in loaded.records}
    labels = {p.stem for p in labels_dir.glob("*.json")} if labels_dir.is_dir() else set()
    requests = (
        {p.name.replace(".request.json", "") for p in queue_dir.glob("*.request.json")}
        if queue_dir.is_dir()
        else set()
    )
    responses = (
        {p.name.replace(".response.json", "") for p in queue_dir.glob("*.response.json")}
        if queue_dir.is_dir()
        else set()
    )
    failed = (
        {p.name.replace(".error.json", "") for p in failed_dir.glob("*.error.json")}
        if failed_dir.is_dir()
        else set()
    )
    missing = sorted(manifest_ids - labels)
    typer.echo(f"manifest={len(manifest_ids)} labeled={len(manifest_ids & labels)}")
    typer.echo(f"missing={len(missing)} failed={len(failed)}")
    typer.echo(f"queue: requests={len(requests)} responses={len(responses)}")
    if missing:
        typer.echo(f"missing ids: {missing}")


@app.command(name="review-queue")
def review_queue(
    manifest: Path = typer.Option(
        Path("artifacts/manifest.json"), "--manifest", help="Manifest to read."
    ),
    data_dir: Path = typer.Option(
        Path("data"), "--data-dir", help="Folder with chart screenshots."
    ),
    labels_dir: Path = typer.Option(Path("artifacts/labels"), "--labels-dir", help="Labels dir."),
    taxonomy_file: Path = typer.Option(
        Path("config/taxonomy.yaml"), "--taxonomy-file", help="Frozen taxonomy."
    ),
    gold_file: Path = typer.Option(
        Path("artifacts/gold_set.json"), "--gold-file", help="Gold registry."
    ),
    review_dir: Path = typer.Option(
        Path("artifacts/review"), "--review-dir", help="Review pages output."
    ),
    output: Path = typer.Option(
        Path("artifacts/review/review_summary.json"),
        "--output",
        help="Summary JSON to write.",
    ),
) -> None:
    """Build review pages, taxonomy gap report, and label statistics."""
    from brooks_lab.application.review import (
        ReviewService,
        compute_label_stats,
        load_labels_for_manifest,
    )
    from brooks_lab.application.review_queue import build_review_queue
    from brooks_lab.domain.imaging import ImageRecord
    from brooks_lab.interfaces.review_pages import (
        image_rel_for_page,
        render_review_index,
        render_review_page,
    )

    loaded = ImageIngestionService.read_manifest(manifest)
    by_id: dict[str, ImageRecord] = {r.image_id: r for r in loaded.records}
    labels = load_labels_for_manifest(loaded, labels_dir)
    service = ReviewService(
        labels_dir=labels_dir,
        history_dir=labels_dir.parent / "labels_history",
        gold_path=gold_file,
    )
    gold = service.load_gold()
    gold_ids = set(gold.image_ids)
    taxonomy = load_taxonomy(taxonomy_file)
    canonical = sorted(taxonomy.day_types | taxonomy.events)
    queue = build_review_queue(labels, canonical)
    stats = compute_label_stats(labels, gold_ids)
    pages_dir = review_dir / "pages"
    for label in labels:
        record = by_id.get(label.image_id)
        filename = record.filename if record else f"{label.image_id}.png"
        page_path = pages_dir / f"{label.image_id}.html"
        render_review_page(
            label,
            image_rel_for_page(page_path, data_dir, filename),
            page_path,
            label.image_id in gold_ids,
            service.history_revisions(label.image_id),
        )
    render_review_index(labels, gold_ids, pages_dir / "index.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "review_queue": queue.model_dump(mode="json"),
                "stats": stats.model_dump(mode="json"),
                "gold_ids": sorted(gold_ids),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    typer.echo(f"labels={len(labels)} gold={len(gold_ids)} unmapped={len(queue.items)}")
    typer.echo(f"day types: {stats.day_type_counts}")
    for item in queue.items:
        typer.echo(f"gap: {item.raw_label!r} x{item.count} suggest={item.suggestion}")
    typer.echo(f"pages -> {pages_dir / 'index.html'}")
    typer.echo(f"summary -> {output}")


@app.command(name="review-apply")
def review_apply(
    corrections_file: Path = typer.Argument(..., help="Corrections JSON file."),
    labels_dir: Path = typer.Option(Path("artifacts/labels"), "--labels-dir", help="Labels dir."),
    history_dir: Path = typer.Option(
        Path("artifacts/labels_history"), "--history-dir", help="History dir."
    ),
    gold_file: Path = typer.Option(
        Path("artifacts/gold_set.json"), "--gold-file", help="Gold registry."
    ),
) -> None:
    """Apply a corrections file (archives history, marks human source)."""
    from brooks_lab.application.review import CorrectionsFile, ReviewService

    service = ReviewService(labels_dir=labels_dir, history_dir=history_dir, gold_path=gold_file)
    corrections = CorrectionsFile.model_validate_json(corrections_file.read_text(encoding="utf-8"))
    result = service.apply_corrections(corrections)
    typer.echo(
        f"{result.image_id}: applied={result.applied} rev={result.revision} "
        f"gold={result.gold} ({result.message})"
    )
    if not result.applied:
        raise typer.Exit(code=1)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
