"""The Story 3.5 journals example must stay executable (L27, tier-1 artifact).

Runs ``examples/journals_usage.py`` as a fresh process and checks it exits clean and
demonstrates the gapless wired producer, the decision-outcome projection, the fp1
correlation_id/display_time exclusion, the typed causal edge, the surfaced sequence-gap
loss, and block-on-unpersistable recovery.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "journals_usage.py"
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
    assert "gapless data-quality stream: sequences=[0, 1, 2]" in completed.stdout
    assert (
        "veto_ledger (refused-by-door) selects on the declared outcome: ['spread-door']"
        in completed.stdout
    )
    assert (
        "correlation_id excluded from fp1: True; display time (log): "
        "1970-01-01T00:00:01.000000000Z" in completed.stdout
    )
    assert (
        "cross-stream causal linkage is a typed edge: enacts (references fp1s)" in completed.stdout
    )
    assert "a sequence gap is surfaced as loss: storage failure" in completed.stdout
    assert (
        "block-on-unpersistable: recovered event landed=True, stream sequences=[0, 1]"
        in completed.stdout
    )


def test_example_uses_no_bare_assert() -> None:
    """L6: the shipped example must not rely on bare ``assert`` — ``-O`` strips it, so its
    self-checks would silently vanish. It uses real raise-based checks instead."""
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
