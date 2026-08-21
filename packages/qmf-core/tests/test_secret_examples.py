"""The secret-seam reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/secret_usage.py`` as a fresh process — the same subprocess idiom the
other example tests use — and checks it exits clean and demonstrates the render
guard, the reveal path, the missing-credential refusal, and store-before-discard
rotation, and that the secret is never printed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "secret_usage.py"


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
    assert "ref renders its id: secret-ref-ctrader-refresh-01" in completed.stdout
    assert "secret value hides its secret in repr/str/format: True" in completed.stdout
    assert "reveal is the only plaintext path: True" in completed.stdout
    assert "missing credential refused: unavailable dependency" in completed.stdout
    assert "rotation stored new value before discard: True" in completed.stdout
    # The plaintext secrets never reach stdout.
    assert "demo-session-material" not in completed.stdout
