"""The Story 7.6 wrapper-set example must stay executable (L27, tier-1 artifact).

Runs ``examples/configured_wrapper_set_usage.py`` as a fresh process — the same subprocess
idiom the other example tests use — and checks it exits clean and demonstrates the four
things the story pins down: the first wrapper set with warm-up at the reference lookback and
both modes, mechanically stated capability terms, the tier-2 equality law, and the FM-4
comparison suite catching an output-changing upgrade with a per-configured-indicator mint.

The example computes with the real canonical reference; when it is unavailable the example
cannot run, so the test skips rather than failing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from qmf.core import is_ok
from qmf.indicators import reference_status

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "configured_wrapper_set_usage.py"


def test_configured_wrapper_set_example_runs_clean() -> None:
    if not is_ok(reference_status()):
        pytest.skip("the pinned canonical reference is unavailable on this machine")
    env = {**os.environ, "PYTHONPATH": str(_PKG_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "wrapper set: ema mom roc rsi sma wma" in completed.stdout
    # Warm-up at the reference lookback and both modes declared.
    assert "sma: warm_up=2 lookback=2 both_modes=True" in completed.stdout
    assert "rsi: warm_up=3 lookback=3 both_modes=True" in completed.stdout
    assert "equality law (streaming == batch): True" in completed.stdout
    assert "upgrade with no output change: unchanged (mint=None)" in completed.stdout
    assert "upgrade that changes output: changed mint 1->2 protocol_unchanged=1" in completed.stdout
    assert "before/after evidence differ: True" in completed.stdout
