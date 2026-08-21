"""The CT-03 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/identity_usage.py`` as a fresh process — the same subprocess
idiom the CT-04 example test uses — and checks it exits clean and demonstrates
the identity, account-role, rename-as-new-record, and refusal paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "identity_usage.py"


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
    assert "distinct instruments: True" in completed.stdout
    assert "role=demo" in completed.stdout
    assert "history has 2 entries" in completed.stdout
    assert "missing venue refused: invalid input / venue" in completed.stdout
    assert "null field refused: invalid input / content" in completed.stdout
