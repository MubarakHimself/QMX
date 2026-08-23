"""The Story 10.10 CT-25/CT-32 reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "journal_performance_usage.py"
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
    assert "entity journals: entity holds no WriterId (invalid input)" in completed.stdout
    assert "legacy mapping: veto_ledger ->" in completed.stdout
    assert "command-fingerprint join: version=" in completed.stdout
    assert "veto_ledger rows: 1 (outcome=refused-by-door)" in completed.stdout
    assert "journal-before-dispatch: storage failure blocks dispatch" in completed.stdout
    assert "no composite score: composite-score refused (policy rejection)" in completed.stdout
    assert "multi-role result: refused (policy rejection)" in completed.stdout
    assert "publish-never-act: bench refused (policy rejection)" in completed.stdout
    assert "replay-world result: never gates live money" in completed.stdout
    assert "bench crossing: governed producer threshold_crossed=True" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
