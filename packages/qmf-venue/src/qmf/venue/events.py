"""Record-before-interpret events and on-demand reconciliation (Story 8.6; CT-20).

`COMP-QMF-VENUE` defines the venue-neutral **event and reconciliation contract** on
qmf-core nouns: every inbound venue event is stored verbatim and journaled **before any
interpretation**, order state is derived as a **read-time fold** over that observation
stream (never a stored field), and reconciliation is an **on-demand read-back** whose
verdict gates the command pipe only — the sensing pipe never blocks on it (CT-20;
DEC-0137, DEC-0138, DEC-0140, DEC-0148, DEC-0158).

The law this module encodes:

* **Recording precedes interpretation** (:class:`InboundVenueEvent`, :class:`EventRecorder`).
  Every inbound event is stored verbatim — with the mandatory receive wall time
  (:class:`~qmf.core.Instant`) and boot-scoped monotonic stamp
  (:class:`~qmf.core.MonotonicReading`) — and journaled before any state evaluation; no
  state machine ever gates the immutable store (AR-47; DEC-0137, DEC-0138). A fill
  observation's price, quantity, and venue instant, plus the mandatory receive instant,
  are **never null on a fill** — the mandatory identity fields of a fill (DEC-0137).
* **The order-state machine is a read-time fold** (:func:`fold_order_state`,
  :class:`OrderStateProjection`). Order state is derived at read time over the
  observation stream and is **never a stored field**; the command-outcome stream and the
  order-state stream are **separate**, and a terminal state is decided **only** by fills
  and venue lifecycle events — never inferred from a command outcome or from absence
  alone (CT-20; DEC-0137, DEC-0140).
* **An observation with no legal transition is out-of-sequence** (:class:`OutOfSequenceEdge`,
  :func:`is_legal_transition`, :func:`detect_out_of_sequence`). It is recorded verbatim,
  annotated with a typed out-of-sequence edge, and forces its owning command to
  ``UNKNOWN``; adapters **never synthesize** a venue observation to paper over the gap —
  a derived state is a fold result, never a stored event (FM-5; DEC-0137).
* **A multi-room write is one ordered unit** (:class:`MultiRoomWrite`,
  :class:`MultiRoomWriteResult`, :class:`TransactionBoundary`). The raw archive, the
  journal, and the registry room complete as one ordered unit with a named transaction
  boundary (``atomic`` or ``ordered-with-recovery``); a partial write is a
  ``storage failure`` refusal that **blocks the command stream** and is journaled on
  recovery (FM-2; DEC-0138, DEC-0140).
* **Reconciliation is an on-demand read-back** (:class:`ReconciliationReadback`,
  :class:`Reconciliation`, :class:`ReconciliationVerdict`) over a **mandatory declared
  lookback** — a do-not-default CT-18 adapter parameter. Its verdict is one of
  ``reconciled | drift | unknown | out-of-lookback`` — the fourth so "I cannot see that
  far back" is never read as "the position closed" — and it gates the command pipe only,
  never the sensing pipe; a standing protection intent re-evaluates **only** against a
  ``reconciled`` verdict (FR-024, SCN-0005; DEC-0137, DEC-0150, DEC-0158).
* **Subject-terminal read-back resolution** (:func:`resolve_subject_terminal`,
  :class:`SubjectResolution`). A ``close_position``, ``close_all``, or ``amend_protection``
  whose subject is observed terminal at or after the submit stamp resolves
  ``rejected-by-venue (superseded-by-terminal-subject)`` — a **named outcome**, never
  ``UNKNOWN``, never a stream block — and a subject absent or already terminal at
  submission resolves **without submission** (CT-20; DEC-0148, DEC-0158).

This module holds the **shape and the law**, never a broker fact or a policy value: the
reconciliation lookback is a declared, application-injected parameter under
do-not-default, and no retry/pool/throttle constant lives here. It reads no clock — every
instant and monotonic reading is injected at the composition root (AR-16). It imports
only ``qmf-core`` and the sibling command/connection modules; nothing imports
``qmf-venue`` (default-deny, L30/DEC-0120). No binary float touches the money path
(DEC-0105). Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from fractions import Fraction
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Duration,
    Fingerprint,
    Instant,
    MonotonicReading,
    Ok,
    Price,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SinkResult,
    TypedRefusal,
    fingerprint,
    is_refusal,
    is_unpersistable,
    unpersistable,
)
from qmf.venue.commands import Command, CommandKind, SubmissionOutcome
from qmf.venue.connection import ConnectionManager

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "EventRecorder",
    "InboundVenueEvent",
    "MultiRoomWrite",
    "MultiRoomWriteResult",
    "ObservationJournalEvent",
    "ObservationKind",
    "OrderState",
    "OrderStateProjection",
    "OutOfSequenceEdge",
    "PartialWriteRecovery",
    "Reconciliation",
    "ReconciliationReadback",
    "ReconciliationVerdict",
    "SubjectResolution",
    "SubjectTerminalOutcome",
    "TransactionBoundary",
    "VenueNativeIdentity",
    "WriteRoom",
    "detect_out_of_sequence",
    "fold_order_state",
    "is_legal_transition",
    "observation_journal_event_type",
    "resolve_subject_terminal",
]

# Every serialized CT-20 artifact stamps this integer contract format version; its
# meaning never mutates — an incompatible change mints the next version (DEC-0103;
# versioning-from-birth L15). CT-20 is at format version 1.
CONTRACT_FORMAT_VERSION: Final[int] = 1

_EnumT = TypeVar("_EnumT", bound=StrEnum)


# --- CT-20 vocabulary -------------------------------------------------------


class ObservationKind(StrEnum):
    """The venue lifecycle event driving the read-time fold (CT-20; DEC-0137, DEC-0140).

    ``OUT_OF_SEQUENCE`` is the **derived annotation** an observation with no legal
    transition carries; it is never a *raw* inbound kind (an adapter records the real
    kind and annotates, it never synthesizes a venue observation). Each kind maps to
    exactly one journal event type under the cardinality law.
    """

    SUBMISSION_ACKNOWLEDGEMENT = "submission-acknowledgement"
    FILL = "fill"
    CANCEL_ACKNOWLEDGEMENT = "cancel-acknowledgement"
    EXPIRY = "expiry"
    CLOSE_BY_VENUE = "close-by-venue"
    OUT_OF_SEQUENCE = "out-of-sequence"


class OrderState(StrEnum):
    """The read-time fold's order state — **never a stored field** (CT-20; DEC-0137).

    The prefix states ``CLIENT_SUBMITTED``, ``VENUE_ACCEPTED``, ``VENUE_REJECTED``, and
    ``UNKNOWN`` are the fold's projection of the command-outcome stream and are **never
    the order's terminal state**. The terminal states ``FILLED``, ``CANCELLED``,
    ``EXPIRED``, and ``CLOSED_BY_VENUE`` are decided **only** by fills and venue lifecycle
    events — never inferred from a command outcome or from absence alone (DEC-0137,
    DEC-0140).
    """

    CLIENT_SUBMITTED = "client-submitted"
    VENUE_ACCEPTED = "venue-accepted"
    VENUE_REJECTED = "venue-rejected"
    UNKNOWN = "UNKNOWN"
    PARTIALLY_FILLED = "partially-filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    CLOSED_BY_VENUE = "closed-by-venue"


class TransactionBoundary(StrEnum):
    """The named transaction boundary of one multi-room write (CT-20; DEC-0138)."""

    ATOMIC = "atomic"
    ORDERED_WITH_RECOVERY = "ordered-with-recovery"


class WriteRoom(StrEnum):
    """The three rooms of one CT-20 multi-room write, in ordered-unit order (DEC-0138)."""

    RAW_ARCHIVE = "raw-archive"
    JOURNAL = "journal"
    REGISTRY_ROOM = "registry-room"


class ReconciliationVerdict(StrEnum):
    """The QMF-owned reconciliation verdict vocabulary (CT-20; DEC-0137, DEC-0158).

    ``OUT_OF_LOOKBACK`` is the fourth term, added so that "I cannot see that far back" is
    **never read as "the position closed"**: a standing protection intent re-evaluates
    only against ``RECONCILED``, while ``DRIFT``, ``UNKNOWN``, and ``OUT_OF_LOOKBACK``
    alarm and hold the intent open without dispatching (DEC-0150, DEC-0158).
    """

    RECONCILED = "reconciled"
    DRIFT = "drift"
    UNKNOWN = "unknown"
    OUT_OF_LOOKBACK = "out-of-lookback"


class SubjectResolution(StrEnum):
    """The subject-terminal read-back resolution outcome (CT-20; DEC-0148, DEC-0158).

    ``SUPERSEDED_BY_TERMINAL_SUBJECT`` — the subject was observed terminal at or after the
    submit stamp; the command resolves ``rejected-by-venue``, a **named outcome**, never
    ``UNKNOWN``, never a stream block. ``RESOLVE_WITHOUT_SUBMISSION`` — the subject is
    absent or already terminal at submission, so the command resolves without ever being
    submitted (never a naked close). ``PROCEED`` — the subject is live; the command
    dispatches normally.
    """

    SUPERSEDED_BY_TERMINAL_SUBJECT = "superseded-by-terminal-subject"
    RESOLVE_WITHOUT_SUBMISSION = "resolve-without-submission"
    PROCEED = "proceed"


# The order-lifecycle terminal states — decided ONLY by fills and venue lifecycle events.
# ``VENUE_REJECTED`` is deliberately excluded: it is a command-outcome projection, never
# an order-lifecycle terminal (DEC-0137).
_TERMINAL_STATES: Final[frozenset[OrderState]] = frozenset(
    {
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.EXPIRED,
        OrderState.CLOSED_BY_VENUE,
    }
)

# The fold's projection of a submitted command's outcome onto its order-state prefix. A
# ``None`` outcome (submitted, no outcome yet) projects to ``CLIENT_SUBMITTED``;
# ``denied-locally`` and ``partially-executed`` have no venue order and never project here.
_PREFIX_PROJECTION: Final[Mapping[SubmissionOutcome, OrderState]] = MappingProxyType(
    {
        SubmissionOutcome.ACCEPTED_BY_VENUE: OrderState.VENUE_ACCEPTED,
        SubmissionOutcome.REJECTED_BY_VENUE: OrderState.VENUE_REJECTED,
        SubmissionOutcome.UNKNOWN: OrderState.UNKNOWN,
    }
)

# The legal prior order states for each recorded observation kind. An observation whose
# kind is illegal from the running fold state has no legal transition and is out-of-sequence
# (DEC-0137). ``OUT_OF_SEQUENCE`` is never legal — it IS the annotation.
_LEGAL_PRIOR: Final[Mapping[ObservationKind, frozenset[OrderState]]] = MappingProxyType(
    {
        ObservationKind.SUBMISSION_ACKNOWLEDGEMENT: frozenset(
            {OrderState.CLIENT_SUBMITTED, OrderState.UNKNOWN}
        ),
        ObservationKind.FILL: frozenset(
            {
                OrderState.CLIENT_SUBMITTED,
                OrderState.VENUE_ACCEPTED,
                OrderState.PARTIALLY_FILLED,
                OrderState.UNKNOWN,
            }
        ),
        ObservationKind.CANCEL_ACKNOWLEDGEMENT: frozenset(
            {
                OrderState.CLIENT_SUBMITTED,
                OrderState.VENUE_ACCEPTED,
                OrderState.PARTIALLY_FILLED,
                OrderState.UNKNOWN,
            }
        ),
        ObservationKind.EXPIRY: frozenset(
            {
                OrderState.CLIENT_SUBMITTED,
                OrderState.VENUE_ACCEPTED,
                OrderState.PARTIALLY_FILLED,
                OrderState.UNKNOWN,
            }
        ),
        ObservationKind.CLOSE_BY_VENUE: frozenset(
            {
                OrderState.CLIENT_SUBMITTED,
                OrderState.VENUE_ACCEPTED,
                OrderState.PARTIALLY_FILLED,
                OrderState.FILLED,
                OrderState.UNKNOWN,
            }
        ),
    }
)

# The observation kinds that terminate a subject (a close/amend subject read by the
# subject-terminal resolution): a fill (the protective stop filled), a cancel, an expiry,
# or a close-by-venue (DEC-0148, DEC-0158).
_SUBJECT_TERMINAL_KINDS: Final[frozenset[ObservationKind]] = frozenset(
    {
        ObservationKind.FILL,
        ObservationKind.CANCEL_ACKNOWLEDGEMENT,
        ObservationKind.EXPIRY,
        ObservationKind.CLOSE_BY_VENUE,
    }
)

# The command kinds whose subject can terminate independently, so they carry a subject
# reference the read-back resolution reads (DEC-0148, DEC-0158).
_SUBJECT_COMMANDS: Final[frozenset[CommandKind]] = frozenset(
    {
        CommandKind.CLOSE_POSITION,
        CommandKind.CLOSE_ALL,
        CommandKind.AMEND_PROTECTION,
    }
)


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a malformed observation or read returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


def _coerce(enum_cls: type[_EnumT], value: object) -> _EnumT | None:
    """Return the enum member ``value`` names, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _as_revision(value: object) -> int | None:
    """Return ``value`` as a non-negative ``int`` revision, or ``None``.

    A ``bool`` (an int subclass) is rejected — a revision is an integer count, never a
    truth value.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, int) or value < 0:
        return None
    return value


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    Mirrors qmf-core's idiom: a mapping becomes a :class:`~types.MappingProxyType` over
    deep-frozen values and a list/tuple becomes a tuple, so a verbatim payload the caller
    keeps a reference to can never be mutated through a stored, frozen observation.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


# --- the venue-native identity key ------------------------------------------


@dataclass(frozen=True, slots=True)
class VenueNativeIdentity:
    """The declared ``(source, source-native id, revision)`` identity key (CT-20).

    The key gap-replay redelivery deduplicates under: every observation carries one, so a
    redelivered event resolves to one identity. Receive stamps, monotonic values, epochs,
    and ``correlation_id`` are occurrence/display-only and never enter identity content
    (DEC-0137, DEC-0138).
    """

    source: str
    source_native_id: str
    revision: int

    @classmethod
    def try_create(
        cls, source: object, source_native_id: object, revision: object
    ) -> Result[VenueNativeIdentity]:
        """Validate and build a :class:`VenueNativeIdentity`, returning value-or-refusal."""
        resolved_source = _clean_str(source)
        if resolved_source is None:
            return _invalid(
                "source", "a venue-native identity names its source", given=repr(source)
            )
        native_id = _clean_str(source_native_id)
        if native_id is None:
            return _invalid(
                "source_native_id",
                "a venue-native identity carries the source's own native id",
                given=repr(source_native_id),
            )
        resolved_revision = _as_revision(revision)
        if resolved_revision is None:
            return _invalid(
                "revision",
                "a venue-native identity carries a non-negative integer revision",
                given=repr(revision),
            )
        return Ok(
            cls(
                source=resolved_source,
                source_native_id=native_id,
                revision=resolved_revision,
            )
        )

    def fp1_identity(self) -> Mapping[str, object]:
        """The key's canonical fp1 identity content (CT-20; DEC-0108)."""
        return {
            "class": "venue-native-identity",
            "source": self.source,
            "source_native_id": self.source_native_id,
            "revision": self.revision,
        }


# --- the out-of-sequence edge -----------------------------------------------


@dataclass(frozen=True, slots=True)
class OutOfSequenceEdge:
    """The typed annotation on an observation with no legal transition (CT-20; DEC-0137).

    An observation whose kind has no legal transition from the current fold state is
    recorded verbatim and annotated with this edge, which forces its owning command to
    ``UNKNOWN`` pending resolution. It is a derived annotation, never a synthesized
    observation.
    """

    attempted_kind: ObservationKind
    prior_state: OrderState
    reason: str

    @classmethod
    def try_create(
        cls, attempted_kind: object, prior_state: object, reason: object
    ) -> Result[OutOfSequenceEdge]:
        """Validate and build an :class:`OutOfSequenceEdge`, returning value-or-refusal."""
        kind = _coerce(ObservationKind, attempted_kind)
        if kind is None:
            return _invalid(
                "attempted_kind",
                "an out-of-sequence edge names the observation kind that had no legal transition",
                given=repr(attempted_kind),
                allowed=[member.value for member in ObservationKind],
            )
        state = _coerce(OrderState, prior_state)
        if state is None:
            return _invalid(
                "prior_state",
                "an out-of-sequence edge names the fold state the illegal transition came from",
                given=repr(prior_state),
                allowed=[member.value for member in OrderState],
            )
        detail = _clean_str(reason)
        if detail is None:
            return _invalid(
                "reason", "an out-of-sequence edge carries a non-empty reason", given=repr(reason)
            )
        return Ok(cls(attempted_kind=kind, prior_state=state, reason=detail))


# --- the verbatim inbound observation ---------------------------------------


@dataclass(frozen=True, slots=True)
class InboundVenueEvent:
    """One inbound venue event, stored verbatim before any interpretation (CT-20).

    Recording precedes interpretation: the ``raw_payload`` is stored verbatim, and the
    mandatory ``receive_wall_time`` (:class:`~qmf.core.Instant`) and ``monotonic_stamp``
    (:class:`~qmf.core.MonotonicReading`, a boot-scoped diagnostic) ride every inbound
    event — a latency rung is a monotonic delta within one boot epoch, and a wall-computed
    rung is refused as a baseline (DEC-0138). The order state is **never** a field here —
    it is a read-time fold result (:func:`fold_order_state`), never a stored event.

    A ``fill`` observation's ``fill_price``, ``fill_quantity``, and ``venue_instant`` — plus
    the mandatory ``receive_wall_time`` — are the mandatory identity fields of a fill and
    are never null on a fill (DEC-0137). Of them, the fill price, fill quantity, and venue
    instant enter fp1 identity content; the receive stamp, monotonic stamp, session epoch,
    ``correlation_id``, and the derived out-of-sequence edge are occurrence/display-only and
    stay on the exclusion list, so a redelivery deduplicates on the venue-native identity
    key regardless of receipt provenance or annotation (DEC-0137, DEC-0138).
    """

    observation_kind: ObservationKind
    venue_native_identity: VenueNativeIdentity
    receive_wall_time: Instant
    monotonic_stamp: MonotonicReading
    session_epoch: str
    raw_payload: Mapping[str, object]
    fill_price: Price | None = None
    fill_quantity: Quantity | None = None
    venue_instant: Instant | None = None
    subject_native_id: str | None = None
    correlation_id: str | None = None
    out_of_sequence: OutOfSequenceEdge | None = None

    def __post_init__(self) -> None:
        # Deep-snapshot the verbatim payload so a later mutation of the caller's dict can
        # never reach back into this frozen, recorded-verbatim observation.
        object.__setattr__(self, "raw_payload", _deep_freeze(self.raw_payload))

    @property
    def is_fill(self) -> bool:
        """Whether this observation is a fill (its identity fields are mandatory)."""
        return self.observation_kind is ObservationKind.FILL

    @property
    def effective_journal_kind(self) -> ObservationKind:
        """The kind that drives the journal-event mapping: ``out-of-sequence`` when the
        observation is annotated with the edge, else its recorded kind (DEC-0137)."""
        if self.out_of_sequence is not None:
            return ObservationKind.OUT_OF_SEQUENCE
        return self.observation_kind

    @property
    def subject_instant(self) -> Instant:
        """The instant the subject-terminal resolution compares against the submit stamp —
        the venue instant when present, else the mandatory receive wall time (DEC-0158)."""
        return self.venue_instant if self.venue_instant is not None else self.receive_wall_time

    @classmethod
    def try_create(
        cls,
        observation_kind: object,
        venue_native_identity: object,
        receive_wall_time: object,
        monotonic_stamp: object,
        session_epoch: object,
        raw_payload: object,
        *,
        fill_price: object = None,
        fill_quantity: object = None,
        venue_instant: object = None,
        subject_native_id: object = None,
        correlation_id: object = None,
    ) -> Result[InboundVenueEvent]:
        """Validate and build an :class:`InboundVenueEvent`, returning value-or-refusal.

        Recording is mandatory-stamped: a non-:class:`~qmf.core.Instant` receive time or a
        non-:class:`~qmf.core.MonotonicReading` monotonic stamp is refused (both are
        mandatory on every inbound event; DEC-0138). ``out-of-sequence`` is a derived
        annotation applied with :meth:`with_out_of_sequence`, never a raw inbound kind — an
        adapter records the real kind and annotates, it never synthesizes a venue
        observation. A ``fill`` requires its mandatory identity fields (price, quantity,
        venue instant), and a non-fill carries no fill price or quantity (a
        kind-inappropriate field is omitted, never a null; DEC-0137).
        """
        kind = _coerce(ObservationKind, observation_kind)
        if kind is None:
            return _invalid(
                "observation_kind",
                "an observation kind is one of submission-acknowledgement | fill | "
                "cancel-acknowledgement | expiry | close-by-venue",
                given=repr(observation_kind),
                allowed=[member.value for member in ObservationKind],
            )
        if kind is ObservationKind.OUT_OF_SEQUENCE:
            return _invalid(
                "observation_kind",
                "out-of-sequence is a derived annotation applied with with_out_of_sequence, "
                "never a raw inbound kind; adapters never synthesize a venue observation",
            )
        if not isinstance(venue_native_identity, VenueNativeIdentity):
            return _invalid(
                "venue_native_identity",
                "every observation carries a declared VenueNativeIdentity key for gap-replay "
                "deduplication",
                given=repr(venue_native_identity),
            )
        if not isinstance(receive_wall_time, Instant):
            return _invalid(
                "receive_wall_time",
                "recording a wall receive instant is mandatory on every inbound venue event "
                "(the Open API exposes no server clock)",
                given=repr(receive_wall_time),
            )
        if not isinstance(monotonic_stamp, MonotonicReading):
            return _invalid(
                "monotonic_stamp",
                "a boot-scoped monotonic stamp is mandatory on every inbound venue event; a "
                "wall-computed latency rung is refused as a baseline",
                given=repr(monotonic_stamp),
            )
        epoch = _clean_str(session_epoch)
        if epoch is None:
            return _invalid(
                "session_epoch",
                "a session-epoch id (distinct from the boot epoch) rides every observation",
                given=repr(session_epoch),
            )
        if not isinstance(raw_payload, Mapping):
            return _invalid(
                "raw_payload",
                "the raw payload is recorded verbatim as a present mapping; recording precedes "
                "interpretation, so it is never absent",
                given=repr(type(raw_payload).__name__),
            )
        fill_fields = _resolve_fill_fields(kind, fill_price, fill_quantity, venue_instant)
        if isinstance(fill_fields, TypedRefusal):
            return fill_fields
        resolved_price, resolved_quantity, resolved_venue_instant = fill_fields
        subject = _optional_token(subject_native_id, "subject_native_id")
        if isinstance(subject, TypedRefusal):
            return subject
        correlation = _optional_token(correlation_id, "correlation_id")
        if isinstance(correlation, TypedRefusal):
            return correlation
        return Ok(
            cls(
                observation_kind=kind,
                venue_native_identity=venue_native_identity,
                receive_wall_time=receive_wall_time,
                monotonic_stamp=monotonic_stamp,
                session_epoch=epoch,
                raw_payload=cast("Mapping[str, object]", raw_payload),
                fill_price=resolved_price,
                fill_quantity=resolved_quantity,
                venue_instant=resolved_venue_instant,
                subject_native_id=subject,
                correlation_id=correlation,
            )
        )

    def with_out_of_sequence(self, edge: object) -> Result[InboundVenueEvent]:
        """Annotate this recorded observation with a typed out-of-sequence edge.

        Returns a *new* observation carrying the edge — the observation is recorded
        verbatim first and annotated after; the annotation is never a synthesized event
        (DEC-0137). A value that is not an :class:`OutOfSequenceEdge` is refused.
        """
        if not isinstance(edge, OutOfSequenceEdge):
            return _invalid(
                "edge",
                "an observation is annotated with a typed OutOfSequenceEdge",
                given=repr(edge),
            )
        return Ok(replace(self, out_of_sequence=edge))

    def fp1_identity(self) -> Mapping[str, object]:
        """The observation's canonical fp1 identity content (CT-20; DEC-0137, DEC-0138).

        Identity is the venue-native identity key and the observation kind; a fill adds its
        mandatory identity fields (price, quantity, venue instant). The receive stamp,
        monotonic stamp, session epoch, ``correlation_id``, and the out-of-sequence edge are
        on the exclusion list and never enter identity — so a redelivery deduplicates on the
        venue-native key regardless of receipt provenance or annotation.
        """
        content: dict[str, object] = {
            "class": "venue-observation",
            "observation_kind": self.observation_kind.value,
            "venue_native_identity": dict(self.venue_native_identity.fp1_identity()),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.subject_native_id is not None:
            content["subject_native_id"] = self.subject_native_id
        if (
            self.is_fill
            and self.fill_price is not None
            and self.fill_quantity is not None
            and self.venue_instant is not None
        ):
            content["fill_price"] = self.fill_price.fp1_identity()
            content["fill_quantity"] = self.fill_quantity.fp1_identity()
            content["venue_instant"] = self.venue_instant.fp1_identity()
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The observation's fp1 fingerprint over its identity, returning value-or-refusal."""
        return fingerprint(self)


def _resolve_fill_fields(
    kind: ObservationKind,
    fill_price: object,
    fill_quantity: object,
    venue_instant: object,
) -> tuple[Price | None, Quantity | None, Instant | None] | TypedRefusal:
    """Resolve and validate the fill identity fields per observation kind (CT-20).

    A ``fill`` requires an exact :class:`~qmf.core.Price`, a strictly-positive exact
    :class:`~qmf.core.Quantity`, and a venue :class:`~qmf.core.Instant` — the mandatory
    identity fields of a fill, never null (DEC-0137). A non-fill carries no fill price or
    quantity (a kind-inappropriate field is omitted); a non-fill may still carry an optional
    venue instant, since lifecycle events do.
    """
    if kind is ObservationKind.FILL:
        if not isinstance(fill_price, Price):
            return _invalid(
                "fill_price",
                "a fill's price is a mandatory identity field: an exact qmf-core Price "
                "(a binary float on the money path is refused)",
                given=repr(fill_price),
            )
        if not isinstance(fill_quantity, Quantity):
            return _invalid(
                "fill_quantity",
                "a fill's quantity is a mandatory identity field: an exact qmf-core Quantity",
                given=repr(fill_quantity),
            )
        if fill_quantity.as_fraction() <= 0:
            return _invalid(
                "fill_quantity",
                "a fill quantity is strictly positive",
                given=str(fill_quantity.as_fraction()),
            )
        if not isinstance(venue_instant, Instant):
            return _invalid(
                "venue_instant",
                "a fill's venue instant is a mandatory identity field: an exact qmf-core Instant",
                given=repr(venue_instant),
            )
        return fill_price, fill_quantity, venue_instant
    if fill_price is not None:
        return _invalid(
            "fill_price",
            "only a fill observation carries a fill price",
            observation_kind=kind.value,
        )
    if fill_quantity is not None:
        return _invalid(
            "fill_quantity",
            "only a fill observation carries a fill quantity",
            observation_kind=kind.value,
        )
    resolved_instant: Instant | None
    if venue_instant is None:
        resolved_instant = None
    elif isinstance(venue_instant, Instant):
        resolved_instant = venue_instant
    else:
        return _invalid(
            "venue_instant",
            "a venue instant, when present, is an exact qmf-core Instant",
            given=repr(venue_instant),
        )
    return None, None, resolved_instant


def _optional_token(value: object, field_name: str) -> str | TypedRefusal | None:
    """Resolve an optional opaque token: ``None`` stays ``None``, a blank string is refused."""
    if value is None:
        return None
    token = _clean_str(value)
    if token is None:
        return _invalid(
            field_name,
            f"{field_name}, when present, is a non-empty opaque token",
            given=repr(value),
        )
    return token


# --- the observation journal event ------------------------------------------


def observation_journal_event_type(kind: object) -> str | TypedRefusal:
    """The journal event type for one observation kind (CT-20; DEC-0137, DEC-0140).

    The deterministic ``(observation kind) -> journal event type`` mapping under the
    cardinality law — exactly one journal event per recorded observation. A value that
    does not name an :class:`ObservationKind` is an ``invalid input`` refusal.
    """
    resolved = _coerce(ObservationKind, kind)
    if resolved is None:
        return _invalid(
            "kind",
            "an observation journal event type requires an ObservationKind",
            given=repr(kind),
        )
    return f"observation.{resolved.value}"


@dataclass(frozen=True, slots=True)
class ObservationJournalEvent:
    """The journal event minted for one recorded observation (CT-13, CT-20; DEC-0137).

    Exactly one journal event per recorded observation (the cardinality law). ``event_type``
    is the deterministic ``(observation kind) -> journal event type`` mapping; an annotated
    observation maps under its effective ``out-of-sequence`` kind.
    """

    venue_native_identity: VenueNativeIdentity
    observation_kind: ObservationKind
    event_type: str

    @classmethod
    def for_event(cls, event: InboundVenueEvent) -> ObservationJournalEvent:
        """Mint the journal event for one recorded observation (one per observation)."""
        kind = event.effective_journal_kind
        return cls(
            venue_native_identity=event.venue_native_identity,
            observation_kind=kind,
            event_type=cast("str", observation_journal_event_type(kind)),
        )


# --- the read-time order-state fold -----------------------------------------


def is_legal_transition(prior_state: object, observation_kind: object) -> bool:
    """Whether an observation kind has a legal transition from ``prior_state`` (CT-20).

    A safe read: a non-:class:`OrderState` or non-:class:`ObservationKind` argument, and an
    ``out-of-sequence`` kind, are all illegal. The transition table is the fold's
    read-resolution rule; an illegal transition is out-of-sequence and forces the owning
    command to ``UNKNOWN`` (DEC-0137).
    """
    state = _coerce(OrderState, prior_state)
    kind = _coerce(ObservationKind, observation_kind)
    if state is None or kind is None:
        return False
    return state in _LEGAL_PRIOR.get(kind, frozenset())


def detect_out_of_sequence(prior_state: object, event: object) -> Result[OutOfSequenceEdge | None]:
    """Detect an out-of-sequence transition, returning the edge to annotate or ``None``.

    Given the current fold state and a recorded observation, returns an
    :class:`OutOfSequenceEdge` when the observation has no legal transition (the caller
    annotates the recorded observation with it, forcing the owning command to ``UNKNOWN``),
    or ``None`` when the transition is legal. A non-:class:`OrderState` prior or a
    non-:class:`InboundVenueEvent` is refused (DEC-0137).
    """
    state = _coerce(OrderState, prior_state)
    if state is None:
        return _invalid(
            "prior_state",
            "a transition is detected against the current fold state (an OrderState)",
            given=repr(prior_state),
        )
    if not isinstance(event, InboundVenueEvent):
        return _invalid(
            "event",
            "an out-of-sequence check reads a recorded InboundVenueEvent",
            given=repr(event),
        )
    if is_legal_transition(state, event.observation_kind):
        return Ok(None)
    edge = OutOfSequenceEdge(
        attempted_kind=event.observation_kind,
        prior_state=state,
        reason=(
            f"a {event.observation_kind.value} observation has no legal transition from "
            f"{state.value}; the owning command is forced to UNKNOWN pending resolution"
        ),
    )
    return Ok(edge)


@dataclass(frozen=True, slots=True)
class OrderStateProjection:
    """A read-time fold result — the derived order state, never a stored field (CT-20).

    ``state`` is the folded order state; ``out_of_sequence`` is ``True`` when an observation
    with no legal transition forced the fold to ``UNKNOWN``; ``terminal`` is ``True`` only
    for an order-lifecycle terminal decided by fills or venue lifecycle events (never for a
    command-outcome prefix); ``cumulative_fill`` is the exact rational quantity filled so far
    (DEC-0137).
    """

    state: OrderState
    out_of_sequence: bool
    terminal: bool
    cumulative_fill: Fraction


def fold_order_state(
    command_outcome: object,
    observations: object,
    *,
    ordered_quantity: object = None,
) -> Result[OrderStateProjection]:
    """Fold the order state at read time over the observation stream (CT-20; DEC-0137).

    The order-state machine is a **read-time fold**, never a stored field: the
    command-outcome stream projects the prefix state (``None`` -> ``client-submitted``;
    ``accepted-by-venue`` -> ``venue-accepted``; ``rejected-by-venue`` -> ``venue-rejected``;
    ``UNKNOWN`` -> ``UNKNOWN``), and the observation stream then decides the order's terminal
    state — a fill completes the ``ordered_quantity`` to ``filled`` (partial otherwise), and a
    cancel/expiry/close-by-venue is the matching terminal. A terminal state is **never**
    inferred from a command outcome or from absence alone. An observation with no legal
    transition (or already annotated out-of-sequence) forces the fold to ``UNKNOWN``.
    ``denied-locally`` and ``partially-executed`` have no venue order and are refused.
    """
    prefix = _resolve_prefix(command_outcome)
    if isinstance(prefix, TypedRefusal):
        return prefix
    events = _resolve_observation_stream(observations)
    if isinstance(events, TypedRefusal):
        return events
    if ordered_quantity is not None and not isinstance(ordered_quantity, Quantity):
        return _invalid(
            "ordered_quantity",
            "the ordered quantity a fill completes against is an exact qmf-core Quantity",
            given=repr(ordered_quantity),
        )
    ordered_fraction = ordered_quantity.as_fraction() if ordered_quantity is not None else None
    running = prefix
    cumulative = Fraction(0)
    for event in events:
        if event.out_of_sequence is not None or not is_legal_transition(
            running, event.observation_kind
        ):
            return Ok(
                OrderStateProjection(
                    state=OrderState.UNKNOWN,
                    out_of_sequence=True,
                    terminal=False,
                    cumulative_fill=cumulative,
                )
            )
        running, cumulative = _apply_transition(running, cumulative, ordered_fraction, event)
    return Ok(
        OrderStateProjection(
            state=running,
            out_of_sequence=False,
            terminal=running in _TERMINAL_STATES,
            cumulative_fill=cumulative,
        )
    )


def _resolve_prefix(command_outcome: object) -> OrderState | TypedRefusal:
    """Project a submitted command's outcome onto its order-state prefix (CT-20)."""
    if command_outcome is None:
        return OrderState.CLIENT_SUBMITTED
    outcome = _coerce(SubmissionOutcome, command_outcome)
    if outcome is None or outcome not in _PREFIX_PROJECTION:
        return _invalid(
            "command_outcome",
            "the order-state prefix projects only a submitted command's outcome — "
            "accepted-by-venue | rejected-by-venue | UNKNOWN, or None for client-submitted; "
            "denied-locally and partially-executed have no venue order",
            given=repr(command_outcome),
            allowed=[member.value for member in _PREFIX_PROJECTION],
        )
    return _PREFIX_PROJECTION[outcome]


def _resolve_observation_stream(observations: object) -> list[InboundVenueEvent] | TypedRefusal:
    """Validate the observation stream is a sequence of recorded observations (CT-20)."""
    if isinstance(observations, (str, bytes)) or not isinstance(observations, Sequence):
        return _invalid(
            "observations",
            "the fold reads a sequence of recorded InboundVenueEvent observations",
            given=repr(observations),
        )
    events: list[InboundVenueEvent] = []
    for index, item in enumerate(cast("Sequence[object]", observations)):
        if not isinstance(item, InboundVenueEvent):
            return _invalid(
                "observations",
                "each recorded observation is an InboundVenueEvent",
                index=index,
                given=repr(item),
            )
        events.append(item)
    return events


def _apply_transition(
    running: OrderState,
    cumulative: Fraction,
    ordered_fraction: Fraction | None,
    event: InboundVenueEvent,
) -> tuple[OrderState, Fraction]:
    """Apply one legal observation to the running fold state (CT-20; DEC-0137)."""
    kind = event.observation_kind
    if kind is ObservationKind.SUBMISSION_ACKNOWLEDGEMENT:
        return OrderState.VENUE_ACCEPTED, cumulative
    if kind is ObservationKind.FILL:
        if event.fill_quantity is not None:
            cumulative = cumulative + event.fill_quantity.as_fraction()
        if ordered_fraction is not None and cumulative >= ordered_fraction:
            return OrderState.FILLED, cumulative
        return OrderState.PARTIALLY_FILLED, cumulative
    if kind is ObservationKind.CANCEL_ACKNOWLEDGEMENT:
        return OrderState.CANCELLED, cumulative
    if kind is ObservationKind.EXPIRY:
        return OrderState.EXPIRED, cumulative
    # CLOSE_BY_VENUE is the only remaining legal kind (OUT_OF_SEQUENCE is never legal).
    return OrderState.CLOSED_BY_VENUE, cumulative


# --- the multi-room write ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class MultiRoomWrite:
    """One ordered-unit multi-room write with a named transaction boundary (CT-20).

    The raw archive, journal, and registry room complete as one ordered unit; the
    ``boundary`` is ``atomic`` or ``ordered-with-recovery``. Built through :meth:`for_event`,
    which derives the one journal event the cardinality law allows per observation
    (DEC-0138, DEC-0140).
    """

    boundary: TransactionBoundary
    event: InboundVenueEvent
    journal_event: ObservationJournalEvent
    registry_record: object

    @classmethod
    def for_event(
        cls, event: object, *, registry_record: object, boundary: object
    ) -> Result[MultiRoomWrite]:
        """Validate and build a :class:`MultiRoomWrite` from one recorded observation.

        The journal event is derived (one per observation); the registry record is the
        root-minted record written through the registry room and must be present (a
        registry-room record is never null). A malformed event or boundary is refused.
        """
        if not isinstance(event, InboundVenueEvent):
            return _invalid(
                "event",
                "a multi-room write archives one recorded InboundVenueEvent",
                given=repr(event),
            )
        resolved_boundary = _coerce(TransactionBoundary, boundary)
        if resolved_boundary is None:
            return _invalid(
                "boundary",
                "a multi-room write declares a named transaction boundary: atomic | "
                "ordered-with-recovery",
                given=repr(boundary),
                allowed=[member.value for member in TransactionBoundary],
            )
        if registry_record is None:
            return _invalid(
                "registry_record",
                "the registry-room record is present; the root mints it and it is written "
                "through the injected RecordSink, never a null",
            )
        return Ok(
            cls(
                boundary=resolved_boundary,
                event=event,
                journal_event=ObservationJournalEvent.for_event(event),
                registry_record=registry_record,
            )
        )


@dataclass(frozen=True, slots=True)
class MultiRoomWriteResult:
    """The result of one multi-room write attempt (CT-20; DEC-0138, DEC-0140).

    ``completed_rooms`` are the rooms that landed, in order; ``failed_room`` is the room a
    partial write failed on (or ``None`` when committed); ``committed`` is ``True`` only when
    all three rooms landed. A partial write is surfaced as a ``storage failure`` refusal from
    the recorder, not this value — this records what did and did not land.
    """

    boundary: TransactionBoundary
    completed_rooms: tuple[WriteRoom, ...]
    failed_room: WriteRoom | None
    committed: bool


@dataclass(frozen=True, slots=True)
class PartialWriteRecovery:
    """A pending partial multi-room write to be journaled on recovery (CT-20; DEC-0138).

    Held by the recorder after a partial write so that, when the store recovers, the partial
    write is journaled (one recovery journal event). It carries which rooms landed, the room
    that failed, and the affected observation's venue-native identity.
    """

    boundary: TransactionBoundary
    completed_rooms: tuple[WriteRoom, ...]
    failed_room: WriteRoom
    event_identity: VenueNativeIdentity

    def recovery_journal_event(self) -> ObservationJournalEvent:
        """The journal event recording the partial write on recovery (one per recovery).

        Keyed by the affected observation's venue-native identity and typed as the
        out-of-sequence-class recovery note, so a partial write is never lost — it is
        journaled on recovery per CT-20 (DEC-0138, DEC-0140).
        """
        return ObservationJournalEvent(
            venue_native_identity=self.event_identity,
            observation_kind=ObservationKind.OUT_OF_SEQUENCE,
            event_type="observation.partial-write-recovery",
        )


class EventRecorder:
    """Records inbound venue events before interpretation, as ordered multi-room units.

    Constructed through :meth:`try_create` from the composition-root-wired
    :class:`~qmf.venue.connection.ConnectionManager` — the writer that holds the ``WriterId``
    and sees every persistence failure. :meth:`record` stores one observation verbatim
    (raw archive), journals it, and writes its registry record, in that order; a partial
    write is a ``storage failure`` refusal that **blocks the command stream** (the connection
    manager applies block-on-unpersistable) while the **sensing pipe is unaffected**, and the
    partial write is journaled on :meth:`recover` when the store returns (AR-47, FM-2;
    DEC-0138). No state machine ever gates the immutable store: recording precedes
    interpretation (DEC-0137).

    Deliberately not a frozen value: it holds the pending-recovery state for its writer,
    following one-writer-per-stream (DEC-0113).
    """

    __slots__ = ("_cm", "_pending_recovery")

    _cm: ConnectionManager
    _pending_recovery: PartialWriteRecovery | None

    def __init__(self, connection_manager: ConnectionManager) -> None:
        # Unchecked trusted-internal constructor; callers use try_create.
        self._cm = connection_manager
        self._pending_recovery = None

    @classmethod
    def try_create(cls, connection_manager: object) -> Result[EventRecorder]:
        """Validate the injected wiring and build an :class:`EventRecorder`."""
        if not isinstance(connection_manager, ConnectionManager):
            return _invalid(
                "connection_manager",
                "the recorder writes through the venue ConnectionManager (the WriterId holder)",
                given=repr(connection_manager),
            )
        return Ok(cls(connection_manager))

    @property
    def connection_manager(self) -> ConnectionManager:
        """The connection manager this recorder writes through (the WriterId holder)."""
        return self._cm

    @property
    def command_pipe_open(self) -> bool:
        """Whether the command pipe accepts dispatch (no outstanding storage-failure block)."""
        return self._cm.command_pipe_open

    @property
    def sensing_pipe_open(self) -> bool:
        """Whether the sensing pipe is flowing — never gated by a command-path failure."""
        return self._cm.sensing_pipe_open

    @property
    def pending_recovery(self) -> PartialWriteRecovery | None:
        """The pending partial multi-room write to journal on recovery, or ``None``."""
        return self._pending_recovery

    def record(
        self, event: object, *, registry_record: object, boundary: object
    ) -> Result[MultiRoomWriteResult]:
        """Record one inbound observation as an ordered multi-room write (CT-20; AR-47).

        Builds the multi-room unit (raw archive, journal, registry room) and executes it in
        order. Recording precedes interpretation: the observation is stored verbatim and
        journaled before any state evaluation. A partial write is a ``storage failure``
        refusal that blocks the command stream (DEC-0137, DEC-0138).
        """
        write = MultiRoomWrite.for_event(event, registry_record=registry_record, boundary=boundary)
        if is_refusal(write):
            return write
        return self.record_multi_room(write.value)

    def record_multi_room(self, write: object) -> Result[MultiRoomWriteResult]:
        """Execute one multi-room write as an ordered unit (CT-20; DEC-0138, DEC-0140).

        Writes the raw archive, then the journal, then the registry room. The first
        ``storage failure`` makes the write **partial**: the command stream is blocked (the
        connection manager applies block-on-unpersistable), the partial write is held for
        recovery journaling, and a ``storage failure`` refusal is returned carrying which
        rooms landed and which failed. All three landing is a committed write.
        """
        if not isinstance(write, MultiRoomWrite):
            return _invalid(
                "write", "a multi-room write executes a MultiRoomWrite unit", given=repr(write)
            )
        completed: list[WriteRoom] = []
        raw = self._cm.emit_command_observation(write.event)
        if is_refusal(raw):
            return self._partial(write, completed, WriteRoom.RAW_ARCHIVE, raw)
        completed.append(WriteRoom.RAW_ARCHIVE)
        journalled = self._cm.append_command_journal(write.journal_event)
        if is_refusal(journalled):
            return self._partial(write, completed, WriteRoom.JOURNAL, journalled)
        completed.append(WriteRoom.JOURNAL)
        recorded = self._cm.write_command_record(write.registry_record)
        if is_refusal(recorded):
            return self._partial(write, completed, WriteRoom.REGISTRY_ROOM, recorded)
        completed.append(WriteRoom.REGISTRY_ROOM)
        self._pending_recovery = None
        return Ok(
            MultiRoomWriteResult(
                boundary=write.boundary,
                completed_rooms=tuple(completed),
                failed_room=None,
                committed=True,
            )
        )

    def _partial(
        self,
        write: MultiRoomWrite,
        completed: list[WriteRoom],
        failed_room: WriteRoom,
        refusal: TypedRefusal,
    ) -> Result[MultiRoomWriteResult]:
        """Handle a partial multi-room write (CT-20; FM-2; DEC-0138, DEC-0140).

        A partial write on a ``storage failure`` blocks the command stream (the connection
        manager already set the block on the failing command-path write), is held for
        recovery journaling, and is surfaced as a ``storage failure`` refusal carrying the
        completed and failed rooms. Any other refusal (a shape error) is surfaced unchanged,
        never relabeled as a storage failure.
        """
        if not is_unpersistable(refusal):
            return refusal
        self._pending_recovery = PartialWriteRecovery(
            boundary=write.boundary,
            completed_rooms=tuple(completed),
            failed_room=failed_room,
            event_identity=write.event.venue_native_identity,
        )
        return unpersistable(
            "a multi-room venue write completed only partially; the command stream is blocked "
            "and the partial write is journaled on recovery",
            context={
                "boundary": write.boundary.value,
                "completed_rooms": [room.value for room in completed],
                "failed_room": failed_room.value,
            },
        )

    def recover(self) -> SinkResult:
        """Journal a pending partial multi-room write on recovery (CT-20; DEC-0138).

        Appends the recovery journal event through the connection manager. On success the
        partial write is cleared (and the recovered command-path write clears the
        storage-failure block); on a still-failing store the recovery stays pending and the
        refusal is surfaced. Calling with nothing pending is an ``invalid input`` refusal.
        """
        if self._pending_recovery is None:
            return _invalid(
                "recovery",
                "there is no pending partial multi-room write to journal on recovery",
            )
        result = self._cm.append_command_journal(self._pending_recovery.recovery_journal_event())
        if is_refusal(result):
            return result
        self._pending_recovery = None
        return result


# --- on-demand reconciliation -----------------------------------------------


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """One reconciliation verdict and what it gates (CT-20; DEC-0137, DEC-0150, DEC-0158).

    Reconciliation gates the **command pipe only** — the sensing pipe never blocks on it. A
    standing protection intent re-evaluates only against a ``reconciled`` verdict, so
    ``drift``, ``unknown``, and ``out-of-lookback`` hold the intent open without dispatching;
    ``out-of-lookback`` in particular is never read as "the position closed".
    """

    verdict: ReconciliationVerdict
    detail: str

    @property
    def standing_intent_may_dispatch(self) -> bool:
        """Whether a standing protection intent may dispatch — only against ``reconciled``."""
        return self.verdict is ReconciliationVerdict.RECONCILED

    @property
    def holds_intent_open(self) -> bool:
        """Whether the verdict holds a standing intent open without dispatching (alarm)."""
        return self.verdict in {
            ReconciliationVerdict.DRIFT,
            ReconciliationVerdict.UNKNOWN,
            ReconciliationVerdict.OUT_OF_LOOKBACK,
        }

    @property
    def is_out_of_lookback(self) -> bool:
        """Whether the read-back could not see the whole declared lookback — never read as
        "the position closed" (DEC-0158)."""
        return self.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK

    @property
    def gates_sensing_pipe(self) -> bool:
        """Reconciliation never gates the sensing pipe — it gates the command pipe only."""
        return False


@dataclass(frozen=True, slots=True)
class ReconciliationReadback:
    """An on-demand read-back over a mandatory declared lookback (CT-20; FR-024; DEC-0158).

    The lookback is a **do-not-default** declared adapter parameter: its existence and
    declaration are QMF's and its value is node's, so it is a mandatory construction
    argument, never defaulted. The read-back's ``earliest_visible`` instant is how far back
    the venue can be read; when the required window (``reference_instant`` minus
    ``declared_lookback``) starts earlier than that, the verdict is ``out-of-lookback`` —
    "I cannot see that far back" is never read as "the position closed" (DEC-0137, DEC-0158).
    """

    reference_instant: Instant
    declared_lookback: Duration
    requested_since: Instant
    earliest_visible: Instant
    readback_evidence: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "readback_evidence", _deep_freeze(self.readback_evidence))

    @classmethod
    def try_create(
        cls,
        reference_instant: object,
        declared_lookback: object,
        earliest_visible: object,
        readback_evidence: object,
    ) -> Result[ReconciliationReadback]:
        """Validate and build a :class:`ReconciliationReadback`, returning value-or-refusal.

        The declared lookback is mandatory (do-not-default) and strictly positive; the
        instants are exact; the read-back evidence (orders, fills, positions, balance) is a
        present mapping. The required window start is ``reference_instant - declared_lookback``,
        refused on nanosecond overflow (FM-2).
        """
        if not isinstance(reference_instant, Instant):
            return _invalid(
                "reference_instant",
                "a read-back is anchored at a reference Instant (injected, never a clock read)",
                given=repr(reference_instant),
            )
        if not isinstance(declared_lookback, Duration):
            return _invalid(
                "declared_lookback",
                "the reconciliation lookback is a mandatory declared adapter parameter under "
                "do-not-default (a qmf-core Duration); its existence is QMF's, its value node's",
                given=repr(declared_lookback),
            )
        if declared_lookback.value_ns <= 0:
            return _invalid(
                "declared_lookback",
                "a reconciliation lookback is a strictly-positive span",
                given=str(declared_lookback.value_ns),
            )
        if not isinstance(earliest_visible, Instant):
            return _invalid(
                "earliest_visible",
                "the earliest instant the venue read-back can see is an exact Instant",
                given=repr(earliest_visible),
            )
        if not isinstance(readback_evidence, Mapping):
            return _invalid(
                "readback_evidence",
                "a read-back carries its orders/fills/positions/balance as a present mapping",
                given=repr(type(readback_evidence).__name__),
            )
        negated = declared_lookback.negate()
        if is_refusal(negated):
            return negated
        requested_since = reference_instant.add_duration(negated.value)
        if is_refusal(requested_since):
            return requested_since
        return Ok(
            cls(
                reference_instant=reference_instant,
                declared_lookback=declared_lookback,
                requested_since=requested_since.value,
                earliest_visible=earliest_visible,
                readback_evidence=cast("Mapping[str, object]", readback_evidence),
            )
        )

    @property
    def covers_declared_lookback(self) -> bool:
        """Whether the read-back can see the whole declared lookback (window start visible)."""
        return self.requested_since.value_ns >= self.earliest_visible.value_ns

    def verdict(self, expected_state: object, observed_state: object) -> Result[Reconciliation]:
        """Produce the reconciliation verdict over the declared lookback (CT-20; DEC-0158).

        ``out-of-lookback`` when the read-back cannot see the whole declared lookback — so
        it is never read as "the position closed"; ``unknown`` when the venue state could
        not be read (``observed_state`` is ``None``); ``reconciled`` when the expected and
        observed states agree; ``drift`` when they disagree. The caller supplies the compared
        local (expected) and venue (observed) states.
        """
        if not self.covers_declared_lookback:
            return Ok(
                Reconciliation(
                    verdict=ReconciliationVerdict.OUT_OF_LOOKBACK,
                    detail=(
                        "the read-back cannot see as far back as the declared lookback; "
                        "'I cannot see that far back' is never read as 'the position closed'"
                    ),
                )
            )
        if observed_state is None:
            return Ok(
                Reconciliation(
                    verdict=ReconciliationVerdict.UNKNOWN,
                    detail="the venue read-back is incomplete; the state could not be read",
                )
            )
        if expected_state == observed_state:
            return Ok(
                Reconciliation(
                    verdict=ReconciliationVerdict.RECONCILED,
                    detail="local and venue state agree over the declared lookback",
                )
            )
        return Ok(
            Reconciliation(
                verdict=ReconciliationVerdict.DRIFT,
                detail="local and venue state disagree over the declared lookback",
            )
        )


# --- subject-terminal read-back resolution ----------------------------------


@dataclass(frozen=True, slots=True)
class SubjectTerminalOutcome:
    """The subject-terminal read-back resolution of a close/amend command (CT-20).

    ``resolution`` is the :class:`SubjectResolution`; ``outcome`` is the named
    :class:`~qmf.venue.commands.SubmissionOutcome` when the command resolves without a normal
    submission (``rejected-by-venue`` for a superseded subject), else ``None``;
    ``resolving_observation`` is the terminal observation that resolved it (the named
    resolving evidence), or ``None`` (DEC-0148, DEC-0158).
    """

    resolution: SubjectResolution
    outcome: SubmissionOutcome | None
    resolving_observation: InboundVenueEvent | None
    detail: str


def resolve_subject_terminal(
    command: object,
    *,
    observations: object,
    submit_stamp: object,
    subject_present_at_submission: object,
) -> Result[SubjectTerminalOutcome]:
    """Resolve a close/amend command against its subject's terminal observations (CT-20).

    The read-back resolution generalizes from cancels to every command whose subject can
    terminate independently — ``close_position``, ``close_all``, ``amend_protection``. A
    subject **absent or already terminal at submission** resolves **without submission**
    (never a naked close). A subject observed terminal **at or after the submit stamp**
    resolves ``rejected-by-venue (superseded-by-terminal-subject)`` — a **named outcome**,
    never ``UNKNOWN``, never a stream block — with the subject-terminal observation as the
    named resolving evidence. A live subject with no terminal observation **proceeds**
    (DEC-0148, DEC-0158).
    """
    if not isinstance(command, Command):
        return _invalid(
            "command", "subject-terminal resolution reads a typed Command", given=repr(command)
        )
    if command.kind not in _SUBJECT_COMMANDS:
        return _invalid(
            "command",
            "subject-terminal resolution applies to close_position | close_all | "
            "amend_protection — the commands whose subject can terminate independently",
            kind=command.kind.value,
        )
    if not isinstance(submit_stamp, Instant):
        return _invalid(
            "submit_stamp",
            "the submit stamp the subject-terminal comparison reads is an exact Instant",
            given=repr(submit_stamp),
        )
    if not isinstance(subject_present_at_submission, bool):
        return _invalid(
            "subject_present_at_submission",
            "whether the subject was live at submission is a boolean the caller resolves from a "
            "pre-submit read",
            given=repr(subject_present_at_submission),
        )
    events = _resolve_observation_stream(observations)
    if isinstance(events, TypedRefusal):
        return events
    subject = command.subject_reference
    if subject is None:  # pragma: no cover - the three subject commands always carry a subject
        return _invalid(
            "command", "a subject command carries a subject reference", kind=command.kind.value
        )
    before, at_or_after = _find_subject_terminal(subject, submit_stamp, events)
    if not subject_present_at_submission or before is not None:
        return Ok(
            SubjectTerminalOutcome(
                resolution=SubjectResolution.RESOLVE_WITHOUT_SUBMISSION,
                outcome=None,
                resolving_observation=before,
                detail=(
                    "the subject is absent or already terminal at submission; the command "
                    "resolves without submission, never as a naked close"
                ),
            )
        )
    if at_or_after is not None:
        return Ok(
            SubjectTerminalOutcome(
                resolution=SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT,
                outcome=SubmissionOutcome.REJECTED_BY_VENUE,
                resolving_observation=at_or_after,
                detail=(
                    "the subject was observed terminal at or after the submit stamp; the command "
                    "resolves rejected-by-venue (superseded-by-terminal-subject), a named outcome, "
                    "never UNKNOWN and never a stream block"
                ),
            )
        )
    return Ok(
        SubjectTerminalOutcome(
            resolution=SubjectResolution.PROCEED,
            outcome=None,
            resolving_observation=None,
            detail="the subject is live with no terminal observation; the command proceeds",
        )
    )


def _find_subject_terminal(
    subject: str, submit_stamp: Instant, events: Sequence[InboundVenueEvent]
) -> tuple[InboundVenueEvent | None, InboundVenueEvent | None]:
    """The earliest subject-terminal observations before, and at-or-after, the submit stamp.

    Scans for terminal observations of ``subject`` (a fill, cancel, expiry, or close-by-venue
    naming it), split by whether the observation's instant falls before or at/after the submit
    stamp (DEC-0148, DEC-0158).
    """
    before: InboundVenueEvent | None = None
    at_or_after: InboundVenueEvent | None = None
    for event in events:
        if event.subject_native_id != subject:
            continue
        if event.observation_kind not in _SUBJECT_TERMINAL_KINDS:
            continue
        if event.subject_instant.value_ns >= submit_stamp.value_ns:
            if at_or_after is None:
                at_or_after = event
        elif before is None:
            before = event
    return before, at_or_after
