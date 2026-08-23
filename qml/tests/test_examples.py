"""The tiny import example must stay executable (L27, tier-1 artifact)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_QML_ROOT = Path(__file__).resolve().parents[1]
_REPO = _QML_ROOT.parent
_EXAMPLE = _QML_ROOT / "examples" / "import_usage.py"


def test_import_usage_example_runs_clean() -> None:
    pythonpath = os.pathsep.join(
        [
            str(_QML_ROOT / "src"),
            str(_REPO / "packages" / "qmf-core" / "src"),
            str(_REPO / "packages" / "qmf-registry" / "src"),
            str(_REPO / "packages" / "qmf-risk" / "src"),
            str(_REPO / "packages" / "qmf-data" / "src"),
        ]
    )
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "import qml ok" in completed.stdout
