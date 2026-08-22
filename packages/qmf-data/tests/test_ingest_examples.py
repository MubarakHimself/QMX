"""The Story 6.1 CT-15 ingest reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "ingest_usage.py"
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
    assert "CT-15 -> CT-10 routed:" in completed.stdout
    assert "idempotent key; revision is a new fp1 artifact" in completed.stdout
    assert "foreign timestamp and money: stored verbatim" in completed.stdout
    assert "incomplete / unmapped instrument: invalid input" in completed.stdout
    assert "rate-limit: transient venue failure; no fabricated observation" in completed.stdout
    assert "scheduler/daemon ask: policy rejection (called port only)" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
