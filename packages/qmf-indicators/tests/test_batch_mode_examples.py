"""The Story 7.3 batch-mode example must stay executable (L27, tier-1 artifact).

Runs ``examples/batch_mode_usage.py`` as a fresh process — the same subprocess idiom the
other example tests use — and checks it exits clean and demonstrates the four batch-mode
laws: full-length index-aligned presence-mapped output, schedule vs missing vs warm-up,
as-of-only alignment with a forward-fill refusal, and governed-evidence admission.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "batch_mode_usage.py"


def test_batch_mode_example_runs_clean() -> None:
    env = {**os.environ, "PYTHONPATH": str(_PKG_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "batch output length: 8 (input length: 8)" in completed.stdout
    assert "position 6 (market-hours closed): absent_by_schedule" in completed.stdout
    assert "position 5 (calendar-open, no data): gap" in completed.stdout
    assert "position 0 (during warm-up): not_ready" in completed.stdout
    assert "forward-fill across the instant: policy rejection" in completed.stdout
    assert "governed evidence: admitted (confirmed)" in completed.stdout
