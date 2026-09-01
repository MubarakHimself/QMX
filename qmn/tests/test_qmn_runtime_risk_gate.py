"""Story 26.14 / D010 — complete runtime risk gate through the composition root."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar, cast

from qmf.core import RefusalCategory, VenueId, World
from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.host import (
    MANUAL_OBSERVATION_IS_PROOF,
    PAPER_PROFIT_IS_PROOF,
    REQUIRED_RISK_CONTRACTS,
    RUNTIME_RISK_GATE_SURFACE,
    RUNTIME_RISK_SCENARIOS,
    RuntimeRiskGateInputs,
    evaluate_runtime_risk_coverage,
    qmn_production_src_root,
    refuse_manual_observation_as_proof,
    refuse_paper_profit_as_proof,
    run_runtime_risk_gate,
)
from qmn.time import VpsClock
from qmn.venue import ConformanceDouble, VenueClientKind

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _clock() -> VpsClock:
    return _ok(
        VpsClock.try_create(
            boot_epoch_id="boot-d010",
            wall_ns=lambda: _NS,
            monotonic_ns=lambda: _NS,
        )
    )


def _venue() -> ConformanceDouble:
    venue_id = _ok(VenueId.try_create("ctrader"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, venue_id))
    assert double.kind is VenueClientKind.CONFORMANCE
    return double


def _inputs(**overrides: object) -> RuntimeRiskGateInputs:
    kwargs: dict[str, object] = {"clock": _clock(), "venue": _venue()}
    kwargs.update(overrides)
    return RuntimeRiskGateInputs(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_and_closed_contract_roster() -> None:
    assert RUNTIME_RISK_GATE_SURFACE == "qmn.host.runtime_risk_gate"
    assert PAPER_PROFIT_IS_PROOF is False
    assert MANUAL_OBSERVATION_IS_PROOF is False
    assert tuple(spec.contract_id for spec in REQUIRED_RISK_CONTRACTS) == (
        "CT-22",
        "CT-23",
        "CT-24",
        "CT-25",
        "CT-27",
        "CT-28",
        "CT-29",
        "CT-30",
        "CT-31",
        "CT-32",
    )
    assert RUNTIME_RISK_SCENARIOS == (
        "entry_preservation",
        "exits_under_blocks",
        "paper_routing",
        "unknown",
        "four_verdict_reconciliation",
        "priority_compose_conflict",
        "bench",
        "kill_line",
        "next_day_activation",
    )


def test_production_coverage_passes_on_qmn_src() -> None:
    report = _ok(evaluate_runtime_risk_coverage())
    assert report.wired_contracts == tuple(spec.contract_id for spec in REQUIRED_RISK_CONTRACTS)
    assert qmn_production_src_root().name == "qmn"
    assert (qmn_production_src_root() / "host" / "runtime_risk_gate.py").is_file()


def test_import_only_unwired_contract_fails_with_traceability_id(tmp_path: Path) -> None:
    (tmp_path / "import_only.py").write_text(
        "\n".join(
            [
                "from qmf.risk.templates import BookDefinition, BmsDefinition",
                "from qmf.risk.door import admit_entry_intent",
                "from qmf.risk.paper import resolve_execution_target",
                "from qmf.risk.journal import project_entity_journal",
                "from qmf.risk.binding import BookBindingRecord",
                "from qmf.risk.exit_record import mint_exit_record",
                "from qmf.risk.control_action import mint_control_action",
                "from qmf.risk.control_window import evaluate_entry_under_windows",
                "from qmf.risk.performance import mint_performance_result",
            ]
        ),
        encoding="utf-8",
    )
    refused = _refusal(evaluate_runtime_risk_coverage(source_root=tmp_path))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "risk_gate.unwired_contract"
    trace = refused.context["traceability_id"]
    assert isinstance(trace, str) and trace.startswith("D010/")
    assert refused.context["missing_runtime_path"]
    assert "importable but unwired" in str(refused.context["reason"])


def test_paper_profit_cannot_satisfy_the_gate() -> None:
    refused = _refusal(
        run_runtime_risk_gate(
            RuntimeRiskGateInputs(clock=_clock(), venue=_venue(), paper_profit=1_000_000)
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "risk_gate.paper_profit"
    assert refused.context["paper_profit_is_proof"] is False
    assert refused.context["traceability_id"] == "D010/TN-23"
    structural = refuse_paper_profit_as_proof()
    assert structural.category is RefusalCategory.POLICY_REJECTION


def test_manual_observation_cannot_satisfy_the_gate() -> None:
    refused = _refusal(
        run_runtime_risk_gate(
            RuntimeRiskGateInputs(
                clock=_clock(),
                venue=_venue(),
                manual_observation="looks profitable",
            )
        )
    )
    assert refused.context["failure_id"] == "risk_gate.manual_observation"
    assert refused.context["manual_observation_is_proof"] is False
    assert refuse_manual_observation_as_proof().category is RefusalCategory.POLICY_REJECTION


def test_gate_exercises_contracts_scenarios_refusals_and_evidence() -> None:
    report = _ok(run_runtime_risk_gate(_inputs()))
    assert report.composition_sealed is True
    assert report.paper_profit_is_proof is False
    assert report.manual_observation_is_proof is False
    assert report.contracts_exercised == tuple(spec.contract_id for spec in REQUIRED_RISK_CONTRACTS)
    assert report.scenarios_exercised == RUNTIME_RISK_SCENARIOS
    assert set(report.refusal_paths) == {member.value for member in RefusalCategory}
    for category, path in report.refusal_paths.items():
        assert isinstance(path, str) and path, category
    for scenario in RUNTIME_RISK_SCENARIOS:
        record = report.evidence_records[scenario]
        assert isinstance(record, dict) or hasattr(record, "keys")
        assert dict(record), scenario

    entry = dict(report.evidence_records["entry_preservation"])
    assert entry["rebased"] is False
    assert "authorized_intent" in entry
    assert "frozen_r" in entry
    assert "exit_record" in entry

    exits = dict(report.evidence_records["exits_under_blocks"])
    assert exits["entry_blocked"] is True
    assert exits["exit_passed"] is True

    paper = dict(report.evidence_records["paper_routing"])
    assert paper["bot_twin_minted"] is False
    assert paper["book_twin_minted"] is False
    assert paper["mode"] == "PAPER"

    unknown = dict(report.evidence_records["unknown"])
    assert unknown["outcome"] == "UNKNOWN"
    assert unknown["stream_open"] is False
    assert unknown["sensing_continues"] is True
    assert unknown["refusal_category"] == RefusalCategory.TRANSIENT_VENUE_FAILURE.value

    verdicts = dict(report.evidence_records["four_verdict_reconciliation"])
    seen = cast("list[str]", verdicts["verdicts"])
    assert set(seen) == {
        "reconciled",
        "drift",
        "unknown",
        "out-of-lookback",
    }

    compose = dict(report.evidence_records["priority_compose_conflict"])
    emit = cast("list[str]", compose["emit"])
    assert set(emit) == {"suspend_new", "flatten"}
    assert compose["arrival_order_ignored"] is True

    bench = dict(report.evidence_records["bench"])
    assert bench["threshold_crossed"] is True
    assert bench["book_mode"] == "LIVE"
    assert bench["seat_state"] == "benched"
    assert bench["qualifying_loss_count"] == 2

    kill = dict(report.evidence_records["kill_line"])
    assert kill["breached"] is True
    assert kill["close_reason"] == "kill_line_flat"
    assert kill["other_bindings_unaffected"] is True

    activation = dict(report.evidence_records["next_day_activation"])
    assert activation["may_trade"] is False
    assert activation["enforced_state"] == "admitted"
    effective = activation["effective_at_ns"]
    signed = activation["signed_at_ns"]
    assert isinstance(effective, int) and isinstance(signed, int)
    assert effective > signed
    assert activation["same_day_trade_path_exists"] is False
