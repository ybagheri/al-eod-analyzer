"""Command-line interface for Brooks Lab.

Phase 1 adds ``ingest`` and ``manifest-stats``; later phases add ``extract`` etc.
"""

from __future__ import annotations

from pathlib import Path

import typer

from brooks_lab import __version__
from brooks_lab.application.ingestion import ImageIngestionService, compute_stats
from brooks_lab.infrastructure.settings import load_ingestion_settings
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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
