"""The tiny import example must stay executable (L27, tier-1 artifact)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_QMB_ROOT = Path(__file__).resolve().parents[1]
_REPO = _QMB_ROOT.parent
_EXAMPLE = _QMB_ROOT / "examples" / "import_usage.py"


def test_replay_binding_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "replay_binding_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "replay binding ok" in completed.stdout
    assert "world=replay binding" in completed.stdout
    assert "seed_overridden" in completed.stdout
    assert "incomparable" in completed.stdout
    assert "full-loss price" in completed.stdout
    assert "CT-29" in completed.stdout


def test_run_config_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "run_config_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "resolved run-config ok" in completed.stdout
    assert "byte-identical" in completed.stdout
    assert "never name@version" in completed.stdout
    assert "invalid input" in completed.stdout
    assert "BMS outranks Book" in completed.stdout


def test_config_fragments_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "config_fragments_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "config fragments ok" in completed.stdout
    assert "DISJOINT" in completed.stdout
    assert "not a registry kind" in completed.stdout
    assert "stress-spread is a config fragment" in completed.stdout
    assert "stays readable" in completed.stdout


def test_registryread_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "registryread_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "registry-read port ok" in completed.stdout
    assert "name@version refused: invalid input" in completed.stdout
    assert "stale evidence" in completed.stdout
    assert "name@latest refused" in completed.stdout


def pythonpath() -> str:
    return os.pathsep.join(
        [
            str(_QMB_ROOT / "src"),
            str(_REPO / "packages" / "qmf-core" / "src"),
            str(_REPO / "packages" / "qmf-registry" / "src"),
            str(_REPO / "packages" / "qmf-data" / "src"),
            str(_REPO / "packages" / "qmf-indicators" / "src"),
            str(_REPO / "packages" / "qmf-structure" / "src"),
            str(_REPO / "packages" / "qmf-risk" / "src"),
        ]
    )


def test_import_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "import qmb ok" in completed.stdout
    assert "qmb 0.1.0" in completed.stdout
