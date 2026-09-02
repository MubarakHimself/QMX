"""Story 28.8 — TN-23 live-readiness verdict packet and checklist fold."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    ACTIVATION_WAITS_FOR_DAY_BOUNDARY,
    BLOCKED_INFRA_ITEMS,
    BLOCKED_INFRA_SCOPES,
    FORBIDDEN_VERDICT_KEYS,
    LIVE_INSTRUMENT_REQUIREMENTS,
    OPENS_LIVE_BINDING,
    PAPER_MILESTONE_IMMUTABLE,
    PRE_WEEK_STORIES,
    PROFIT_ENTERS_VERDICT,
    PROMOTION_AND_ACTIVATION_ARE_SEPARATE,
    REQUIRED_CHECKLIST_ITEM_IDS,
    RUNS_UNATTENDED_PAPER_WEEK,
    TN23_CHECKLIST_ITEMS,
    VERDICT_PACKET_CLASS,
    VERDICT_SURFACE,
    WHOLE_SYSTEM_SURFACES,
    ChecklistItemStatus,
    WeekInterruptionClass,
    apply_week_interruption,
    evaluate_live_instrument_readiness,
    fold_tn23_checklist,
    publish_live_readiness_verdict,
    record_operator_proceed,
    refuse_live_binding,
    refuse_merged_promotion_activation,
    refuse_profit_in_verdict,
    refuse_same_day_activation,
    refuse_unattended_paper_week,
    run_unattended_paper_week,
)
from qmn.host.verdict import (
    refuse_invented_ksa_or_latency_number,
    refuse_procure_vps,
)
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.paper.first_deployment import DEMO_SHAPE_MACHINERY

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "verdict-test", "label": label}))


def _journal(
    *,
    refused: frozenset[str] = frozenset(),
    extra: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    evidence = _fp("item-evidence")
    recovery = _fp("recovery")
    items: list[dict[str, object]] = []
    for item_id in REQUIRED_CHECKLIST_ITEM_IDS:
        row: dict[str, object] = {
            "item_id": item_id,
            "status": "refuse" if item_id in refused else "pass",
            "evidence_fp1": evidence,
            "incidents": (),
            "recovery_proof_fp1": recovery,
        }
        items.append(row)
    if extra is not None:
        items.append(extra)
    return items


def _live_ready_flags() -> dict[str, bool]:
    return dict.fromkeys(LIVE_INSTRUMENT_REQUIREMENTS, True)


def _publish(**overrides: object):
    kwargs: dict[str, object] = {
        "journaled_items": _journal(),
        "first_hours_fp1": _fp("first-hours"),
    }
    kwargs.update(overrides)
    return publish_live_readiness_verdict(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_skip_week_vps_profit_and_live_binding() -> None:
    assert VERDICT_SURFACE == "qmn.host.verdict"
    assert VERDICT_PACKET_CLASS == "tn23-live-readiness-verdict"
    assert RUNS_UNATTENDED_PAPER_WEEK is False
    assert OPENS_LIVE_BINDING is False
    assert PROFIT_ENTERS_VERDICT is False
    assert PROMOTION_AND_ACTIVATION_ARE_SEPARATE is True
    assert ACTIVATION_WAITS_FOR_DAY_BOUNDARY is True
    assert PAPER_MILESTONE_IMMUTABLE is True
    assert PRE_WEEK_STORIES == (
        "28.1",
        "28.2",
        "28.3",
        "28.4",
        "28.5",
        "28.6",
        "28.7",
    )
    assert BLOCKED_INFRA_SCOPES == (
        "vps_procurement",
        "ksa_matrix_values",
        "paper_week",
    )
    assert WHOLE_SYSTEM_SURFACES == DEMO_SHAPE_MACHINERY
    assert "profit" in FORBIDDEN_VERDICT_KEYS
    assert "loss" in FORBIDDEN_VERDICT_KEYS
    assert "win_rate" in FORBIDDEN_VERDICT_KEYS
    assert "paper_performance" in FORBIDDEN_VERDICT_KEYS
    assert len(TN23_CHECKLIST_ITEMS) == 30
    assert set(REQUIRED_CHECKLIST_ITEM_IDS).isdisjoint(BLOCKED_INFRA_ITEMS)
    assert set(BLOCKED_INFRA_ITEMS) <= set(TN23_CHECKLIST_ITEMS)
    assert BLOCKED_INFRA_ITEMS["unattended-week-continuous"] == "paper_week"
    assert BLOCKED_INFRA_ITEMS["ksa-escalation"] == "ksa_matrix_values"
    assert BLOCKED_INFRA_ITEMS["systemd-load-credential-encrypted"] == "vps_procurement"


def test_fold_skips_blocked_infra_and_publishes_pass_refuse() -> None:
    folded = _ok(fold_tn23_checklist(_journal()))
    by_id = {item.item_id: item for item in folded}
    assert tuple(item.item_id for item in folded) == TN23_CHECKLIST_ITEMS
    for item_id in REQUIRED_CHECKLIST_ITEM_IDS:
        row = by_id[item_id]
        assert row.status is ChecklistItemStatus.PASSED
        assert row.evidence_fp1 is not None
        assert row.recovery_proof_fp1 is not None
    for item_id, scope in BLOCKED_INFRA_ITEMS.items():
        row = by_id[item_id]
        assert row.status is ChecklistItemStatus.SKIPPED_BLOCKED_INFRA
        assert row.blocked_infra == scope
        assert row.evidence_fp1 is None
    refused = _ok(fold_tn23_checklist(_journal(refused=frozenset({"no-scale-in"}))))
    assert next(item for item in refused if item.item_id == "no-scale-in").status is (
        ChecklistItemStatus.REFUSED
    )


def test_packet_records_fingerprints_incidents_baselines_and_value_status() -> None:
    packet = _ok(
        _publish(
            incidents=("incident-1",),
            recovery_proofs=("recovery-1",),
            value_status={
                "kill_line_capital_floor": "provisional-evidence",
                "governor_cpu_budget": "ratified",
            },
        )
    )
    assert packet.fingerprint.value.startswith("fp1:sha256:")
    assert packet.qa_debt_matrix_fp1.value.startswith("fp1:sha256:")
    assert packet.first_hours_fp1 == _fp("first-hours")
    assert packet.incidents == ("incident-1",)
    assert packet.recovery_proofs == ("recovery-1",)
    assert packet.value_status["kill_line_capital_floor"] == "provisional-evidence"
    assert packet.value_status["governor_cpu_budget"] == "ratified"
    assert packet.ok is True
    assert packet.week_complete is False
    assert packet.unattended_week_ran is False
    assert packet.live_binding_open is False
    assert packet.grants_live_money_authority is False
    assert packet.profit_enters_verdict is False
    assert packet.demo_milestone_invalidated is False
    identity = packet.fp1_identity()
    assert identity["class"] == VERDICT_PACKET_CLASS
    assert "version" not in identity
    assert "profit" not in identity
    assert "loss" not in identity
    assert "win_rate" not in identity
    mapped = packet.as_mapping()
    assert mapped["fingerprint"] == packet.fingerprint.value
    assert mapped["runs_unattended_paper_week"] is False
    assert mapped["opens_live_binding"] is False
    assert mapped["paper_milestone_immutable"] is True
    assert "profit" not in mapped
    assert set(packet.blocked_infra) == {"ksa_matrix_values", "paper_week", "vps_procurement"}


def test_profit_loss_win_rate_and_paper_performance_are_refused() -> None:
    profit = _refusal(_publish(profit=12))
    assert profit.category is RefusalCategory.POLICY_REJECTION
    assert profit.context["failure_id"] == "verdict.profit"
    assert profit.context["profit_enters_verdict"] is False
    loss = _refusal(_publish(loss=3))
    assert loss.context["failure_id"] == "verdict.profit"
    win_rate = _refusal(_publish(win_rate="0.6"))
    assert win_rate.context["failure_id"] == "verdict.profit"
    performance = _refusal(_publish(paper_performance={"sharpe": 1}))
    assert performance.context["failure_id"] == "verdict.profit"
    nested = _refusal(_publish(journaled_items=[*_journal(), {"profit": 1}]))
    assert nested.context["failure_id"] == "verdict.profit"
    keyed = _refusal(
        fold_tn23_checklist(
            [
                {
                    "item_id": "no-scale-in",
                    "status": "pass",
                    "evidence_fp1": _fp("item-evidence"),
                    "win_rate": 0.4,
                }
            ]
        )
    )
    assert keyed.context["failure_id"] == "verdict.profit"
    assert refuse_profit_in_verdict().context["failure_id"] == "verdict.profit"


def test_running_the_week_or_claiming_it_complete_is_refused() -> None:
    week = _refusal(_publish(run_unattended_week=True))
    assert week.context["failure_id"] == "verdict.unattended_week"
    claimed = _refusal(_publish(claim_week_complete=True))
    assert claimed.context["failure_id"] == "verdict.unattended_week"
    direct = run_unattended_paper_week()
    assert direct.context["failure_id"] == "verdict.unattended_week"
    assert refuse_unattended_paper_week().context["failure_id"] == "verdict.unattended_week"


def test_procure_vps_and_invented_ksa_or_latency_are_refused() -> None:
    vps = _refusal(_publish(procure_vps=True))
    assert vps.context["failure_id"] == "verdict.procure_vps"
    ksa = _refusal(_publish(invented_ksa_value={"level": 3}))
    assert ksa.context["failure_id"] == "verdict.invented_ksa_or_latency"
    latency = _refusal(_publish(invented_latency_value=50))
    assert latency.context["failure_id"] == "verdict.invented_ksa_or_latency"
    duration = _refusal(_publish(soak_duration=604_800))
    assert duration.context["failure_id"] == "verdict.invented_ksa_or_latency"
    assert refuse_procure_vps().context["failure_id"] == "verdict.procure_vps"
    assert (
        refuse_invented_ksa_or_latency_number().context["failure_id"]
        == "verdict.invented_ksa_or_latency"
    )


def test_missing_required_item_fails_the_fold() -> None:
    items = [row for row in _journal() if row["item_id"] != "no-scale-in"]
    refused = _refusal(fold_tn23_checklist(items))
    assert refused.context["failure_id"] == "verdict.incomplete_checklist"
    assert refused.context["missing"] == ("no-scale-in",)


def test_unplanned_interruption_restarts_the_week_clock() -> None:
    unplanned = _ok(apply_week_interruption("unplanned"))
    assert unplanned.interruption is WeekInterruptionClass.UNPLANNED
    assert unplanned.restart_full_week_clock is True
    assert unplanned.week_complete is False
    planned = _ok(apply_week_interruption("planned-drill-boundary"))
    assert planned.restart_full_week_clock is False
    drill = _ok(apply_week_interruption("drill"))
    assert drill.interruption is WeekInterruptionClass.PLANNED_DRILL_BOUNDARY
    assert drill.restart_full_week_clock is False
    boundary = _ok(apply_week_interruption("boundary"))
    assert boundary.restart_full_week_clock is False
    unknown = _refusal(apply_week_interruption("operator-watched"))
    assert unknown.context["failure_id"] == "verdict.inputs"


def test_missing_live_evidence_delays_binding_without_invalidating_demo() -> None:
    delayed = _ok(_publish(live_credentials_present=False))
    assert delayed.live_ready is False
    assert delayed.live_delayed is True
    assert delayed.demo_milestone_invalidated is False
    assert delayed.ok is True
    partial = _ok(
        _publish(
            live_credentials_present=True,
            live_instruments={"EURUSD": {"kyc": True, "silent_battery_pass": True}},
        )
    )
    assert partial.live_delayed is True
    assert partial.live_ready is False
    assert partial.demo_milestone_invalidated is False
    eur = partial.live_instruments[0]
    assert eur.instrument == "EURUSD"
    assert "verified_capability_profile" in eur.missing
    assert "live_conditioned_sqs_baseline" in eur.missing
    ready = _ok(
        _publish(
            live_credentials_present=True,
            live_instruments={"EURUSD": _live_ready_flags(), "GBPUSD": _live_ready_flags()},
        )
    )
    assert ready.live_ready is True
    assert ready.live_delayed is False
    assert ready.live_binding_open is False
    assert ready.grants_live_money_authority is False
    without_creds = _ok(
        evaluate_live_instrument_readiness(
            live_credentials_present=False,
            instruments={"EURUSD": _live_ready_flags()},
        )
    )
    assert without_creds[0].ready is False
    assert without_creds[0].missing == LIVE_INSTRUMENT_REQUIREMENTS


def test_operator_proceed_opens_no_live_binding() -> None:
    packet = _ok(_publish())
    proceeding = _ok(record_operator_proceed(packet))
    assert proceeding.live_binding_open is False
    assert proceeding.grants_live_money_authority is False
    assert proceeding.promotion_activation_separate is True
    assert proceeding.activation_waits_for_day_boundary is True
    assert proceeding.paper_milestone_immutable is True
    assert proceeding.paper_milestone_fp1 == packet.fingerprint
    live = _refusal(record_operator_proceed(packet, request_live_binding=True))
    assert live.context["failure_id"] == "verdict.live_binding"
    merged = _refusal(record_operator_proceed(packet, merge_promotion_activation=True))
    assert merged.context["failure_id"] == "verdict.promotion_activation"
    same_day = _refusal(record_operator_proceed(packet, same_day_activation=True))
    assert same_day.context["failure_id"] == "verdict.promotion_activation"
    opened = _refusal(_publish(open_live_binding=True))
    assert opened.context["failure_id"] == "verdict.live_binding"
    assert refuse_live_binding().context["failure_id"] == "verdict.live_binding"
    assert (
        refuse_merged_promotion_activation().context["failure_id"] == "verdict.promotion_activation"
    )
    assert refuse_same_day_activation().context["failure_id"] == "verdict.promotion_activation"


def test_refused_checklist_item_publishes_ok_false() -> None:
    packet = _ok(_publish(journaled_items=_journal(refused=frozenset({"bench-fold"}))))
    assert packet.ok is False
    bench = next(item for item in packet.items if item.item_id == "bench-fold")
    assert bench.status is ChecklistItemStatus.REFUSED
    assert packet.live_binding_open is False


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(_publish())
    second = _ok(_publish())
    assert first.fingerprint == second.fingerprint
    assert [item.as_mapping() for item in first.items] == [
        item.as_mapping() for item in second.items
    ]


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in (
        "verdict.profit",
        "verdict.unattended_week",
        "verdict.live_binding",
        "verdict.procure_vps",
        "verdict.invented_ksa_or_latency",
        "verdict.inputs",
        "verdict.incomplete_checklist",
        "verdict.promotion_activation",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
