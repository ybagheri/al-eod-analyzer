"""Engine purity guard (plan v2.6 S1 item 1, MQL5 parity).

`src/brooks_lab/engine/` must import only the Python standard library (and
itself). Violations fail the gate before heavy wheels can creep in again
(pandas/numpy/opencv/pytesseract live in separate extras and are forbidden
here for exact MQL5 parity).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE_DIR = REPO / "src" / "brooks_lab" / "engine"

LOCAL_FIRST_PARTS = {"brooks_lab"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names if a.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_engine_imports_are_stdlib_only() -> None:
    assert ENGINE_DIR.is_dir(), "engine package missing"
    sources = list(ENGINE_DIR.rglob("*.py"))
    assert sources, "engine package has no python files"
    stdlib = set(sys.stdlib_module_names)
    violations: dict[str, set[str]] = {}
    for path in sources:
        bad = {
            root for root in _imports(path) if root not in stdlib and root not in LOCAL_FIRST_PARTS
        }
        if bad:
            violations[str(path.relative_to(REPO))] = bad
    assert not violations, f"engine must stay stdlib-only; violations: {violations}"
