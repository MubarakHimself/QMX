"""Story 26.16 — state the V1 seat-containment limit honestly (E15-F03)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmb.runloop import CancelToken, ScriptedLimitProbe
from qmf.core import Duration, Instant, RefusalCategory, fingerprint, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.refusal import Result
from qml.declaration import mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import FunctionFactory
from qmn.host.supervise import (
    LifecycleSupervisor,
    RecordingNotifyTransport,
    SupervisionConfig,
)
from qmn.observability import (
    AlertPublisher,
    RecordingNotificationChannel,
    load_alert_allow_list,
)
from qmn.seats import (
    COMPENSATING_CONTROLS,
    CONTAINMENT_LIMIT_SURFACE,
    GAP_0054_ID,
    GAP_0054_STATUS,
    OPERATOR_PRINCIPAL,
    OPERATOR_SEAT_REINSTATE,
    V1_HARDENED_OS_CONFINEMENT,
    ContainmentInjection,
    EnforcementClass,
    GovernedSeatState,
    QuarantineTrigger,
    SeatContainment,
    SeatTransitionStream,
    apply_operator_seat_reinstate,
    construct_governed_seat,
    fold_seat_state,
    prove_v1_seat_containment,
    refuse_invented_os_hard_cap,
    scan_os_confinement_apis,
    v1_containment_documentation_report,
    v1_seat_containment_limits,
)

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_REPO = Path(__file__).resolve().parents[2]


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _declaration():
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": _pinned("zone")}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [_pinned("sma")],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    return _ok(
        mint_bot_definition(
            strategy_family_id="trend-follow",
            confluence_set=[confluence],
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ],
            footprint=footprint,
            permitted_exit_intents=(),
            logic_reference=logic,
        )
    )


def _containment(*, deadline_ns: int = 1_000_000, memory_bytes: int = 10_000) -> SeatContainment:
    return _ok(
        SeatContainment.try_create(
            callback_deadline=_duration(deadline_ns),
            memory_ceiling_bytes=memory_bytes,
        )
    )


def _seat(*, factory: FunctionFactory | None = None, memory_bytes: int = 10_000):
    return _ok(
        construct_governed_seat(
            factory if factory is not None else FunctionFactory(logic=lambda evidence: ()),
            seat_id="seat-alpha",
            binding_ref="binding-live-1",
            declaration=_declaration(),
            containment=_containment(memory_bytes=memory_bytes),
            read_surfaces={},
            stream_id="stream-eurusd",
        )
    )


def _supervisor() -> LifecycleSupervisor:
    config = _ok(
        SupervisionConfig.try_create(
            crash_loop_max_boots=3,
            crash_loop_window_ns=60_000_000_000,
            drain_window_ns=30_000_000_000,
            watchdog_interval_ns=5_000_000_000,
            seat_callback_deadline_ns=1_000_000_000,
            slice_watch_trip_multiple=3,
        )
    )
    return LifecycleSupervisor(
        config=config,
        notify=RecordingNotifyTransport(),
        boot_epoch_id="boot-containment-26-16",
    )


def _publisher() -> tuple[AlertPublisher, RecordingNotificationChannel]:
    channel = RecordingNotificationChannel()
    publisher = AlertPublisher(allow_list=_ok(load_alert_allow_list()), channel=channel)
    return publisher, channel


def test_catalog_records_advisory_versus_enforced_and_does_not_close_gap() -> None:
    catalog = {record.name: record for record in v1_seat_containment_limits()}
    assert CONTAINMENT_LIMIT_SURFACE == "qmn.seats.containment_limit"
    assert V1_HARDENED_OS_CONFINEMENT is False
    assert GAP_0054_ID == "GAP-0054"
    assert GAP_0054_STATUS == "deferred"
    assert catalog["callback-deadline"].enforcement is EnforcementClass.ENFORCED
    assert catalog["callback-deadline"].cooperative is True
    assert catalog["memory-ceiling"].enforcement is EnforcementClass.ENFORCED
    assert catalog["memory-ceiling"].os_level is False
    assert catalog["callback-exception"].enforcement is EnforcementClass.ENFORCED
    assert catalog["non-returning-callback"].enforcement is EnforcementClass.LAST_RESORT
    os_limit = catalog["os-memory-security-confinement"]
    assert os_limit.enforcement is EnforcementClass.ADVISORY
    assert os_limit.os_level is False
    assert os_limit.gap_id == GAP_0054_ID
    assert os_limit.gap_status == GAP_0054_STATUS
    assert os_limit.closes_gap is False
    assert all(record.closes_gap is False for record in catalog.values())
    assert COMPENSATING_CONTROLS == (
        "ql-8-static-scan",
        "capability-starvation",
        "host-process-isolation",
        "callback-deadline",
        "memory-ceiling",
        "quarantine",
    )
    assert os_limit.compensating_controls == COMPENSATING_CONTROLS


def test_invented_os_hard_cap_and_gap_close_are_refused() -> None:
    invented = refuse_invented_os_hard_cap(given="8388608")
    assert is_refusal(invented)
    assert invented.category is RefusalCategory.POLICY_REJECTION
    assert invented.context["gap_status"] == "deferred"
    assert invented.context["gap_0054_closed"] is False
    seat = _seat()
    closed = _refusal(
        prove_v1_seat_containment(
            injection=ContainmentInjection.DEADLINE,
            seat=seat,
            instant=_instant(),
            stream=SeatTransitionStream(),
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,)),
            close_gap_0054=True,
        )
    )
    assert closed.category is RefusalCategory.POLICY_REJECTION
    assert "GAP-0054" in str(closed.context["reason"])
    cap = _refusal(
        prove_v1_seat_containment(
            injection=ContainmentInjection.DEADLINE,
            seat=seat,
            instant=_instant(),
            stream=SeatTransitionStream(),
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,)),
            os_hard_cap_bytes=8_388_608,
        )
    )
    assert cap.category is RefusalCategory.POLICY_REJECTION


def test_deadline_injection_cancels_quarantines_and_alarms() -> None:
    publisher, channel = _publisher()
    stream = SeatTransitionStream()
    seat = _seat()
    proof = _ok(
        prove_v1_seat_containment(
            injection=ContainmentInjection.DEADLINE,
            seat=seat,
            instant=_instant(),
            stream=stream,
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,)),
            alerts=publisher,
        )
    )
    assert proof.enforcement is EnforcementClass.ENFORCED
    assert proof.cancelled_cooperatively is True
    assert proof.quarantined is True
    assert proof.alarmed is True
    assert "protection-escalation" in proof.alarm_classes
    assert proof.last_resort_watchdog is False
    assert proof.os_level_confinement is False
    assert proof.gap_0054 == "deferred"
    assert proof.gap_0054_closed is False
    assert proof.trigger == QuarantineTrigger.DEADLINE_BREACH.value
    assert proof.exit == OPERATOR_SEAT_REINSTATE
    assert proof.stream_failure is False
    assert proof.node_restart_on_cooperative_breach is False
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED
    assert channel.delivered
    assert channel.delivered[0].failure_id == "FR-19"
    assert channel.delivered[0].alert_class == "protection-escalation"
    mapping = proof.as_mapping()
    assert mapping["enforcement"] == "enforced"
    assert mapping["v1_hardened_os_confinement"] is False


def test_cooperative_memory_probe_quarantines_as_enforced_not_os() -> None:
    publisher, channel = _publisher()
    stream = SeatTransitionStream()
    seat = _seat(memory_bytes=8)
    proof = _ok(
        prove_v1_seat_containment(
            injection=ContainmentInjection.COOPERATIVE_MEMORY_PROBE,
            seat=seat,
            instant=_instant(),
            stream=stream,
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(64,)),
            alerts=publisher,
        )
    )
    assert proof.limit_name == "memory-ceiling"
    assert proof.enforcement is EnforcementClass.ENFORCED
    assert proof.cancelled_cooperatively is True
    assert proof.quarantined is True
    assert proof.os_level_confinement is False
    assert proof.trigger == QuarantineTrigger.MEMORY_CEILING_BREACH.value
    assert proof.last_resort_supervised_restart is False
    assert channel.delivered[0].alert_class == "protection-escalation"


def test_callback_exception_quarantines_and_only_operator_reinstate_exits() -> None:
    def boom(evidence: object) -> object:
        del evidence
        raise RuntimeError("callback exploded")

    publisher, _channel = _publisher()
    stream = SeatTransitionStream()
    seat = _seat(factory=FunctionFactory(logic=boom))
    instant = _instant()
    proof = _ok(
        prove_v1_seat_containment(
            injection=ContainmentInjection.CALLBACK_EXCEPTION,
            seat=seat,
            instant=instant,
            stream=stream,
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0, 1), memory_bytes=(1, 1)),
            alerts=publisher,
        )
    )
    assert proof.enforcement is EnforcementClass.ENFORCED
    assert proof.cancelled_cooperatively is False
    assert proof.trigger == QuarantineTrigger.CALLBACK_EXCEPTION.value
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED
    ops = apply_operator_seat_reinstate(
        principal="ops",
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        transition_instant=instant,
        operator_signature="sig-ops",
        stream=stream,
    )
    assert is_refusal(ops)
    reinstated = _ok(
        apply_operator_seat_reinstate(
            principal=OPERATOR_PRINCIPAL,
            seat_id=seat.seat_id,
            binding_ref=seat.binding_ref,
            transition_instant=instant,
            operator_signature="sig-operator-1",
            stream=stream,
        )
    )
    assert reinstated.trigger == OPERATOR_SEAT_REINSTATE
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.ADMITTED


def test_non_returning_callback_uses_watchdog_last_resort_not_os_cap() -> None:
    publisher, channel = _publisher()
    stream = SeatTransitionStream()
    seat = _seat()
    supervisor = _supervisor()
    proof = _ok(
        prove_v1_seat_containment(
            injection=ContainmentInjection.NON_RETURNING_CALLBACK,
            seat=seat,
            instant=_instant(),
            stream=stream,
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,)),
            supervisor=supervisor,
            alerts=publisher,
        )
    )
    assert proof.enforcement is EnforcementClass.LAST_RESORT
    assert proof.cancelled_cooperatively is False
    assert proof.quarantined is True
    assert proof.last_resort_watchdog is True
    assert proof.last_resort_supervised_restart is True
    assert proof.os_level_confinement is False
    assert proof.restart_clears_quarantine is False
    assert proof.trigger == QuarantineTrigger.NON_RETURNING_CALLBACK.value
    assert "silent-degradation" in proof.alarm_classes
    assert "protection-escalation" in proof.alarm_classes
    assert supervisor.keepalive_enabled is False
    notify = supervisor.notify
    assert isinstance(notify, RecordingNotifyTransport)
    assert "WATCHDOG=trigger" in notify.messages
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED
    assert channel.delivered
    assert proof.as_mapping()["enforcement"] == "last-resort"


def test_operator_reinstate_clears_last_resort_quarantine() -> None:
    stream = SeatTransitionStream()
    seat = _seat()
    instant = _instant()
    _ok(
        prove_v1_seat_containment(
            injection=ContainmentInjection.NON_RETURNING_CALLBACK,
            seat=seat,
            instant=instant,
            stream=stream,
            cancel=CancelToken(),
            probe=ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,)),
            supervisor=_supervisor(),
        )
    )
    reinstated = _ok(
        apply_operator_seat_reinstate(
            principal=OPERATOR_PRINCIPAL,
            seat_id=seat.seat_id,
            binding_ref=seat.binding_ref,
            transition_instant=instant,
            operator_signature="sig-operator-last-resort",
            stream=stream,
        )
    )
    assert reinstated.to_state is GovernedSeatState.ADMITTED
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.ADMITTED


def test_production_src_does_not_invent_os_confinement_apis() -> None:
    hits = scan_os_confinement_apis()
    assert hits == ()


def test_release_and_security_docs_state_the_v1_limit_honestly() -> None:
    report = _ok(v1_containment_documentation_report(repo_root=_REPO))
    assert report.gap_0054_status == "deferred"
    assert report.gap_0054_closed is False
    assert report.missing_required == ()
    assert any(path.endswith("security-model.md") for path in report.documents)
    assert report.as_mapping()["gap_0054_closed"] is False
