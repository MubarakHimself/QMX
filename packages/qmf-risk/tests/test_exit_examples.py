"""The Story 10.7 CT-29 reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "exit_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)]),
    }
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "single-sourced realized_r for protective-stop full loss: -51/50" in completed.stdout
    assert "whole-trade attribution credits opening bot=bot-alpha" in completed.stdout
    assert "bench fold: qualifying_loss_count=2" in completed.stdout
    assert "recording precedes interpretation: refused (stale evidence)" in completed.stdout
    assert "move-to-breakeven ratchet: zero-offset ok" in completed.stdout
    assert "kill_line_flat != protection_forced_flat: True" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
