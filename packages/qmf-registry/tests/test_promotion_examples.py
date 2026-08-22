"""The Story 2.3 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/promotion_usage.py`` as a fresh process — the same subprocess idiom the
CT-06/CT-07 example tests use — and checks it exits clean and demonstrates the signed card
with a derived id, the no-card refusal law, the summary correction that mints a new card,
the AD-32 template binding, and the CT-13 promotion event emitted through a JournalSink.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "promotion_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    # The example imports qmf.core and qmf.registry; put both on the path (the package
    # imports only qmf.core, but the example is executed as a standalone process).
    pythonpath = os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)])
    env = {**os.environ, "PYTHONPATH": pythonpath}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "signed card, derived id: fp1:sha256:" in completed.stdout
    assert "no card present, promotion refused: policy rejection" in completed.stdout
    assert "card attesting another record refused: policy rejection" in completed.stdout
    assert "summary correction mints a new card: True" in completed.stdout
    assert "risk-admission card binds the template fingerprint: True" in completed.stdout
    assert "promotion event is only a pointer to the card: fp1:sha256:" in completed.stdout
    assert "promotion event emitted through the JournalSink: 1" in completed.stdout
