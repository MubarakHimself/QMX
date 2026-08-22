"""The Story 3.4 splits/seal example must stay executable (L27, tier-1 artifact).

Runs ``examples/splits_usage.py`` as a fresh process and checks it exits clean and
demonstrates the fingerprinted manifest, knowledge-time partitioning, the seal enforced at
every read boundary, the one journaled final look, and the foreign-calendar refusal.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "splits_usage.py"
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
    assert (
        "split manifest: 3 default segments, split_id derived from fp1 (widths=50 ns)"
        in completed.stdout
    )
    assert (
        "record partition: knowledge-time 1500 -> validation; straddle -> policy rejection"
        in completed.stdout
    )
    assert "seal at 4 read boundaries: policy rejection; pre-seal read: allowed" in completed.stdout
    assert (
        "final look: sealed-period-final-look; second look: policy rejection; "
        "after look: policy rejection" in completed.stdout
    )
    assert "foreign calendar row: policy rejection" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it, so
    its self-checks would silently vanish. It uses real raise-based checks instead."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
