"""The Story 10.9 CT-31 reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "control_window_usage.py"
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
    assert "instrument scope: symbol currency parse refused (policy rejection)" in completed.stdout
    assert "resolved scope instruments: ['EURUSD', 'USDJPY']" in completed.stdout
    assert "news window: two instants" in completed.stdout
    assert "entries-only: exit block refused (policy rejection)" in completed.stdout
    assert "blocked entry under book_mode=LIVE" in completed.stdout
    assert "blocked entry under book_mode=PAPER" in completed.stdout
    assert "veto path: door=control-window path=veto" in completed.stdout
    assert "widen-never-shrink fold: [800, 2500) from 3 revisions" in completed.stdout
    assert "fail closed: unknown_coverage blocks; no live skip button" in completed.stdout
    assert "handover kind=session_handover_buffer anchor=both" in completed.stdout
    assert "window_forced_flat V1 declares_none rank=2" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
