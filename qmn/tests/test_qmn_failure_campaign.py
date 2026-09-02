"""Story 28.3 — injected command, protection, and reconciliation failure paths."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core import (
    ExactRational,
    Money,
    UnitKind,
    VenueId,
    World,
)
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    DESIGNED_DEGRADED_STATES,
    FAILURE_CAMPAIGN_CLASS,
    FAILURE_CAMPAIGN_SURFACE,
    INJECTED_COMMAND_FAULTS,
    INVENTS_KSA_OR_LATENCY,
    PROTECTION_COINCIDENCE_FIXTURES,
    REQUIRES_LIVE_DEMO_ACCOUNT,
    FailureCampaignInputs,
    refuse_live_demo_account_required,
    run_paper_milestone_failure_campaign,
)
from qmn.host.failure_campaign import refuse_invented_ksa_or_latency_number
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.time import VpsClock
from qmn.venue import (
    SHARED_FAULT_CONTRACT,
    ConformanceDouble,
    InjectedFault,
    ReconciliationVerdict,
    SubmissionOutcome,
    VenueClientKind,
    agree_live_and_double_fault_contract,
)

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
            boot_epoch_id="boot-28-3",
            wall_ns=lambda: _NS,
            monotonic_ns=lambda: _NS,
        )
    )


def _venue() -> ConformanceDouble:
    venue_id = _ok(VenueId.try_create("conformance:paper-28-3"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, venue_id))
    assert double.kind is VenueClientKind.CONFORMANCE
    return double


def _floor() -> Money:
    return _ok(Money.try_create(80_000_00, "USD", 2))


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE))


def _inputs(**overrides: object) -> FailureCampaignInputs:
    kwargs: dict[str, object] = {
        "clock": _clock(),
        "venue": _venue(),
        "kill_line_capital_floor": _floor(),
        "qualifying_loss_threshold": _r(1),
        "bench_consecutive_loss_threshold": 2,
        "breakeven_ratchet_trigger": _r(1),
    }
    kwargs.update(overrides)
    return FailureCampaignInputs(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_pin_ftr07_and_need_no_live_account() -> None:
    assert FAILURE_CAMPAIGN_SURFACE == "qmn.host.failure_campaign"
    assert FAILURE_CAMPAIGN_CLASS == "paper-milestone-failure-campaign"
    assert REQUIRES_LIVE_DEMO_ACCOUNT is False
    assert INVENTS_KSA_OR_LATENCY is False
    assert tuple(fault.value for fault in INJECTED_COMMAND_FAULTS) == (
        "timeout",
        "transport-error",
        "disconnect",
        "superseded-by-fill",
        "reconnect-gap",
        "unpersistable-identity",
        "queue-bound",
        "protective-stop-capability",
    )
    assert PROTECTION_COINCIDENCE_FIXTURES == (
        "ksa",
        "kill-line",
        "news",
        "dead-zone",
        "sqs",
        "ad-37",
    )
    assert SHARED_FAULT_CONTRACT["timeout"] == SubmissionOutcome.UNKNOWN.value
    assert SHARED_FAULT_CONTRACT["superseded-by-fill"] == (
        SubmissionOutcome.REJECTED_BY_VENUE.value
    )


def test_campaign_proves_all_injected_faults_and_coincidence() -> None:
    report = _ok(run_paper_milestone_failure_campaign(_inputs()))
    assert report.live_demo_account_required is False
    assert report.invents_ksa_or_latency is False
    assert report.ksa_matrix_values_supplied is False
    assert report.live_double_contract_agrees is True
    assert report.unknown_blocks_one_stream is True
    assert report.protective_intents_survive is True
    assert report.fills_persist_before_healthy is True
    assert report.commands_retried == 0
    assert report.unprotected_entries_refused is True
    assert tuple(report.injected_faults) == tuple(fault.value for fault in INJECTED_COMMAND_FAULTS)
    assert dict(report.degraded_states) == dict(DESIGNED_DEGRADED_STATES)
    coincidence = report.protection_coincidence
    for name in PROTECTION_COINCIDENCE_FIXTURES:
        assert name in coincidence

    def _section(name: str) -> Mapping[str, object]:
        value = coincidence[name]
        assert isinstance(value, Mapping)
        return cast("Mapping[str, object]", value)

    ksa = _section("ksa")
    assert ksa["scoped_monotone"] is True
    assert ksa["operator_only_deescalation"] is True
    assert ksa["live_connectivity_blocks_demo"] is False
    ad37 = _section("ad-37")
    assert ad37["compose_both_execute"] is True
    assert ad37["exit_preservation"] is True
    kill_line = _section("kill-line")
    assert kill_line["paper_flatten_stand_down"] is True
    news = _section("news")
    assert news["widen_not_shrink"] == "narrowing-held"
    assert news["exit_preserved"] is True
    dead_zone = _section("dead-zone")
    assert dead_zone["exit_preserved"] is True
    sqs = _section("sqs")
    assert sqs["separated"] is True
    ratchet = _section("ratchet")
    assert ratchet["single_sided"] is True
    bench = _section("bench")
    assert bench["book_mode"] == "LIVE"
    recon = report.reconciliation
    assert recon["verdicts"] == ["drift", "out-of-lookback", "reconciled", "unknown"]
    assert recon["residuals_proven"] is True
    assert recon["demo_drift"] == "alarm-and-continue"
    assert recon["live_drift"] == "entries-only-stand-down"
    assert recon["out_of_lookback_auto_resolves"] is False
    assert recon["venue_equity_differenced"] is False
    mapped = report.as_mapping()
    assert mapped["fingerprint"] == report.fingerprint.value
    assert mapped["surface"] == FAILURE_CAMPAIGN_SURFACE


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(run_paper_milestone_failure_campaign(_inputs()))
    second = _ok(run_paper_milestone_failure_campaign(_inputs()))
    assert first.fingerprint == second.fingerprint


def test_refuses_live_demo_account_requirement() -> None:
    refused = _refusal(
        run_paper_milestone_failure_campaign(_inputs(require_live_demo_account=True))
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "failure_campaign.live_demo_account"
    direct = refuse_live_demo_account_required()
    assert is_refusal(direct)
    assert direct.context["failure_id"] == "failure_campaign.live_demo_account"


def test_ftr07_refuses_invented_ksa_or_latency() -> None:
    ksa = _refusal(run_paper_milestone_failure_campaign(_inputs(invent_ksa_matrix_values=True)))
    assert ksa.context["failure_id"] == "failure_campaign.invented_ksa_or_latency"
    latency = _refusal(run_paper_milestone_failure_campaign(_inputs(invent_latency_gate=True)))
    assert latency.context["failure_id"] == "failure_campaign.invented_ksa_or_latency"
    direct = refuse_invented_ksa_or_latency_number()
    assert is_refusal(direct)


def test_demo_sqs_never_satisfies_live() -> None:
    refused = _refusal(
        run_paper_milestone_failure_campaign(_inputs(claim_demo_sqs_satisfies_live=True))
    )
    assert refused.context["failure_id"] == "failure_campaign.demo_sqs_satisfies_live"


def test_venue_equity_never_subtracted() -> None:
    refused = _refusal(
        run_paper_milestone_failure_campaign(_inputs(subtract_venue_from_virtual_equity=True))
    )
    assert refused.context["failure_id"] == "failure_campaign.equity_difference"


def test_live_and_double_contract_agree_when_live_results_match() -> None:
    report = _ok(
        run_paper_milestone_failure_campaign(
            _inputs(live_fault_results=dict(SHARED_FAULT_CONTRACT))
        )
    )
    assert report.live_double_contract_agrees is True


def test_live_double_contract_divergence_refuses() -> None:
    diverged = dict(SHARED_FAULT_CONTRACT)
    diverged["timeout"] = SubmissionOutcome.REJECTED_BY_VENUE.value
    refused = _refusal(run_paper_milestone_failure_campaign(_inputs(live_fault_results=diverged)))
    assert refused.context["failure_id"] == "failure_campaign.live_double_divergence"


def test_agree_helper_accepts_missing_live_results() -> None:
    agreed = _ok(agree_live_and_double_fault_contract(dict(SHARED_FAULT_CONTRACT), None))
    assert agreed["disconnect"] == SubmissionOutcome.UNKNOWN.value


def test_double_inject_scripts_node_local_flags() -> None:
    client = _venue()
    identity = _ok(client.inject(InjectedFault.UNPERSISTABLE_IDENTITY))
    assert identity is InjectedFault.UNPERSISTABLE_IDENTITY
    assert client.identity_persistable is False
    queue = _ok(client.inject("queue-bound"))
    assert queue is InjectedFault.QUEUE_BOUND
    assert client.queue_bound_breached is True
    assert client.identity_persistable is True
    stop = _ok(client.inject(InjectedFault.PROTECTIVE_STOP_CAPABILITY))
    assert stop is InjectedFault.PROTECTIVE_STOP_CAPABILITY
    assert dict(client.protective_stop_forms) == {}
    gap = _ok(client.inject(InjectedFault.RECONNECT_GAP))
    assert gap is InjectedFault.RECONNECT_GAP
    recovered = client.gap_recovered_observations()
    assert recovered[0]["kind"] == "fill"
    armed = _ok(client.arm_reconcile(ReconciliationVerdict.OUT_OF_LOOKBACK))
    assert armed is ReconciliationVerdict.OUT_OF_LOOKBACK
    recon = _ok(client.reconcile())
    assert recon.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in (
        "failure_campaign.demo_sqs_satisfies_live",
        "failure_campaign.equity_difference",
        "failure_campaign.incomplete_injection",
        "failure_campaign.inputs",
        "failure_campaign.invented_kill_line_floor",
        "failure_campaign.invented_ksa_or_latency",
        "failure_campaign.live_demo_account",
        "failure_campaign.live_double_divergence",
        "failure_campaign.venue",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
