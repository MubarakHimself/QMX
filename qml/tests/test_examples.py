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


def test_state_usage_example_runs_clean() -> None:
    completed = _run_example("state_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "snapshot format version: 1" in completed.stdout
    assert "identical-tuple round-trip equivalent: True" in completed.stdout
    assert "restored-state fingerprint enters labels: True" in completed.stdout
    assert "cross-OS restore: unavailable dependency" in completed.stdout
    assert "cross-logic restore: unavailable dependency" in completed.stdout
    assert "cross-protocol restore: unavailable dependency" in completed.stdout
    assert "cross-arithmetic-reference restore: unavailable dependency" in completed.stdout
    assert "exceeded state bound: policy rejection" in completed.stdout
    assert "state usage ok" in completed.stdout


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


def test_sandbox_usage_example_runs_clean() -> None:
    completed = _run_example("sandbox_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert (
        "v1 mechanisms: static_ast_import_scan,capability_starvation,host_process_isolation"
        in completed.stdout
    )
    assert "windows_restricted_tokens,windows_job_objects,linux_seccomp" in completed.stdout
    assert "out of scope: dynamically_evasive_malicious_bot" in completed.stdout
    assert "v1 scope is honest: True" in completed.stdout
    assert "isolated run matches in-process: True" in completed.stdout
    assert "two hosts identical verdict: True" in completed.stdout
    assert "clock import before spawn: clock" in completed.stdout
    assert "filesystem open before spawn: io" in completed.stdout
    assert "network import before spawn: network" in completed.stdout
    assert "sandbox runner ok" in completed.stdout


def test_layer2_usage_example_runs_clean() -> None:
    completed = _run_example("layer2_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "layer 2 format version: 1" in completed.stdout
    assert "denial set: clock,io,network,undeclared_randomness" in completed.stdout
    assert "golden slice is identity-bearing: True" in completed.stdout
    assert "logic loads in isolation: True" in completed.stdout
    assert "two hosts identical verdict: True" in completed.stdout
    assert "no Book present: True" in completed.stdout
    assert "differing intents is layer-2 failure: policy rejection" in completed.stdout
    assert "non-permitted kind is layer-2 failure: policy rejection" in completed.stdout
    assert "clock import is layer-2 failure: policy rejection" in completed.stdout
    assert "layer2 conformance ok" in completed.stdout


def test_prediction_usage_example_runs_clean() -> None:
    completed = _run_example("prediction_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert (
        "prediction checks: footprint_satisfies_requirements,exit_intent_subset,"
        "family_resolves_exit_policy,stream_set_within_venue_capabilities" in completed.stdout
    )
    assert "threshold gaps: GAP-0048,GAP-0049" in completed.stdout
    assert "entry-only vs zero-exit Book: True" in completed.stdout
    assert "unresolved family: policy rejection" in completed.stdout
    assert "stream set exceeds venue: unsupported capability" in completed.stdout
    assert "blank passes registration: True" in completed.stdout
    assert "blank blocks live: policy rejection" in completed.stdout
    assert "ruled footprint miss: policy rejection" in completed.stdout
    assert "prediction linter ok" in completed.stdout


def test_layer1_usage_example_runs_clean() -> None:
    completed = _run_example("layer1_usage.py")
    assert completed.returncode == 0, completed.stderr
    assert "layer 1 format version: 1" in completed.stdout
    assert "clean declaration passes: True" in completed.stdout
    assert "missing unit-kind: invalid input" in completed.stdout
    assert "unresolvable family: unavailable dependency" in completed.stdout
    assert "unresolvable confluence: unavailable dependency" in completed.stdout
    assert "unresolvable logic: unavailable dependency" in completed.stdout
    assert "unresolvable producer formula: unavailable dependency" in completed.stdout
    assert "missing confluence-leg producer: invalid input" in completed.stdout
    assert "omitted AD-22 field: invalid input" in completed.stdout
    assert "exit kind outside vocabulary: invalid input" in completed.stdout
    assert "unknown contract format version: unsupported capability" in completed.stdout
    assert "layer 1 failures journaled: True" in completed.stdout
    assert "layer1 linter ok" in completed.stdout
