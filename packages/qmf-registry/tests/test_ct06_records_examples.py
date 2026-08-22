"""The CT-06 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/records_usage.py`` as a fresh process — the same subprocess idiom the
qmf-core example tests use — and checks it exits clean and demonstrates the per-kind
record, the derived id, cross-sandbox dedup, the parent-ref rules, the
idempotent/collision paths, and the FM-1 refusals.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "records_usage.py"
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
    assert "per-kind record, derived id: fp1:sha256:" in completed.stdout
    assert "two sandboxes deduplicate: True" in completed.stdout
    assert "order-insensitive, identity-bearing, header-only" in completed.stdout
    assert "true collision refused and alarmed: policy rejection" in completed.stdout
    assert "unknown kind refused: invalid input" in completed.stdout
    assert "reserved kind honored (refused): invalid input" in completed.stdout
    assert "undefined body field refused: invalid input" in completed.stdout
