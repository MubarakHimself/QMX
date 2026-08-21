"""The CT-04 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/refusal_usage.py`` as a fresh process — the same subprocess idiom
the import-time benchmark uses — and checks it exits clean and demonstrates both
a success and a refusal path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "refusal_usage.py"


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
    assert "accepted 3 lots" in completed.stdout
    assert "refused (invalid input" in completed.stdout
