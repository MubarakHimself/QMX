"""The CT-07 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/lineage_usage.py`` as a fresh process — the same subprocess idiom the
CT-06 example test uses — and checks it exits clean and demonstrates the typed edge and
its JSONL line, linear supersedes with one resolvable head, branches-from's several
heads, the idempotent/collision paths, the FM-2 refusals, and the single-writer law.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "lineage_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    # The example imports qmf.core and qmf.registry; put both on the path (the package
    # imports only qmf.core, but the example is executed as a standalone process).
    pythonpath = os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)])
    env = {**os.environ, "PYTHONPATH": pythonpath}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "typed edge JSONL line, LF-terminated: True" in completed.stdout
    assert "supersedes head resolves to one current: fp1:sha256:" in completed.stdout
    assert "second supersedes for a subject refused: policy rejection" in completed.stdout
    assert "branches-from allows several heads: 2" in completed.stdout
    assert "first append outcome: stored" in completed.stdout
    assert "true collision refused and alarmed: policy rejection" in completed.stdout
    assert "edge type outside the set refused: invalid input" in completed.stdout
    assert "non-fp1 endpoint refused: invalid input" in completed.stdout
    assert "foreign writer refused (one writer per stream): policy rejection" in completed.stdout
