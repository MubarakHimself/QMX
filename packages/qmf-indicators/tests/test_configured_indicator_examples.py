"""The CT-16 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/configured_indicator_usage.py`` as a fresh process — the same
subprocess idiom the other example tests use — and checks it exits clean and
demonstrates the fp1-spans-the-configuration, one-change-forks-identity, and
binary-float-parameter-refused paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "configured_indicator_usage.py"


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
    assert "fp1 spans the whole configuration: fp1:sha256:" in completed.stdout
    assert "one parameter change forks identity: True" in completed.stdout
    assert "binary float parameter refused: invalid input" in completed.stdout
