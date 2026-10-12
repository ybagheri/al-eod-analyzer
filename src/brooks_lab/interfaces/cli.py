"""Command-line interface for Brooks Lab.

Provides the ``brooks`` console script. Phase 0 exposes only ``--version``
(and ``version`` subcommand); later phases add ``ingest``, ``extract``, etc.
"""

from __future__ import annotations

import typer

from brooks_lab import __version__

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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
