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


def test_completed_boundary_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "completed_boundary_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "higher BarSpec derived from finest base" in completed.stdout
    assert "forming bar not visible" in completed.stdout
    assert "same-slice bars and fills share one series" in completed.stdout
    assert "regardless of GAP-0048" in completed.stdout
    assert "completed-boundary derivation ok" in completed.stdout


def test_execution_ports_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "execution_ports_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "fill, slippage, and cost are separate Protocol seams" in completed.stdout
    assert "never a bot-sized order" in completed.stdout
    assert "full-loss price required before open" in completed.stdout
    assert "partial fill is first-class" in completed.stdout
    assert "optimistic taint on every fill" in completed.stdout
    assert "one CT-29 exit per virtual close" in completed.stdout
    assert "bot-proposed exits are risk-monotonic" in completed.stdout
    assert "world=simulated policy rejection" in completed.stdout
    assert "execution ports ok" in completed.stdout


def test_golden_slice_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "golden_slice_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "two identical runs share one CT-32 fingerprint" in completed.stdout
    assert "re-run under resolved config reproduces; mismatch is typed refusal" in completed.stdout
    assert "concurrency is scheduling only" in completed.stdout
    assert "no HTML/charts in the fingerprint" in completed.stdout
    assert "golden-slice determinism ok" in completed.stdout


def test_cancel_observe_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "cancel_observe_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "cooperative cancel at a slice boundary" in completed.stdout
    assert "progress data-points-processed and is_warming_up while running" in completed.stdout
    assert "time/memory limit breach is typed aborted, not a hang" in completed.stdout
    assert "no partial governed result" in completed.stdout
    assert "cancel and observe ok" in completed.stdout


def test_warmup_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "warmup_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "same event-slice loop during warm-up; trading locked" in completed.stdout
    assert "acting during warm-up is policy rejection" in completed.stdout
    assert "never a Duration" in completed.stdout
    assert "pre-seeding buffers is not warm-up" in completed.stdout
    assert "evidence range is the trading interval only" in completed.stdout
    assert "in-loop warm-up ok" in completed.stdout


def test_event_slice_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "event_slice_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "pinned sub-phase order is identity-bearing" in completed.stdout
    assert "never fill against this slice's path" in completed.stdout
    assert "forming bar skipped" in completed.stdout
    assert "run is pure" in completed.stdout
    assert "event-slice loop ok" in completed.stdout


def test_frontier_clock_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "frontier_clock_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "injected Clock read via read_frontier" in completed.stdout
    assert "min next-emit pull" in completed.stdout
    assert "rewind refused" in completed.stdout
    assert "GAP-0048" in completed.stdout
    assert "frontier clock ok" in completed.stdout
    assert "does not choose world" in completed.stdout


def pythonpath() -> str:
    return os.pathsep.join(
        [
            str(_QMB_ROOT / "src"),
            str(_REPO / "qml" / "src"),
            str(_REPO / "packages" / "qmf-core" / "src"),
            str(_REPO / "packages" / "qmf-registry" / "src"),
            str(_REPO / "packages" / "qmf-data" / "src"),
            str(_REPO / "packages" / "qmf-indicators" / "src"),
            str(_REPO / "packages" / "qmf-structure" / "src"),
            str(_REPO / "packages" / "qmf-risk" / "src"),
        ]
    )


def test_ql7_host_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "ql7_host_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "factory constructed via construct_bot / FunctionFactory / HostedBot" in completed.stdout
    assert "declared-footprint evidence only" in completed.stdout
    assert "assignment_is_canonical True" in completed.stdout
    assert "producer template resolved to one configured-producer fingerprint" in completed.stdout
    assert "run-spec override" in completed.stdout
    assert "passed through unchanged" in completed.stdout
    assert "needs no QL-7 adapter" in completed.stdout
    assert "ql7 host ok" in completed.stdout


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
