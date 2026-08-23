"""The Story 7.2 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/canonical_reference_usage.py`` as a fresh process — the same subprocess
idiom the other example tests use — and checks it exits clean and demonstrates the
import-time assertion, reference/package ownership, and registry conformance. The
pinned reference installs on this machine, so the assertion verifies; the assertions
below hold in both the verified and the unavailable-dependency branches.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "canonical_reference_usage.py"


def test_reference_usage_example_runs_clean() -> None:
    env = {**os.environ, "PYTHONPATH": str(_PKG_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "reference asserted at import:" in completed.stdout
    assert "sma ownership: reference (wraps SMA)" in completed.stdout
    assert "vwap ownership: package (package-canonical)" in completed.stdout
    assert "ownership registry conformant: True" in completed.stdout
