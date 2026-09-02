"""Story 28.2 — first-deployment PAPER routing and live sensing-only contract."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import AccountRole, Fingerprint, VenueId, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.binding import BmsInstanceId
from qmf.risk.paper import BookMode, ExecutionTarget, RoutingOutcome, SeatState
from qmn.config import (
    AccountBindingDecl,
    BookBindingDecl,
    PositionModelDecl,
    SensingOnlyDecl,
    StateCarryChoice,
    ThrottleScope,
)
from qmn.config.roster import STATE_CARRY_COUNTERS
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.paper import (
    DECLARED_FAULT_INJECTION_POINTS,
    DEMO_SHAPE_MACHINERY,
    DEMO_SHAPE_NODE_TIMERS,
    DEMO_SHAPE_UNITS,
    FAULT_INJECTION_MODE,
    FIRST_DEPLOYMENT_BOOK_ROUTING,
    FIRST_DEPLOYMENT_SURFACE,
    LATE_LIVE_APPROVAL_DELAYS,
    LIVE_SENSING_ALLOWED,
    LIVE_SENSING_FORBIDDEN,
    NODE_PAPER_ACCOUNT_ROLE,
    OPENS_LIVE_CREDENTIALS,
    PRE_UNATTENDED_PROOFS,
    PROCURES_VPS,
    admit_live_sensing,
    begin_unattended_interval,
    build_paired_demo_target,
    compose_first_deployment_window,
    record_pre_unattended_proofs,
    refuse_open_live_credentials,
    refuse_procure_vps,
    require_first_deployment_book_routing,
    resolve_first_deployment_execution_target,
)
from qmn.paper.first_deployment import (
    DEMO_SHAPE_DOORS,
    DEMO_SHAPE_PRINCIPALS,
    DEMO_SHAPE_TREES,
    FIRST_DEPLOYMENT_WINDOW_CLASS,
    FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION,
)

T = TypeVar("T")

_VENUE = VenueId(value="ic-markets")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "first-deployment-test", "label": label}))


def _state_carry() -> dict[str, StateCarryChoice]:
    return dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)


def _book() -> BookBindingDecl:
    return BookBindingDecl(
        binding_id="book-demo-1",
        book_definition_fp1="fp1:book:demo",
        instruments=frozenset({"EURUSD"}),
    )


def _demo_binding() -> AccountBindingDecl:
    return AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-demo-1",
        role=AccountRole.DEMO,
        world=World.LIVE,
        environment="demo",
        credential_reference="qmx/venue-demo",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:demo",
        bms_instance_id="bms-demo-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-demo-1",
    )


def _bms(account: str, seed: str) -> BmsInstanceId:
    return _ok(BmsInstanceId.derive(_fp(seed), account, _VENUE, World.LIVE))


def _paired():
    return _ok(
        build_paired_demo_target(
            venue_id=_VENUE,
            account_id="acct-demo-1",
            live_bms_instance_id=_bms("acct-live", "bms-live"),
            paired_bms_instance_id=_bms("acct-demo-1", "bms-demo"),
            live_binding_epoch=_fp("live-binding-demo"),
        )
    )


def _sensing() -> SensingOnlyDecl:
    return SensingOnlyDecl(
        venue_id="ic-markets",
        environment="live",
        account_id="acct-live-sense",
        credential_reference="qmx/venue-live",
        opaque_metric_id="m-sense",
    )


def _compose(**overrides: object):
    kwargs: dict[str, object] = {
        "demo_binding": _demo_binding(),
        "paired": _paired(),
        "protective_reserve_capacity": 1,
    }
    kwargs.update(overrides)
    return compose_first_deployment_window(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_pin_paper_and_do_not_provision() -> None:
    assert FIRST_DEPLOYMENT_SURFACE == "qmn.paper.first_deployment"
    assert FIRST_DEPLOYMENT_WINDOW_CLASS == "first-deployment-window"
    assert FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION == 1
    assert FIRST_DEPLOYMENT_BOOK_ROUTING is BookMode.PAPER
    assert DEMO_SHAPE_DOORS == ("powers", "evidence")
    assert DEMO_SHAPE_TREES == ("rooms", "evidence", "hub-inbox", "hub-published")
    assert DEMO_SHAPE_PRINCIPALS == ("qmx", "qmxobs", "ops")
    assert PROCURES_VPS is False
    assert OPENS_LIVE_CREDENTIALS is False
    assert FAULT_INJECTION_MODE == "declared-boundary-only"
    assert DEMO_SHAPE_NODE_TIMERS == (
        "qmn-news-calendar.timer",
        "qmn-backup.timer",
        "qmn-restore-sample.timer",
        "qmn-restore-full.timer",
    )
    assert "qmn.service" in DEMO_SHAPE_UNITS
    assert "qmx-observability.service" in DEMO_SHAPE_UNITS
    assert "paired-demo-account" in DEMO_SHAPE_MACHINERY
    assert "paper-virtual-ledger" in DEMO_SHAPE_MACHINERY
    assert LIVE_SENSING_FORBIDDEN == (
        "live-binding",
        "command-stream",
        "sequencer",
        "execution-target",
    )
    assert "sensing" in LIVE_SENSING_ALLOWED
    assert LATE_LIVE_APPROVAL_DELAYS == ("live-baseline", "go-live")
    assert frozenset({"boundary", "drill"}) == DECLARED_FAULT_INJECTION_POINTS
    assert PRE_UNATTENDED_PROOFS == (
        "synthetic-alert",
        "missing-heartbeat-notification",
    )


def test_window_pins_paper_routing_and_paired_demo_ledger() -> None:
    window = _ok(_compose())
    assert window.book_routing is BookMode.PAPER
    assert window.paired.paper_target.role is NODE_PAPER_ACCOUNT_ROLE
    assert window.paired.world is World.LIVE
    assert window.paired.bot_twin_minted is False
    assert window.paired.book_twin_minted is False
    assert window.paper_virtual_ledger is True
    assert window.procures_vps is False
    assert window.opens_live_credentials is False
    assert window.demo_week_blocked_by_late_live is False
    assert window.blocked_infra == ("vps_procurement",)
    assert any(plan.connection.environment == "demo" for plan in window.composition.command_streams)
    assert window.live_sensing.sensing_open is False
    assert window.live_sensing.delays == LATE_LIVE_APPROVAL_DELAYS
    assert window.fingerprint.value.startswith("fp1:sha256:")
    identity = window.fp1_identity()
    assert identity["class"] == "first-deployment-window"
    assert "version" not in identity


def test_live_book_routing_is_refused_for_the_window() -> None:
    refused = _refusal(require_first_deployment_book_routing(BookMode.LIVE))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "first_deployment.book_routing"
    composed = _refusal(_compose(book_mode=BookMode.LIVE))
    assert composed.context["failure_id"] == "first_deployment.book_routing"


def test_paper_intents_route_to_paired_demo() -> None:
    live = _ok(ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, "acct-live"))
    paper = _ok(ExecutionTarget.try_create(AccountRole.DEMO, _VENUE, "acct-demo-1"))
    resolution = _ok(
        resolve_first_deployment_execution_target(
            book_mode=BookMode.PAPER,
            seat_state=SeatState.ACTIVE,
            active_controls=(),
            live_target=live,
            paper_target=paper,
        )
    )
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    assert resolution.execution_target is not None
    assert resolution.execution_target.role is AccountRole.DEMO
    live_mode = _refusal(
        resolve_first_deployment_execution_target(
            book_mode=BookMode.LIVE,
            seat_state=SeatState.ACTIVE,
            active_controls=(),
            live_target=live,
            paper_target=paper,
        )
    )
    assert live_mode.context["failure_id"] == "first_deployment.book_routing"


def test_live_sensing_opens_only_when_credentials_exist() -> None:
    deferred = _ok(admit_live_sensing(credentials_present=False))
    assert deferred.sensing_open is False
    assert deferred.demo_week_blocked is False
    assert deferred.delays == LATE_LIVE_APPROVAL_DELAYS

    opened = _ok(admit_live_sensing(credentials_present=True, live_sensing=_sensing()))
    assert opened.sensing_open is True
    assert opened.may_record is True
    assert opened.may_verify_capabilities is True
    assert opened.may_accumulate_baseline is True
    assert opened.has_live_binding is False
    assert opened.has_command_stream is False
    assert opened.opens_sequencer is False
    assert opened.resolves_execution_target is False
    assert opened.demo_week_blocked is False

    window = _ok(_compose(live_credentials_present=True, live_sensing=_sensing()))
    assert window.live_sensing.sensing_open is True
    assert len(window.composition.sensing_plans) == 1
    plan = window.composition.sensing_plans[0]
    assert plan.opens_sequencer is False
    assert plan.has_command_stream is False
    assert plan.has_book_binding is False
    assert plan.resolves_execution_target is False
    assert plan.may_record_observations is True
    assert not any(
        stream.connection.environment == "live" for stream in window.composition.command_streams
    )


def test_live_authority_requests_are_refused() -> None:
    for flag, failure_id in (
        ("request_live_binding", "first_deployment.live_binding"),
        ("request_command_stream", "first_deployment.live_command_stream"),
        ("request_sequencer", "first_deployment.live_sequencer"),
        ("request_execution_target", "first_deployment.live_execution_target"),
    ):
        refused = _refusal(_compose(**{flag: True}))
        assert refused.context["failure_id"] == failure_id


def test_live_account_binding_is_refused() -> None:
    live = AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-live-1",
        role=AccountRole.LIVE,
        world=World.LIVE,
        environment="live",
        credential_reference="qmx/venue-live",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:live",
        bms_instance_id="bms-live-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-live-1",
    )
    refused = _refusal(_compose(live_account_binding=live))
    assert refused.context["failure_id"] == "first_deployment.live_binding"


def test_late_approval_does_not_block_the_demo_week() -> None:
    window = _ok(_compose(live_credentials_present=False))
    assert window.demo_week_blocked_by_late_live is False
    assert window.live_sensing.demo_week_blocked is False
    blocked = _refusal(_compose(treat_late_live_as_demo_blocker=True))
    assert blocked.context["failure_id"] == "first_deployment.late_approval_blocks_demo"


def test_pre_unattended_proofs_gate_the_week_start() -> None:
    incomplete = _ok(
        record_pre_unattended_proofs(
            synthetic_alert_delivered=True,
            missing_heartbeat_delivered=False,
        )
    )
    assert incomplete.unattended_interval_may_begin is False
    refused = _refusal(begin_unattended_interval(incomplete))
    assert refused.context["failure_id"] == "first_deployment.pre_unattended"

    ready = _ok(
        record_pre_unattended_proofs(
            synthetic_alert_delivered=True,
            missing_heartbeat_delivered=True,
            fault_injection_point="boundary",
        )
    )
    started = _ok(begin_unattended_interval(ready))
    assert started.unattended_interval_may_begin is True

    window = _ok(
        _compose(
            synthetic_alert_delivered=True,
            missing_heartbeat_delivered=True,
            claim_unattended_ready=True,
        )
    )
    assert window.pre_unattended.unattended_interval_may_begin is True

    missing = _refusal(_compose(claim_unattended_ready=True))
    assert missing.context["failure_id"] == "first_deployment.pre_unattended"


def test_continuous_supervision_and_undeclared_drills_are_refused() -> None:
    continuous = _refusal(
        record_pre_unattended_proofs(
            synthetic_alert_delivered=True,
            missing_heartbeat_delivered=True,
            continuous_human_supervision=True,
        )
    )
    assert continuous.context["failure_id"] == "first_deployment.continuous_supervision"
    undeclared = _refusal(
        record_pre_unattended_proofs(
            synthetic_alert_delivered=True,
            missing_heartbeat_delivered=True,
            fault_injection_point="always",
        )
    )
    assert undeclared.context["failure_id"] == "first_deployment.continuous_supervision"


def test_procure_vps_and_open_live_credentials_are_refused() -> None:
    procure = _refusal(_compose(procure_vps=True))
    assert procure.context["failure_id"] == "first_deployment.procure_vps"
    opened = _refusal(_compose(open_live_credentials=True))
    assert opened.context["failure_id"] == "first_deployment.open_live_credentials"
    sensing_without = _refusal(
        admit_live_sensing(credentials_present=False, live_sensing=_sensing())
    )
    assert sensing_without.context["failure_id"] == "first_deployment.open_live_credentials"
    assert refuse_procure_vps().context["failure_id"] == "first_deployment.procure_vps"
    assert (
        refuse_open_live_credentials().context["failure_id"]
        == "first_deployment.open_live_credentials"
    )


def test_demo_roster_requires_demo_role() -> None:
    live = AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-live-1",
        role=AccountRole.LIVE,
        world=World.LIVE,
        environment="live",
        credential_reference="qmx/venue-live",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:live",
        bms_instance_id="bms-live-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-live-1",
    )
    refused = _refusal(_compose(demo_binding=live))
    assert refused.context["failure_id"] == "first_deployment.demo_roster"


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in (
        "first_deployment.book_routing",
        "first_deployment.continuous_supervision",
        "first_deployment.demo_roster",
        "first_deployment.late_approval_blocks_demo",
        "first_deployment.live_binding",
        "first_deployment.live_command_stream",
        "first_deployment.live_execution_target",
        "first_deployment.live_sequencer",
        "first_deployment.open_live_credentials",
        "first_deployment.pre_unattended",
        "first_deployment.procure_vps",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(_compose())
    second = _ok(_compose())
    assert first.fingerprint == second.fingerprint
