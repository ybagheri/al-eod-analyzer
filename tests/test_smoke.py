"""Smoke tests for the Phase 0 skeleton."""

from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from brooks_lab import __version__
from brooks_lab.interfaces.cli import app, main


def test_version_constant() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_cli_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "brooks" in result.output.lower()


def test_main_entry_point(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["brooks", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out
