"""The Story 5.2 restore reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "restore_usage.py"
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
        "restore into replacement: timestamps verbatim; "
        "source untouched; off-machine version retained" in completed.stdout
    )
    assert "restored seal enforcement: policy rejection on sealed holdout" in completed.stdout
    assert (
        "cross-world / in-place / discard-only-copy: policy rejection "
        "(raw originals kept forever)" in completed.stdout
    )


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
