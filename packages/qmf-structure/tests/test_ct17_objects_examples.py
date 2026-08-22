"""The CT-17 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/structure_usage.py`` as a fresh process — the same subprocess idiom the
qmf-core and qmf-registry example tests use — and checks it exits clean and demonstrates
the object mint, the derived fingerprint, cross-sandbox dedup, immutability, the
emission-invariant refusals, the append-only lifecycle read-time fold, and the refit that
mints a new artifact instead of overwriting.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "structure_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    # The example imports qmf.core and qmf.structure; put both on the path (the package
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
    assert "minted at observation, derived fp1: fp1:sha256:" in completed.stdout
    assert "two sandboxes deduplicate: True" in completed.stdout
    assert "object immutable and unstamped" in completed.stdout
    assert "anchor end after observed-at refused: invalid input" in completed.stdout
    assert "observed-at behind consumed input refused: invalid input" in completed.stdout
    assert "still valid is a read-time fold (before=True, after=False)" in completed.stdout
    assert "confirmation record references object by fp1: fp1:sha256:" in completed.stdout
    assert "refit mints a new artifact, prior untouched: True" in completed.stdout
    assert "confirmed read refuses an unconfirmed row: policy rejection" in completed.stdout
    assert "equality is consumption (True), causality refuses equal (True)" in completed.stdout
    assert "revised input yields a different result label: True" in completed.stdout
    assert "citation makes object governed evidence: True" in completed.stdout
    assert "split embargo refuses a straddling record: policy rejection" in completed.stdout
