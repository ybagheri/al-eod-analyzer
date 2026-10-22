"""Unit tests: extraction-queue dirty-tree guard."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from brooks_lab.infrastructure.queue_guard import queue_dirty


class FakeRunner:
    """Fake subprocess runner: first call = rev-parse, second = status."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "E:/repo\n",
        status_returncode: int = 0,
        status_stdout: str = "",
        raise_oserror: bool = False,
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.status_returncode = status_returncode
        self.status_stdout = status_stdout
        self.raise_oserror = raise_oserror
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((tuple(cmd), kwargs))
        if self.raise_oserror:
            raise OSError("git not found")
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, "")
        return subprocess.CompletedProcess(cmd, self.status_returncode, self.status_stdout, "")


def test_queue_dirty_false_when_clean(tmp_path: Path) -> None:
    runner = FakeRunner(stdout="E:/repo\n")
    assert queue_dirty(tmp_path, runner=runner) is False
    assert runner.calls[1][0][:3] == ("git", "status", "--porcelain")


def test_queue_dirty_true_when_output(tmp_path: Path) -> None:
    runner = FakeRunner(stdout="E:/repo\n", status_stdout="?? queue/x.response.json\n")
    assert queue_dirty(tmp_path, runner=runner) is True


def test_queue_dirty_fail_closed_on_git_error(tmp_path: Path) -> None:
    assert queue_dirty(tmp_path, runner=FakeRunner(status_returncode=128)) is True
    assert queue_dirty(tmp_path, runner=FakeRunner(raise_oserror=True)) is True


def test_queue_dirty_open_outside_work_tree(tmp_path: Path) -> None:
    assert queue_dirty(tmp_path, runner=FakeRunner(returncode=128)) is False


def test_queue_dirty_false_when_dir_missing(tmp_path: Path) -> None:
    assert queue_dirty(tmp_path / "nope") is False
