"""The CT-01 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/exact_usage.py`` as a fresh process — the same subprocess idiom
the CT-03/CT-04 example tests use — and checks it exits clean and demonstrates the
float ban and boundary, mixed-scale promotion, delta-typed subtraction, the
value-factor conversion, and the equal-value/equal-fingerprint property.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "exact_usage.py"


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
    assert "exact money 1.50 stored as 150 at scale 2" in completed.stdout
    assert "float refused; boundary-converted to 150 at scale 2" in completed.stdout
    assert "mixed-scale sum promoted to 17500 at scale 4" in completed.stdout
    assert "price delta is a PriceDelta of 5 at scale 5" in completed.stdout
    assert "delta converted via value-factor to 1000 USD at scale 2" in completed.stdout
    assert "equal value equal fingerprint: True" in completed.stdout
