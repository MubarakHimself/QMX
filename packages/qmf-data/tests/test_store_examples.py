"""The store reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/store_usage.py`` as a fresh process and checks it exits clean and
demonstrates the four boundaries, idempotency, the world policy, one-writer, and the
backup input.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "store_usage.py"
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
    assert "four boundaries over four engines: parquet, duckdb, jsonl, sqlite" in completed.stdout
    assert "byte-identical re-write is: idempotent" in completed.stdout
    assert "simulated store and cross-world read: both policy rejection" in completed.stdout
    assert "second writer on a held stream: policy rejection" in completed.stdout
    assert "backup input read raw-archive records verbatim: 3" in completed.stdout
