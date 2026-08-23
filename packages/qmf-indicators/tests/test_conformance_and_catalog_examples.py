"""The Story 7.5 conformance/benchmark/catalog example must stay executable (L27, tier-1 artifact).

Runs ``examples/conformance_and_catalog_usage.py`` as a fresh process — the same subprocess
idiom the other example tests use — and checks it exits clean and demonstrates the four things
Story 7.5 pins down: the conformance register's concept-walk expressibility, the two-rung
benchmark gate refusing a peak-memory regression, the heavy-by-default budget with its
unsupported synchronous entry and a proven light claim, and explicit catalog registration of a
graduated extension carrying its lineage edge and mandatory identity fields.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "conformance_and_catalog_usage.py"


def test_conformance_and_catalog_example_runs_clean() -> None:
    env = {**os.environ, "PYTHONPATH": str(_PKG_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "conformance concepts checked: 2" in completed.stdout
    assert "conformance all expressible: True" in completed.stdout
    assert "benchmark within budget: True" in completed.stdout
    assert "peak-memory regression refused: True" in completed.stdout
    assert "heavy by default: True" in completed.stdout
    assert "heavy synchronous entry: a heavy configuration" in completed.stdout
    assert "proven light claim: True" in completed.stdout
    assert "graduated lineage: research://experiment-42" in completed.stdout
    assert "artifact carries extension distribution: qmf-ind-ext-zigzag" in completed.stdout
    assert "artifact identity mandatory-check: True" in completed.stdout
