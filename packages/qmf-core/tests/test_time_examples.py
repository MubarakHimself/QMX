"""The CT-02 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/time_usage.py`` as a fresh process — the same subprocess idiom the
CT-01/CT-03/CT-04 example tests use — and checks it exits clean and demonstrates
exact instants with checked arithmetic, the calendar-scoped trading date, causality
on instants only, the injected clock with its type-separated monotonic readings,
and the strictly-increasing per-writer ordering sequence.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "time_usage.py"


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
    assert (
        "instant 0 renders (display-only, UTC) as 1970-01-01T00:00:00.000000000Z"
        in completed.stdout
    )
    assert "trading date 2026-08-21 is scoped to forex-17NY" in completed.stdout
    assert "causality compares instants only" in completed.stdout
    assert "monotonic elapsed = 32 ns" in completed.stdout
    assert "strictly-increasing sequence; next is 2" in completed.stdout
