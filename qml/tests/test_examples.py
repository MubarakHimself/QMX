"""The tiny import example must stay executable (L27, tier-1 artifact)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_QML_ROOT = Path(__file__).resolve().parents[1]
_REPO = _QML_ROOT.parent
_PYTHONPATH = os.pathsep.join(
    [
        str(_QML_ROOT / "src"),
        str(_REPO / "packages" / "qmf-core" / "src"),
        str(_REPO / "packages" / "qmf-registry" / "src"),
        str(_REPO / "packages" / "qmf-risk" / "src"),
        str(_REPO / "packages" / "qmf-data" / "src"),
    ]
)


def _run_example(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_QML_ROOT / "examples" / name)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": _PYTHONPATH},
        check=False,
    )


def test_import_usage_example_runs_clean() -> None:
    completed = _run_example("import_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "import qml ok" in completed.stdout


def test_family_usage_example_runs_clean() -> None:
    completed = _run_example("family_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "family mint ok" in completed.stdout
    assert "two sandboxes deduplicate: True" in completed.stdout
    assert "unresolvable family at Layer 1: unavailable dependency" in completed.stdout
