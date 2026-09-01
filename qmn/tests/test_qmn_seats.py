"""Story 26.8 — host governed QL-7 seats under deadline, memory, and quarantine."""

from __future__ import annotations

from typing import TypeVar

from qmb.runloop import CancelToken, ScriptedLimitProbe
from qmf.core import (
    DataDrivenClock,
    Duration,
    Instant,
    RefusalCategory,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.refusal import Result
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import FunctionFactory, MappingReadSurface, PresenceState
from qmn.seats import (
    FORBIDDEN_SEAT_SURFACE_KEYS,
    OPERATOR_PRINCIPAL,
    OPERATOR_SEAT_REINSTATE,
    QUARANTINE_TRIGGERS,
    SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
    SEAT_MEMORY_CEILING_REGISTRY_KEY,
    SEATS_SURFACE,
    GovernedSeat,
    GovernedSeatHandler,
    GovernedSeatState,
    QuarantineTrigger,
    SeatContainment,
    SeatTransitionStream,
    apply_operator_seat_reinstate,
    construct_governed_seat,
    drive_governed_seat,
    fold_seat_state,
    mint_seat_reinstate,
    refuse_invented_seat_bounds,
)

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


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


def _declaration() -> BotDefinition:
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


def _present_series(instant: Instant, value: int = 1) -> dict[str, object]:
    return {
        "kind": "series",
        "samples": [
            {
                "presence": PresenceState.PRESENT.value,
                "knowable_at": instant,
                "value": value,
            }
        ],
    }


def _surface(instant: Instant, payload: object) -> MappingReadSurface:
    return _ok(MappingReadSurface.try_create({instant: payload}))


def _containment(
    *,
    deadline_ns: int = 1_000_000_000,
    memory_bytes: int = 10_000_000,
) -> SeatContainment:
    return _ok(
        SeatContainment.try_create(
            callback_deadline=_duration(deadline_ns),
            memory_ceiling_bytes=memory_bytes,
        )
    )


def _silent_factory() -> FunctionFactory:
    return FunctionFactory(logic=lambda evidence: ())


def _seat(
    *,
    factory: FunctionFactory | None = None,
    assignment: object = None,
    read_surfaces: object = None,
    containment: SeatContainment | None = None,
    stream_id: str = "stream-eurusd",
    clock: object = None,
    book: object = None,
    venue: object = None,
    signal_snapshot: object = None,
) -> Result[GovernedSeat]:
    return construct_governed_seat(
        factory if factory is not None else _silent_factory(),
        seat_id="seat-alpha",
        binding_ref="binding-live-1",
        declaration=_declaration(),
        containment=containment if containment is not None else _containment(),
        assignment=assignment,
        read_surfaces=read_surfaces if read_surfaces is not None else {},
        stream_id=stream_id,
        clock=clock,
        book=book,
        venue=venue,
        signal_snapshot=signal_snapshot,
    )


def _drive(
    seat: GovernedSeat,
    instant: Instant,
    *,
    stream: SeatTransitionStream | None = None,
    cancel: CancelToken | None = None,
    probe: ScriptedLimitProbe | None = None,
):
    return drive_governed_seat(
        seat,
        instant,
        stream=stream if stream is not None else SeatTransitionStream(),
        cancel=cancel if cancel is not None else CancelToken(),
        probe=probe
        if probe is not None
        else ScriptedLimitProbe(elapsed_ns=(0, 1), memory_bytes=(1, 1)),
    )


# --- surface / bounds --------------------------------------------------------


def test_seats_surface_and_registry_keys() -> None:
    assert SEATS_SURFACE == "qmn.seats"
    assert SEAT_CALLBACK_DEADLINE_REGISTRY_KEY == "seat_callback_deadline"
    assert SEAT_MEMORY_CEILING_REGISTRY_KEY == "seat_memory_ceiling"
    assert "clock" in FORBIDDEN_SEAT_SURFACE_KEYS
    assert "book" in FORBIDDEN_SEAT_SURFACE_KEYS
    assert "venue" in FORBIDDEN_SEAT_SURFACE_KEYS
    assert "signal_snapshot" in FORBIDDEN_SEAT_SURFACE_KEYS
    assert (
        frozenset(
            {
                QuarantineTrigger.DEADLINE_BREACH.value,
                QuarantineTrigger.MEMORY_CEILING_BREACH.value,
                QuarantineTrigger.CALLBACK_EXCEPTION.value,
            }
        )
        == QUARANTINE_TRIGGERS
    )


def test_containment_refuses_invented_deadline_and_memory() -> None:
    none_deadline = SeatContainment.try_create(
        callback_deadline=None,
        memory_ceiling_bytes=10_000_000,
    )
    assert is_refusal(none_deadline)
    assert none_deadline.category is RefusalCategory.POLICY_REJECTION
    invented_ns = SeatContainment.try_create(
        callback_deadline=15,
        memory_ceiling_bytes=10_000_000,
    )
    assert is_refusal(invented_ns)
    none_memory = SeatContainment.try_create(
        callback_deadline=_duration(1_000_000),
        memory_ceiling_bytes=None,
    )
    assert is_refusal(none_memory)
    zero_memory = SeatContainment.try_create(
        callback_deadline=_duration(1_000_000),
        memory_ceiling_bytes=0,
    )
    assert is_refusal(zero_memory)
    invented = refuse_invented_seat_bounds()
    assert is_refusal(invented)
    assert invented.category is RefusalCategory.POLICY_REJECTION


# --- construct: canonical assignment and forbidden objects -------------------


def test_construct_uses_canonical_assignment_and_declared_evidence() -> None:
    instant = _instant()
    seat = _ok(
        _seat(
            assignment={"lookback": 20},
            read_surfaces={"primary": _surface(instant, _present_series(instant))},
        )
    )
    assert isinstance(seat, GovernedSeat)
    assert seat.assignment_is_canonical is True
    assert seat.hosted.assignment["lookback"] == 20
    intents = _ok(_drive(seat, instant))
    assert intents == ()


def test_omitted_assignment_is_the_canonical_defaults() -> None:
    seat = _ok(_seat(assignment=None))
    assert seat.assignment_is_canonical is True
    assert seat.hosted.assignment["lookback"] == 20


def test_non_canonical_assignment_is_refused() -> None:
    refused = _seat(assignment={"lookback": 21})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "canonical assignment" in str(refused.context["reason"])


def test_clock_book_venue_and_signal_snapshot_objects_are_refused() -> None:
    instant = _instant()
    clock = DataDrivenClock(boot_epoch_id="boot", wall_instants=(instant,), monotonic_ns=(0,))
    clocked = _seat(clock=clock)
    assert is_refusal(clocked)
    assert clocked.category is RefusalCategory.POLICY_REJECTION
    booked = _seat(book=object())
    assert is_refusal(booked)
    venued = _seat(venue=object())
    assert is_refusal(venued)
    snapped = _seat(signal_snapshot=object())
    assert is_refusal(snapped)
    surface_clock = _seat(read_surfaces={"primary": clock})
    assert is_refusal(surface_clock)
    named = _seat(
        read_surfaces={"signal_snapshot": _surface(instant, _present_series(instant))},
    )
    assert is_refusal(named)


def test_undeclared_surface_key_is_refused_by_the_protocol() -> None:
    instant = _instant()
    extra = _seat(
        read_surfaces={"ghost": _surface(instant, _present_series(instant))},
    )
    assert is_refusal(extra)
    assert extra.category is RefusalCategory.INVALID_INPUT


# --- drive: as-of evidence, containment, quarantine --------------------------


def test_look_ahead_evidence_is_refused_without_quarantine() -> None:
    evaluation = _instant(_NS)
    future = _instant(_NS + 1)
    seat = _ok(_seat(read_surfaces={"primary": _surface(evaluation, _present_series(future))}))
    stream = SeatTransitionStream()
    refused = _drive(seat, evaluation, stream=stream)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    state = _ok(fold_seat_state(stream, seat.seat_id))
    assert state is GovernedSeatState.ADMITTED


def test_deadline_breach_quarantines_and_is_not_a_stream_failure() -> None:
    instant = _instant()
    seat = _ok(_seat(containment=_containment(deadline_ns=10, memory_bytes=10_000)))
    stream = SeatTransitionStream()
    probe = ScriptedLimitProbe(elapsed_ns=(50,), memory_bytes=(1,))
    refused = _drive(seat, instant, stream=stream, probe=probe)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["trigger"] == QuarantineTrigger.DEADLINE_BREACH.value
    assert refused.context["stream_failure"] is False
    assert refused.context["node_restart"] is False
    state = _ok(fold_seat_state(stream, seat.seat_id))
    assert state is GovernedSeatState.QUARANTINED


def test_memory_ceiling_breach_quarantines() -> None:
    instant = _instant()
    seat = _ok(_seat(containment=_containment(deadline_ns=1_000_000, memory_bytes=8)))
    stream = SeatTransitionStream()
    probe = ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(64,))
    refused = _drive(seat, instant, stream=stream, probe=probe)
    assert is_refusal(refused)
    assert refused.context["trigger"] == QuarantineTrigger.MEMORY_CEILING_BREACH.value
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED


def test_callback_exception_quarantines() -> None:
    def boom(evidence: object) -> object:
        del evidence
        raise RuntimeError("callback exploded")

    instant = _instant()
    seat = _ok(_seat(factory=FunctionFactory(logic=boom)))
    stream = SeatTransitionStream()
    refused = _drive(seat, instant, stream=stream)
    assert is_refusal(refused)
    assert refused.context["trigger"] == QuarantineTrigger.CALLBACK_EXCEPTION.value
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED


def test_cancel_token_deadline_quarantines_before_callback() -> None:
    seen = {"called": False}

    def logic(evidence: object) -> object:
        del evidence
        seen["called"] = True
        return ()

    instant = _instant()
    seat = _ok(_seat(factory=FunctionFactory(logic=logic)))
    stream = SeatTransitionStream()
    cancel = CancelToken()
    _ok(cancel.cancel("deadline-breach"))
    refused = _drive(seat, instant, stream=stream, cancel=cancel)
    assert is_refusal(refused)
    assert seen["called"] is False
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED


def test_quarantined_seat_emits_no_intents_until_operator_reinstate() -> None:
    instant = _instant()
    seat = _ok(_seat(containment=_containment(deadline_ns=10, memory_bytes=10_000)))
    stream = SeatTransitionStream()
    probe = ScriptedLimitProbe(elapsed_ns=(50,), memory_bytes=(1,))
    _refusal(_drive(seat, instant, stream=stream, probe=probe))
    again = _drive(
        seat,
        instant,
        stream=stream,
        probe=ScriptedLimitProbe(elapsed_ns=(0, 1), memory_bytes=(1, 1)),
    )
    assert is_refusal(again)
    assert again.context["exit"] == OPERATOR_SEAT_REINSTATE
    ops = apply_operator_seat_reinstate(
        principal="ops",
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        transition_instant=instant,
        operator_signature="sig-ops",
        stream=stream,
    )
    assert is_refusal(ops)
    restart = mint_seat_reinstate(
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        transition_instant=instant,
        operator_signature="sig-restart",
        stream=stream,
        infer_from_restart=True,
    )
    assert is_refusal(restart)
    unsigned = mint_seat_reinstate(
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        transition_instant=instant,
        operator_signature=None,
        stream=stream,
    )
    assert is_refusal(unsigned)
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
    assert reinstated.to_state is GovernedSeatState.ADMITTED
    assert reinstated.trigger == OPERATOR_SEAT_REINSTATE
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.ADMITTED
    recovered = _ok(
        _drive(
            seat,
            instant,
            stream=stream,
            probe=ScriptedLimitProbe(elapsed_ns=(0, 1), memory_bytes=(1, 1)),
        )
    )
    assert recovered == ()


def test_reinstate_is_never_inferred_from_boot_config_or_silence() -> None:
    instant = _instant()
    for flag in (
        "infer_from_boot_epoch",
        "infer_from_config_version",
        "infer_from_absence_of_breaches",
    ):
        refused = mint_seat_reinstate(
            seat_id="seat-alpha",
            binding_ref="binding-live-1",
            transition_instant=instant,
            operator_signature="sig-operator-1",
            **{flag: True},
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION


def test_handler_quarantine_is_not_a_stream_failure() -> None:
    instant = _instant()
    seat = _ok(
        _seat(
            containment=_containment(deadline_ns=10, memory_bytes=10_000),
            stream_id="stream-eurusd",
        )
    )
    stream = SeatTransitionStream()
    handler = GovernedSeatHandler(
        seat=seat,
        stream=stream,
        cancel=CancelToken(),
        probe=ScriptedLimitProbe(elapsed_ns=(50,), memory_bytes=(1,)),
    )
    minted = handler.mint_intents("stream-eurusd", instant)
    assert is_ok(minted)
    assert minted.value == ()
    assert _ok(fold_seat_state(stream, seat.seat_id)) is GovernedSeatState.QUARANTINED
    other = handler.mint_intents("other-stream", instant)
    assert is_ok(other)
    assert other.value == ()
