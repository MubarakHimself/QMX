"""The qmf-venue reference-usage examples must stay executable (L27, AR-21)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"
_PYTHONPATH = os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)])


def _run_example(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_PKG_ROOT / "examples" / name)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": _PYTHONPATH},
        check=False,
    )


def test_account_binding_usage_example_runs_clean() -> None:
    completed = _run_example("account_binding_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "encoding secret reference refused: invalid input" in completed.stdout
    assert "rotation never forks identity: True" in completed.stdout
    assert "cross-venue account refused: invalid input" in completed.stdout
    assert "account binding usage ok" in completed.stdout


def test_observation_events_usage_example_runs_clean() -> None:
    completed = _run_example("observation_events_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "observation kinds mapped one-to-one: 6" in completed.stdout
    assert "malformed kind refused: invalid input" in completed.stdout
    assert "submission outcomes: 4; risk-reducing kinds: 4" in completed.stdout
    assert "observation events usage ok" in completed.stdout
