"""The CT-05 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/fingerprint_usage.py`` as a fresh process — the same subprocess
idiom the other example tests use — and checks it exits clean and demonstrates the
serializer, fingerprint, result-label, world-policy, and idempotent/collision paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "fingerprint_usage.py"


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
    assert "equal value, equal fingerprint: fp1:sha256:" in completed.stdout
    assert "serializer is key-order independent:" in completed.stdout
    assert "float refused in identity: invalid input" in completed.stdout
    assert "null refused in identity: invalid input" in completed.stdout
    assert "label identity dedups across occurrences: True" in completed.stdout
    assert "simulated into evidence refused: policy rejection" in completed.stdout
    assert "true collision refused and alarmed: policy rejection" in completed.stdout
    assert "stays out of identity" in completed.stdout
