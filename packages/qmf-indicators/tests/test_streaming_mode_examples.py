"""The Story 7.4 streaming-mode example must stay executable (L27, tier-1 artifact).

Runs ``examples/streaming_mode_usage.py`` as a fresh process — the same subprocess idiom
the other example tests use — and checks it exits clean and demonstrates the four things
Story 7.4 pins down: the one named stateful class with its sequence-numbered outputs and
health, the tier-2 equality law, restore-equivalence with the snapshot fingerprint carried
as an input fingerprint, and the cross-tuple restore refusal.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "streaming_mode_usage.py"


def test_streaming_mode_example_runs_clean() -> None:
    env = {**os.environ, "PYTHONPATH": str(_PKG_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "update seq=0:" in completed.stdout
    assert "tier-2 equality law (streaming == batch, 0 ULP): True" in completed.stdout
    assert "restore-equivalence (values equal): True" in completed.stdout
    assert "restored result carries snapshot fingerprint as input: True" in completed.stdout
    assert "cross-tuple restore: unavailable dependency" in completed.stdout
