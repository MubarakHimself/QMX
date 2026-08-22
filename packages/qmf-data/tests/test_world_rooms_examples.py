"""The Story 3.3 room-roles example must stay executable (L27, tier-1 artifact).

Runs ``examples/world_rooms_usage.py`` as a fresh process and checks it exits clean and
demonstrates the seven roles per world, the rebuildable-view pins, the retention law,
partition-scoped resolution, and the cross-world refusal.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "world_rooms_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)])}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "seven room-roles per world; simulated: policy rejection" in completed.stdout
    assert (
        "rebuildable view pins: engine=duckdb-1, calendar=forex-17NY:v3, tzdata=2025a"
        in completed.stdout
    )
    assert (
        "retention: raw deletable=False, uncited-view deletable=True, cited-view deletable=False"
        in completed.stdout
    )
    assert "series resolves within partition: dukascopy-ticks | dukascopy:EURUSD | 1000-2000" in (
        completed.stdout
    )
    assert "cross-world read: policy rejection" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it, so
    its self-checks would silently vanish. It uses real raise-based checks instead."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
