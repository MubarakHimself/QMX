"""The Story 3.6 logbooks example must stay executable (L27, tier-1 artifact).

Runs ``examples/logbooks_usage.py`` as a fresh process and checks it exits clean and
demonstrates the Book projection with the command-fingerprint join, the FM-11 cross-role
guard and its declared exception, the legacy Records projection names, and the role-scoped
namespaces.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "logbooks_usage.py"
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
        "live Book journal (join): 5 rows, "
        "types=['decision', 'control action', 'decision', 'order', 'fill']" in completed.stdout
    )
    assert (
        "cross-role guard: refusal=policy rejection; declared multi-role read spans 2 roles"
        in completed.stdout
    )
    assert (
        "veto_ledger (refused-by-door) doors=['spread-door']; trade_journal rows=2; veto rows=1"
        in completed.stdout
    )
    assert "role-scoped namespaces: live='live', paper-benched='paper-benched'" in completed.stdout
    assert "binding identity is generic qmf-core-noun value: True" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it, so its
    self-checks would silently vanish. It uses real raise-based checks instead."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
