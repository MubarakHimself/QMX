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


def test_synthetic_spread_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "synthetic_spread_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "trade-only bars use instrument x hour-UTC x session calibration" in completed.stdout
    assert "equal buy/sell refused" in completed.stdout
    assert "missing calibration is typed refusal, never zero spread" in completed.stdout
    assert "real quotes take precedence" in completed.stdout
    assert "quote-real ranks higher; ordinal taxonomy is not invented here" in completed.stdout
    assert "non-live SQS door consumes modeled-spread series of exact Prices" in completed.stdout
    assert "CT-32 label declares the spread calibration fingerprint" in completed.stdout
    assert "synthetic spread ok" in completed.stdout


def test_fill_pipeline_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "fill_pipeline_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "dispatched per order type" in completed.stdout
    assert "Fill | NoFill | PartialFill" in completed.stdout
    assert "worst-case default" in completed.stdout
    assert "optimistic-exact fill-basis" in completed.stdout
    assert "optimistic taint" in completed.stdout
    assert "all-or-none any-leg-fail is NoFill" in completed.stdout
    assert "partial capped by position and lot step" in completed.stdout
    assert "each partial has its own fee reference" in completed.stdout
    assert "typed NoFill reasons" in completed.stdout
    assert "gap fill at gapped price" in completed.stdout
    assert "deterministic path-split sequencing" in completed.stdout
    assert "new intents rest for a later slice" in completed.stdout
    assert "wired into run-loop sub-phase 3" in completed.stdout
    assert "slippage maps pre-slip to post-slip or vetoes" in completed.stdout
    assert "passive limits skip slippage unless configured" in completed.stdout
    assert "fill pipeline ok" in completed.stdout


def test_cost_port_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "cost_port_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "exact-integer Money in its own currency" in completed.stdout
    assert "no float on the money path" in completed.stdout
    assert "each partial has its own pro-rated commission" in completed.stdout
    assert "commission is a distinct line item" in completed.stdout
    assert (
        "zero | percent-of-notional | per-lot/per-1k-units | "
        "notional-proportional-with-per-order-minimum"
    ) in completed.stdout
    assert "admission query matches fill-time charge" in completed.stdout
    assert "missing calibration is typed refusal, never silent zero" in completed.stdout
    assert "cost port ok" in completed.stdout


def test_financing_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "financing_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "financing is a scheduled cash event, not an order fill" in completed.stdout
    assert "applied at the broker calendar rollover, not per slice" in completed.stdout
    assert "triple-swap weekday and multiplier come from the artifact" in completed.stdout
    assert "weekend/holiday handling comes from the artifact" in completed.stdout
    assert "missing calibration is typed refusal, never silent zero" in completed.stdout
    assert "distinct CT-13 journal event, not a fill" in completed.stdout
    assert "cost drag decomposes fill P&L / slippage / commission / financing" in completed.stdout
    assert "CT-32 label declares the financing calibration fingerprint" in completed.stdout
    assert "optimistic taint; no edge claim until GAP-0048" in completed.stdout
    assert "financing ok" in completed.stdout


def test_execution_composition_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "execution_composition_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "bound from resolved run-config" in completed.stdout
    assert "fill -> slippage -> cost" in completed.stdout
    assert "never a bot-sized order" in completed.stdout
    assert "full-loss price required before open" in completed.stdout
    assert "risk-reducing exit admitted without new full-loss" in completed.stdout
    assert "fidelity identity is adapter-id + composition-version + taint" in completed.stdout
    assert "optimistic taint" in completed.stdout
    assert "lowest fidelity of bound adapters" in completed.stdout
    assert "mixed-fidelity Book-bar comparison refused" in completed.stdout
    assert "world=simulated refused" in completed.stdout
    assert "replay-on-synthetic is invalid input" in completed.stdout
    assert "execution composition ok" in completed.stdout


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


def test_measure_set_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "measure_set_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (
        "ordered V1 core measure set; every computed quantity has a non-null AD-40 unit-kind"
        in (completed.stdout)
    )
    assert (
        "money measures are exact scaled integers; durations are int64 UTC-ns" in completed.stdout
    )
    assert "null unit-kind is invalid input, never defaulted" in completed.stdout
    assert "profit factor with no losers is typed undefined, never a magic cap of 10" in (
        completed.stdout
    )
    assert "Sharpe with <2 daily samples is insufficient-sample, never NaN coerced to 0" in (
        completed.stdout
    )
    assert (
        "no composite score/grade/tier; producing the set sizes, promotes, and benches nothing"
        in (completed.stdout)
    )
    assert "V1 core measure set ok" in completed.stdout


def test_downstream_reads_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "downstream_reads_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "HTML/markdown are token substitution of the stored CT-32; no new number" in (
        completed.stdout
    )
    assert "headline shows world and account-binding role verbatim and unmissably" in (
        completed.stdout
    )
    assert "interpretation skills read CT-32 and never parse HTML" in completed.stdout
    assert "re-execute stored run id reproduces the CT-32 fingerprint or typed refusal" in (
        completed.stdout
    )
    assert "concurrent runs write isolated output directories; no shared render state" in (
        completed.stdout
    )
    assert "rendering, interpretation, and reproduction are publish-only" in completed.stdout
    assert "pure downstream reads ok" in completed.stdout


def test_chart_series_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "chart_series_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "each chart is {name, unit_kind, points:[{t, v}]}; t is int64 UTC-ns" in completed.stdout
    assert "no image, base64, PNG, color, style, or histogram bin in the data" in completed.stdout
    assert "single-instrument unleveraged run omits holdings rather than faking them" in (
        completed.stdout
    )
    assert "benchmark-relative series omitted with 'no benchmark declared'" in completed.stdout
    assert (
        "multi-instrument run reconstructs holdings/exposure/allocation from the position stream"
        in (completed.stdout)
    )
    assert "display downsample is a derivative with declared sampler identity; AD-10-excluded" in (
        completed.stdout
    )
    assert "PNG/base64 is refused as canonical payload" in completed.stdout
    assert "chart series as data ok" in completed.stdout


def test_accounting_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "accounting_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "quiet run keeps explicit zero counts; keys are never omitted" in completed.stdout
    assert "tallies fold CT-13 journals; count unit-kind; distinct from measure_set" in (
        completed.stdout
    )
    assert "unresolvable authority is typed refusal; parallel log is refused" in completed.stdout
    assert "suppression and veto accounting ok" in completed.stdout


def test_ct32_artifact_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "ct32_artifact_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "exactly one CT-32 container written; fp1 label-derived via qmf-core" in completed.stdout
    assert "AD-12 label plus registry_as_of, data/split, fidelity, RNG stamps" in completed.stdout
    assert "world=replay from data-derived provenance; optimistic taint; no edge claim" in (
        completed.stdout
    )
    assert "multi-role span is policy rejection; writes nothing" in completed.stdout
    assert "no second report JSON" in completed.stdout
    assert "canonical CT-32 artifact ok" in completed.stdout


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


def test_sweep_axes_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "sweep_axes_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Cartesian product: 24 isolated run specs, declaration order" in completed.stdout
    assert "pure inspection, spawns no process" in completed.stdout
    assert "1x1x1 sweep" in completed.stdout
    assert "never a silent zero-combo batch" in completed.stdout
    assert "a binary float never enters identity" in completed.stdout
    assert "thin wrapper over one pure library expansion function" in completed.stdout
    assert "sweep axes ok" in completed.stdout


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


def test_governor_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "governor_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "min(cpu budget, memory budget)" in completed.stdout
    assert "enqueue-on-full" in completed.stdout
    assert "typed refusal when projected peak exceeds the declared budget" in completed.stdout
    assert "finish then admit next" in completed.stdout
    assert (
        "12-14 concurrent is a motivating reference, never a validated budget" in completed.stdout
    )
    assert "governor ok" in completed.stdout


def test_orchestrator_log_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "orchestrator_log_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "orchestrator owns the injected log sink" in completed.stdout
    assert "AD-14 operational logs only, never evidence" in completed.stdout
    assert "correlation_id excluded from fp1 identity" in completed.stdout
    assert "crashed run leaves a partial log in its own room" in completed.stdout
    assert "never corrupts sibling or the ledger" in completed.stdout
    assert "orchestrator log ok" in completed.stdout


def test_orchestrator_ledger_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "orchestrator_ledger_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "one ledger line per run" in completed.stdout
    assert "completed run appends one confirmation line" in completed.stdout
    assert "aborted line carries refusal context" in completed.stdout
    assert "direct library run() produces no governed evidence" in completed.stdout
    assert "WriterId-scoped fragments" in completed.stdout
    assert "orchestrator ledger ok" in completed.stdout


def test_orchestrator_abort_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "orchestrator_abort_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "declared per-run limits qmb_run_time_limit and qmb_run_memory_limit" in completed.stdout
    assert "every submitted run carries a cancel token and declared limits" in completed.stdout
    assert "limit breach or cancel is typed aborted with context" in completed.stdout
    assert "aborting one process does not touch siblings" in completed.stdout
    assert "no partial governed result" in completed.stdout
    assert "orchestrator abort ok" in completed.stdout


def test_orchestrator_spawn_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "orchestrator_spawn_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "process-per-run via stdlib subprocess" in completed.stdout
    assert "isolated output directory named by the run id" in completed.stdout
    assert "no Ray, no required Docker, no daemon" in completed.stdout
    assert "one-writer-per-stream" in completed.stdout
    assert "run is pure" in completed.stdout
    assert "process-per-run ok" in completed.stdout


def test_data_download_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "data_download_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "provider port:" in completed.stdout
    assert "AD-22 conversion" in completed.stdout
    assert "download-once CT-10" in completed.stdout
    assert "idempotent re-run" in completed.stdout
    assert "overwrite revision=" in completed.stdout
    assert "run provider fetch is policy rejection" in completed.stdout
    assert "qmb data download ok" in completed.stdout


def test_data_licensing_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "data_licensing_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "licensing gate:" in completed.stdout
    assert "governed-evidence admitted:" in completed.stdout
    assert "CT-07 lineage:" in completed.stdout
    assert "unlicensed governed-evidence refused:" in completed.stdout
    assert "non-evidence use allowed" in completed.stdout
    assert "zero corpus bytes" in completed.stdout
    assert "qmb data licensing gate ok" in completed.stdout


def test_data_catalog_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "data_catalog_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "catalog identity:" in completed.stdout
    assert "list both: bid=present ask=not present" in completed.stdout
    assert "absent window: status=not present" in completed.stdout
    assert "catalog aliases list:" in completed.stdout
    assert "CLI and Python API share coverage:" in completed.stdout
    assert "data catalog ok" in completed.stdout


def test_data_verify_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "data_verify_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "verify identity:" in completed.stdout
    assert "pass counts=" in completed.stdout
    assert "armed edge refusal" in completed.stdout
    assert "float taint refused" in completed.stdout
    assert "CT-13 data-quality events=" in completed.stdout
    assert "determinism: same window + config" in completed.stdout
    assert "qmb data verify ok" in completed.stdout


def test_data_gap_check_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "data_gap_check_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "gap-check identity:" in completed.stdout
    assert "open-session gaps=" in completed.stdout
    assert "weekend closure:" in completed.stdout
    assert "always-open gaps=" in completed.stdout
    assert "determinism: same window + calendar version" in completed.stdout
    assert "interior fill refused" in completed.stdout
    assert "unresolvable calendar refused" in completed.stdout
    assert "qmb data gap-check ok" in completed.stdout


def test_cli_refusal_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "cli_refusal_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "library RETURNED the refusal; door rendered stderr JSON" in completed.stdout
    assert "nonzero exit + category/context/retryability" in completed.stdout
    assert "successful run exits zero" in completed.stdout
    assert "programmer error surfaces as an exception, not stderr JSON" in completed.stdout
    assert "typed refusal was not raised" in completed.stdout
    assert "qmb CLI refusal rendering ok" in completed.stdout


def test_api_door_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "api_door_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "importable from uv-added qmb as qmb.doors.api" in completed.stdout
    assert "thin re-export: api.run is qmb.run" in completed.stdout
    assert "refusal returned verbatim, not raised" in completed.stdout
    assert "UI backend consumes this in-process; never HTTP" in completed.stdout
    assert "direct library run() produces no governed evidence" in completed.stdout
    assert "qmb Python API door ok" in completed.stdout


def test_mcp_door_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "mcp_door_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "sibling wrapper over the same library; post-CLI-v1, not shipped" in completed.stdout
    assert "invocation is typed unsupported-capability refusal" in completed.stdout
    assert "localhost-bound by default; never stacked over HTTP" in completed.stdout
    assert "error.data carries the refusal union verbatim" in completed.stdout
    assert "CLI v1 ships first; MCP does not gate it" in completed.stdout
    assert "qmb MCP door scaffold ok" in completed.stdout


def test_door_parity_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "door_parity_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "CLI and Python API share the catalog:" in completed.stdout
    assert "shipped doors: cli, api; MCP not in the door-set" in completed.stdout
    assert "a capability on one door missing from the other fails" in completed.stdout
    assert "CLI: nonzero exit + stderr JSON" in completed.stdout
    assert "Python: refusal union verbatim" in completed.stdout
    assert "qmb door parity ok" in completed.stdout


def test_cli_autocomplete_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "cli_autocomplete_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "autocomplete enumerates through the one registry-read port" in completed.stdout
    assert "same answers as resolve:" in completed.stdout
    assert "new Book arrives as a fresher as-of set" in completed.stdout
    assert "never a door cache refresh" in completed.stdout
    assert "click native shell_complete" in completed.stdout
    assert "missing port yields no candidates, not a live query" in completed.stdout
    assert "qmb CLI registry autocomplete ok" in completed.stdout


def test_cli_tree_usage_example_runs_clean() -> None:
    completed = subprocess.run(
        [sys.executable, str(_QMB_ROOT / "examples" / "cli_tree_usage.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": pythonpath()},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "command tree groups:" in completed.stdout
    assert "absent resources return typed refusal" in completed.stdout
    assert "compiled via compile_run_config; submitted to qmb.orchestrator" in completed.stdout
    assert "run-id is the compiler fingerprint; door computed none" in completed.stdout
    assert "qmb CLI command tree ok" in completed.stdout


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
