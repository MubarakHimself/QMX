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


def test_logic_usage_example_runs_clean() -> None:
    completed = _run_example("logic_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "logic identity ok" in completed.stdout
    assert "two sandboxes one Bot fp1: True" in completed.stdout
    assert "one-character change mints new Bot fp1: True" in completed.stdout
    assert "unresolvable logic at Layer 1: unavailable dependency" in completed.stdout


def test_footprint_usage_example_runs_clean() -> None:
    completed = _run_example("footprint_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "footprint authoring ok" in completed.stdout
    assert "omitted AD-22 field at Layer 1: invalid input" in completed.stdout
    assert "transitive-union complete: True" in completed.stdout
    assert "derived warm-up observations: 20" in completed.stdout


def test_confluence_usage_example_runs_clean() -> None:
    completed = _run_example("confluence_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "confluence authoring ok" in completed.stdout
    assert "two sandboxes reuse one confluence: True" in completed.stdout
    assert "unresolvable producer at Layer 1: unavailable dependency" in completed.stdout
    assert "order-significance changes fingerprint: True" in completed.stdout


def test_protocol_usage_example_runs_clean() -> None:
    completed = _run_example("protocol_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "protocol format version: 1" in completed.stdout
    assert "ladder is qml-ad5, not CT-numbered: True" in completed.stdout
    assert "factory constructed: True" in completed.stdout
    assert "zero intents on empty evidence: True" in completed.stdout
    assert "advisory stop is advisory: True" in completed.stdout
    assert "inbound requested_r is invalid input" in completed.stdout
    assert "venue command rejected: unsupported capability" in completed.stdout
    assert "replay identical intents: True" in completed.stdout
    assert "protocol usage ok" in completed.stdout


def test_bot_definition_usage_example_runs_clean() -> None:
    completed = _run_example("bot_definition_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "bot definition authoring ok" in completed.stdout
    assert "identity excludes AD-16 header: True" in completed.stdout
    assert "canonical assignment is derived: True" in completed.stdout
    assert "zero family ids is invalid input: invalid input" in completed.stdout
    assert "entry-only bot is legal: True" in completed.stdout
    assert "two sandboxes one Bot fp1: True" in completed.stdout
    assert "changed default mints new Bot: True" in completed.stdout
