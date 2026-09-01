"""QL-7 seat host: declared-footprint evidence, canonical assignment, containment.

A factory per seat is constructed with the declaration, the canonical assignment,
and injected read surfaces over the declared footprint only. The loop drives the
callback per evaluation instant through ``mint_intents``. Clock, Book, venue, and
signal-snapshot objects are never injected. Deadline and memory-ceiling values
are caller-supplied registry resolutions — never invented (FTR-07; TN-19).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmb.runloop import (
    CancelToken,
    LimitProbe,
    RestingIntent,
    SilentSliceHandler,
)
from qmf.core import (
    Clock,
    Duration,
    Instant,
    Ok,
    Result,
    TypedRefusal,
    fingerprint,
    is_refusal,
)
from qmf.core.exact import ExactRational
from qml.declaration.bot import BotDefinition
from qml.protocol import (
    FORBIDDEN_EVIDENCE_KEYS,
    HostedBot,
    construct_bot,
    resolve_assignment,
)
from qml.protocol.intents import BotIntent

from qmn.mis.signal_snapshot import SignalSnapshot
from qmn.seats._refuse import clean_token, invalid, policy
from qmn.seats.state import (
    OPERATOR_PRINCIPAL,
    OPERATOR_SEAT_REINSTATE,
    GovernedSeatState,
    QuarantineTrigger,
    SeatTransitionStream,
    fold_seat_state,
    mint_quarantine_transition,
)
from qmn.venue.port import VenueClientPort

__all__ = [
    "FORBIDDEN_SEAT_SURFACE_KEYS",
    "SEAT_CALLBACK_DEADLINE_REGISTRY_KEY",
    "SEAT_MEMORY_CEILING_REGISTRY_KEY",
    "GovernedSeat",
    "GovernedSeatHandler",
    "SeatContainment",
    "construct_governed_seat",
    "drive_governed_seat",
    "refuse_invented_seat_bounds",
]

SEAT_CALLBACK_DEADLINE_REGISTRY_KEY: Final[str] = "seat_callback_deadline"
SEAT_MEMORY_CEILING_REGISTRY_KEY: Final[str] = "seat_memory_ceiling"

FORBIDDEN_SEAT_SURFACE_KEYS: Final[frozenset[str]] = FORBIDDEN_EVIDENCE_KEYS | frozenset(
    {
        "venue",
        "venue_client",
        "venue_command",
        "signal_snapshot",
        "signal-snapshot",
        "mis_snapshot",
        "sqs",
    }
)


@dataclass(frozen=True, slots=True)
class SeatContainment:
    """Injected per-seat deadline and memory ceiling (registry-resolved, FTR-07)."""

    callback_deadline: Duration
    memory_ceiling_bytes: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "callback_deadline_ns": self.callback_deadline.value_ns,
                "memory_ceiling_bytes": self.memory_ceiling_bytes,
                "callback_deadline_key": SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
                "memory_ceiling_key": SEAT_MEMORY_CEILING_REGISTRY_KEY,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        callback_deadline: object,
        memory_ceiling_bytes: object,
    ) -> Result[SeatContainment]:
        """Admit caller-supplied bounds; refuse blanks and invented numbers."""
        if callback_deadline is None:
            return refuse_invented_seat_bounds(
                SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
                given="None",
            )
        if not isinstance(callback_deadline, Duration):
            return refuse_invented_seat_bounds(
                SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
                given=repr(callback_deadline),
            )
        if callback_deadline.value_ns <= 0:
            return invalid(
                SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
                "seat_callback_deadline is a positive Duration from the node-config "
                "artifact; a non-positive bound cannot contain a callback",
                given=callback_deadline.value_ns,
            )
        if memory_ceiling_bytes is None:
            return refuse_invented_seat_bounds(
                SEAT_MEMORY_CEILING_REGISTRY_KEY,
                given="None",
            )
        if (
            isinstance(memory_ceiling_bytes, bool)
            or not isinstance(memory_ceiling_bytes, int)
            or memory_ceiling_bytes <= 0
        ):
            return refuse_invented_seat_bounds(
                SEAT_MEMORY_CEILING_REGISTRY_KEY,
                given=repr(memory_ceiling_bytes),
            )
        return Ok(
            cls(
                callback_deadline=callback_deadline,
                memory_ceiling_bytes=memory_ceiling_bytes,
            )
        )


def refuse_invented_seat_bounds(field: object = "bounds", **extra: object) -> TypedRefusal:
    """FTR-07: the node never invents a seat deadline or memory ceiling."""
    token = clean_token(field) or "bounds"
    return policy(
        token,
        "seat_callback_deadline and seat_memory_ceiling are registry-resolved "
        "values on the node-config artifact; the node never invents a latency "
        "or memory number (FTR-07)",
        **extra,
    )


@dataclass(frozen=True, slots=True)
class GovernedSeat:
    """One QL-7 hosted seat at a Book binding (TN-19)."""

    seat_id: str
    binding_ref: str
    hosted: HostedBot
    containment: SeatContainment
    assignment_is_canonical: bool
    stream_id: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "seat_id": self.seat_id,
                "binding_ref": self.binding_ref,
                "assignment_is_canonical": self.assignment_is_canonical,
                "stream_id": self.stream_id,
                "containment": dict(self.containment.as_mapping()),
            }
        )


def construct_governed_seat(
    factory: object,
    *,
    seat_id: object,
    binding_ref: object,
    declaration: object,
    containment: object,
    assignment: object = None,
    read_surfaces: object = None,
    stream_id: object = None,
    clock: object = None,
    book: object = None,
    venue: object = None,
    signal_snapshot: object = None,
    protocol_format_version: object = None,
    state_scope: object = None,
    state_bound: object = None,
) -> Result[GovernedSeat]:
    """Construct a QL-7 seat over declared as-of evidence and the canonical assignment."""
    blocked = _refuse_host_objects(
        clock=clock,
        book=book,
        venue=venue,
        signal_snapshot=signal_snapshot,
    )
    if is_refusal(blocked):
        return blocked
    sid = clean_token(seat_id)
    if sid is None:
        return invalid("seat_id", "a governed seat names a non-empty seat id", given=repr(seat_id))
    binding = clean_token(binding_ref)
    if binding is None:
        return invalid(
            "binding_ref",
            "a governed seat sits at a non-empty Book binding reference",
            given=repr(binding_ref),
        )
    bounds = _as_containment(containment)
    if is_refusal(bounds):
        return bounds
    bot = _as_bot_definition(declaration)
    if is_refusal(bot):
        return bot
    definition = bot.value
    canonical = dict(definition.canonical_assignment())
    supplied = canonical if assignment is None else assignment
    resolved = resolve_assignment(definition, supplied)
    if is_refusal(resolved):
        return resolved
    if not _assignments_equal(resolved.value, canonical):
        return policy(
            "assignment",
            "governed live and paper seats execute the canonical assignment only; "
            "a tuned overlay is a B-3 experimentation override, never a node seat",
        )
    surfaces = _coerce_read_surfaces(read_surfaces)
    if is_refusal(surfaces):
        return surfaces
    kwargs: dict[str, object] = {
        "declaration": definition,
        "assignment": resolved.value,
        "read_surfaces": surfaces.value,
    }
    if protocol_format_version is not None:
        kwargs["protocol_format_version"] = protocol_format_version
    if state_scope is not None:
        kwargs["state_scope"] = state_scope
    if state_bound is not None:
        kwargs["state_bound"] = state_bound
    hosted = construct_bot(factory, **kwargs)
    if is_refusal(hosted):
        return hosted
    stream_token: str | None = None
    if stream_id is not None:
        stream_token = clean_token(stream_id)
        if stream_token is None:
            return invalid(
                "stream_id",
                "a seat stream id is a non-empty token when present",
                given=repr(stream_id),
            )
    return Ok(
        GovernedSeat(
            seat_id=sid,
            binding_ref=binding,
            hosted=hosted.value,
            containment=bounds.value,
            assignment_is_canonical=True,
            stream_id=stream_token,
        )
    )


def drive_governed_seat(
    seat: object,
    instant: object,
    *,
    stream: object,
    cancel: object,
    probe: object,
    transition_instant: object = None,
) -> Result[tuple[BotIntent, ...]]:
    """Drive one evaluation instant under deadline and memory-ceiling containment.

    A deadline breach, memory-ceiling breach, or raised exception is a typed
    refusal plus automatic quarantine. The command stream does not fail and the
    node does not restart. Leaving ``quarantined`` is operator ``seat_reinstate``.
    """
    if not isinstance(seat, GovernedSeat):
        return invalid(
            "seat",
            "the node drives a GovernedSeat constructed through the QL-7 factory",
            given=repr(type(seat).__name__),
        )
    if not isinstance(instant, Instant):
        return invalid(
            "instant",
            "the evaluation instant rides the callback; bots never read a clock",
            given=repr(instant),
        )
    if not isinstance(stream, SeatTransitionStream):
        return invalid(
            "stream",
            "seat drives journal containment breaches onto a SeatTransitionStream",
            given=repr(stream),
        )
    dated = instant if transition_instant is None else transition_instant
    if not isinstance(dated, Instant):
        return invalid(
            "transition_instant",
            "a seat-state transition is dated with an injected Instant",
            given=repr(transition_instant),
        )
    folded = fold_seat_state(stream, seat.seat_id)
    if is_refusal(folded):
        return folded
    current = folded.value
    if current is GovernedSeatState.QUARANTINED:
        return policy(
            "seat",
            "a quarantined seat emits no intents; only operator seat_reinstate exits",
            seat_id=seat.seat_id,
            exit=OPERATOR_SEAT_REINSTATE,
            principal=OPERATOR_PRINCIPAL,
            stream_failure=False,
            node_restart=False,
        )
    if not isinstance(cancel, CancelToken):
        return invalid(
            "cancel",
            "the slice driver enforces seat_callback_deadline through a CancelToken "
            "at slice boundaries",
            given=repr(type(cancel).__name__),
        )
    if not isinstance(probe, LimitProbe):
        return invalid(
            "probe",
            "seat_memory_ceiling and seat_callback_deadline are enforced by an "
            "injected LimitProbe; the node never reads an ambient meter (FTR-07)",
            given=repr(type(probe).__name__),
        )
    before = _evaluate_containment(seat.containment, cancel=cancel, probe=probe)
    if is_refusal(before):
        return before
    if before.value is not None:
        return _quarantine(
            seat,
            from_state=current,
            trigger=before.value,
            transition_instant=dated,
            stream=stream,
            breach_detail=before.value.value,
        )
    try:
        intents = seat.hosted.on_instant(instant)
    except Exception as exc:
        return _quarantine(
            seat,
            from_state=current,
            trigger=QuarantineTrigger.CALLBACK_EXCEPTION,
            transition_instant=dated,
            stream=stream,
            breach_detail=type(exc).__name__,
        )
    if is_refusal(intents):
        return intents
    after = _evaluate_containment(seat.containment, cancel=cancel, probe=probe)
    if is_refusal(after):
        return after
    if after.value is not None:
        return _quarantine(
            seat,
            from_state=current,
            trigger=after.value,
            transition_instant=dated,
            stream=stream,
            breach_detail=after.value.value,
        )
    return intents


@dataclass(frozen=True, slots=True)
class GovernedSeatHandler(SilentSliceHandler):
    """``mint_intents`` hook: drive one governed seat; quarantine is not a stream failure."""

    seat: GovernedSeat
    stream: SeatTransitionStream
    cancel: CancelToken
    probe: LimitProbe

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        expected = self.seat.stream_id
        if expected is not None and stream_id != expected:
            return Ok(())
        intents = drive_governed_seat(
            self.seat,
            frontier,
            stream=self.stream,
            cancel=self.cancel,
            probe=self.probe,
            transition_instant=frontier,
        )
        if is_refusal(intents):
            if intents.context.get("stream_failure") is False:
                return Ok(())
            return intents
        tokens = _to_resting(intents.value, stream_id)
        if is_refusal(tokens):
            return tokens
        return Ok(cast("object", tokens.value))


def _as_containment(value: object) -> Result[SeatContainment]:
    if isinstance(value, SeatContainment):
        return Ok(value)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        return SeatContainment.try_create(
            callback_deadline=mapping.get("callback_deadline"),
            memory_ceiling_bytes=mapping.get("memory_ceiling_bytes"),
        )
    return invalid(
        "containment",
        "a governed seat carries injected SeatContainment bounds; the host "
        "never invents seat_callback_deadline or seat_memory_ceiling (FTR-07)",
        given=repr(type(value).__name__),
    )


def _as_bot_definition(value: object) -> Result[BotDefinition]:
    if isinstance(value, BotDefinition):
        return Ok(value)
    return BotDefinition.try_from_mapping(value)


def _assignments_equal(
    resolved: Mapping[str, object],
    canonical: Mapping[str, object],
) -> bool:
    if set(resolved) != set(canonical):
        return False
    return all(_same_assigned(value, canonical[name]) for name, value in resolved.items())


def _same_assigned(left: object, right: object) -> bool:
    if isinstance(left, ExactRational) and isinstance(right, ExactRational):
        return left.fp1_identity() == right.fp1_identity()
    return left == right


def _refuse_host_objects(
    *,
    clock: object,
    book: object,
    venue: object,
    signal_snapshot: object,
) -> Result[None]:
    if clock is not None:
        return policy(
            "clock",
            "QL-7 seats never receive a clock object; the evaluation instant rides the callback",
        )
    if book is not None:
        return policy(
            "book",
            "QL-7 seats never receive a Book object; Book admission is a later door",
        )
    if venue is not None:
        return policy(
            "venue",
            "QL-7 seats never receive a venue object; venue commands are not a bot surface",
        )
    if signal_snapshot is not None:
        return policy(
            "signal_snapshot",
            "QL-7 seats never receive the signal snapshot; bots consume declared "
            "footprint evidence only",
        )
    return Ok(None)


def _coerce_read_surfaces(value: object) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return invalid(
            "read_surfaces",
            "hosts inject a mapping of declared-footprint key to ReadSurface",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, object] = {}
    for raw_key, surface in mapping.items():
        key = clean_token(raw_key)
        if key is None:
            return invalid(
                "read_surfaces",
                "read-surface keys are declared footprint tokens",
                given=repr(raw_key),
            )
        if key in FORBIDDEN_SEAT_SURFACE_KEYS:
            return policy(
                "read_surfaces",
                "hosts inject only declared as-of evidence; clock, Book, venue, "
                "and signal-snapshot objects are never injected",
                key=key,
            )
        kind = _forbidden_surface_kind(surface)
        if kind is not None:
            return policy(
                "read_surfaces",
                "hosts inject only declared as-of evidence; clock, Book, venue, "
                "and signal-snapshot objects are never injected",
                key=key,
                surface=kind,
            )
        resolved[key] = surface
    return Ok(MappingProxyType(resolved))


def _forbidden_surface_kind(surface: object) -> str | None:
    if isinstance(surface, Clock):
        return "clock"
    if isinstance(surface, VenueClientPort):
        return "venue"
    if isinstance(surface, SignalSnapshot):
        return "signal-snapshot"
    return None


def _evaluate_containment(
    containment: SeatContainment,
    *,
    cancel: CancelToken,
    probe: LimitProbe,
) -> Result[QuarantineTrigger | None]:
    if cancel.is_cancelled:
        if cancel.cause in {
            QuarantineTrigger.MEMORY_CEILING_BREACH.value,
            "memory-limit",
        }:
            return Ok(QuarantineTrigger.MEMORY_CEILING_BREACH)
        return Ok(QuarantineTrigger.DEADLINE_BREACH)
    elapsed = probe.elapsed()
    if isinstance(elapsed, TypedRefusal):
        return elapsed
    if elapsed.value.value_ns >= containment.callback_deadline.value_ns:
        return Ok(QuarantineTrigger.DEADLINE_BREACH)
    memory = probe.memory_bytes()
    if isinstance(memory, TypedRefusal):
        return memory
    observed = memory.value
    if isinstance(observed, bool) or observed < 0:
        return invalid(
            "probe",
            "LimitProbe.memory_bytes is a non-negative byte count",
            given=repr(observed),
        )
    if observed >= containment.memory_ceiling_bytes:
        return Ok(QuarantineTrigger.MEMORY_CEILING_BREACH)
    return Ok(None)


def _quarantine(
    seat: GovernedSeat,
    *,
    from_state: GovernedSeatState,
    trigger: QuarantineTrigger,
    transition_instant: Instant,
    stream: SeatTransitionStream,
    breach_detail: str,
) -> Result[tuple[BotIntent, ...]]:
    minted = mint_quarantine_transition(
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        from_state=from_state,
        trigger=trigger.value,
        transition_instant=transition_instant,
        breach_detail=breach_detail,
        stream=stream,
    )
    if is_refusal(minted):
        return minted
    return policy(
        "seat",
        "a seat-callback containment breach is a typed refusal plus automatic "
        "quarantine; it is never a stream failure and never a node restart",
        seat_id=seat.seat_id,
        trigger=trigger.value,
        exit=OPERATOR_SEAT_REINSTATE,
        principal=OPERATOR_PRINCIPAL,
        stream_failure=False,
        node_restart=False,
    )


def _to_resting(intents: object, stream_id: str) -> Result[tuple[RestingIntent, ...]]:
    if intents is None:
        return Ok(())
    if isinstance(intents, Mapping):
        return invalid(
            "intents",
            "QL-7 callbacks return zero-or-more CT-23 intents, never a mapping",
            given="mapping",
        )
    if isinstance(intents, (tuple, list)):
        sequence = tuple(cast("Sequence[object]", intents))
    else:
        sequence = (intents,)
    tokens: list[RestingIntent] = []
    for index, intent in enumerate(sequence):
        identity = getattr(intent, "fp1_identity", None)
        if not callable(identity):
            return invalid(
                "intents",
                "each QL-7 intent carries fp1 identity so resting tokens are deterministic",
                index=index,
                given=type(intent).__name__,
            )
        stamped = fingerprint(identity())
        if is_refusal(stamped):
            return stamped
        token = RestingIntent.try_create(f"{stamped.value.value}:{index}", stream_id)
        if is_refusal(token):
            return token
        tokens.append(token.value)
    return Ok(tuple(tokens))
