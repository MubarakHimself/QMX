"""The sinks reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/sinks_usage.py`` as a fresh process and checks it exits clean and
demonstrates a successful write, protocol conformance, and the block-on-unpersistable
rule (AR-47).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "sinks_usage.py"


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
    assert "observation persisted: True" in completed.stdout
    assert "record persisted: True" in completed.stdout
    assert "journal blocked after 2 events on unpersistable: True" in completed.stdout
    assert "block refusal category: storage failure" in completed.stdout
    assert "block retryable after: free space in the journal store" in completed.stdout
