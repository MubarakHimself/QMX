"""The Story 5.3 verify reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "verify_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)]),
        "PYTHONIOENCODING": "utf-8",
    }
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (
        "node/ops pointers: cadence/RPO/RTO/retention remain null "
        "(never filled from a recommendation)" in completed.stdout
    )
    assert "snapshot alone: policy rejection (no recoverability claim)" in completed.stdout
    assert "sample-restore: recoverability claimed" in completed.stdout
    assert "corrupt restore: storage failure (no recoverability claim)" in completed.stdout
    assert (
        "migration: preflight → backup-first → dry-run → migrate → verify; "
        "source untouched; recoverability via full-restore rehearsal" in completed.stdout
    )


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
