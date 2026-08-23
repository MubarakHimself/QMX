"""Story 10.10 — CT-25 entity journals as read-time projections (COMP-QMF-RISK).

Entity journals — the Book journal, the BMS journal, and the per-bot journal (the
operator's logbook) — are **read-time projections** over AD-21 writer-scoped streams
selected by entity identity. An entity holds no ``WriterId`` and mints no stream of
its own (AD-31; DEC-0145, DEC-0158).

* the legacy five Records names (``veto_ledger``, ``trade_journal``, ``book_journal``,
  ``ksa_audit_log``, ``correlation_ledger``) survive as **projection names only**,
  mapped onto AD-21's seven event types by one versioned table — no second event
  catalog;
* two event classes: **risk-authored** (``decision``, ``risk transition``,
  ``control action``, ``promotion``) carry the Book-definition fingerprint and
  binding identity; **venue-authored** (``order``, ``fill``, ``data quality``) carry
  the command record's content fingerprint — Book identity is never threaded into a
  venue payload;
* the **command-fingerprint join** is pinned versioned CT-25 surface;
* a control action is journaled before dispatch: a storage failure **blocks** the
  dispatch rather than losing the intent;
* paper and live resolve inside one role-scoped namespace; a cross-role read is an
  explicit declaration, never a silent union.

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface — no live binding or order is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_refusal,
    is_unpersistable,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, type_name
from qmf.risk.control_action import ControlActionRecord, journal_before_dispatch

__all__ = [
    "CT25_COMMAND_FINGERPRINT_JOIN_VERSION",
    "CT25_CONTRACT_FORMAT_VERSION",
    "CT25_MAPPING_TABLE_VERSION",
    "LEGACY_PROJECTION_NAMES",
    "RECORDS_STREAM_MAPPING",
    "RISK_AUTHORED_EVENT_TYPES",
    "VENUE_AUTHORED_EVENT_TYPES",
    "CommandFingerprintJoin",
    "DecisionOutcome",
    "EntityJournalProjection",
    "EntityKind",
    "EntitySelector",
    "EventClass",
    "JournalEventType",
    "LegacyProjectionName",
    "ProjectedJournalRow",
    "RiskAuthoredEvent",
    "RiskWriterUnit",
    "VenueAuthoredEvent",
    "WriterScopedStream",
    "block_dispatch_on_journal_failure",
    "event_class_of",
    "join_via_command_fingerprint",
    "map_legacy_projection",
    "project_entity_journal",
    "project_legacy",
    "reject_book_identity_in_venue_payload",
    "reject_cross_role_silent_union",
    "reject_entity_as_writer",
]

CT25_CONTRACT_FORMAT_VERSION: Final[int] = 1
CT25_MAPPING_TABLE_VERSION: Final[int] = 1
CT25_COMMAND_FINGERPRINT_JOIN_VERSION: Final[int] = 1


# --- closed vocabularies -----------------------------------------------------


class JournalEventType(StrEnum):
    """AD-21's seven journal event types the mapping table targets (DEC-0145)."""

    DECISION = "decision"
    ORDER = "order"
    FILL = "fill"
    RISK_TRANSITION = "risk transition"
    PROMOTION = "promotion"
    DATA_QUALITY = "data quality"
    CONTROL_ACTION = "control action"


class EventClass(StrEnum):
    """Which authoring layer minted the underlying AD-21 event (DEC-0145)."""

    RISK_AUTHORED = "risk-authored"
    VENUE_AUTHORED = "venue-authored"


class LegacyProjectionName(StrEnum):
    """Legacy five Records stream names — projection names only, never writers."""

    VETO_LEDGER = "veto_ledger"
    TRADE_JOURNAL = "trade_journal"
    BOOK_JOURNAL = "book_journal"
    KSA_AUDIT_LOG = "ksa_audit_log"
    CORRELATION_LEDGER = "correlation_ledger"


class EntityKind(StrEnum):
    """Entity identity a projection resolves by — never a WriterId (DEC-0145)."""

    BOOK = "book"
    BMS = "bms"
    BOT = "bot"


class DecisionOutcome(StrEnum):
    """Mandatory closed outcome on a decision event (DEC-0158).

    Every projection (the legacy ``veto_ledger`` included) selects on this declared
    field and never on key presence.
    """

    AUTHORIZED = "authorized"
    REFUSED_BY_DOOR = "refused-by-door"
    SUPPRESSED = "suppressed"


RISK_AUTHORED_EVENT_TYPES: Final[frozenset[JournalEventType]] = frozenset(
    {
        JournalEventType.DECISION,
        JournalEventType.RISK_TRANSITION,
        JournalEventType.CONTROL_ACTION,
        JournalEventType.PROMOTION,
    }
)
VENUE_AUTHORED_EVENT_TYPES: Final[frozenset[JournalEventType]] = frozenset(
    {
        JournalEventType.ORDER,
        JournalEventType.FILL,
        JournalEventType.DATA_QUALITY,
    }
)

# One versioned table: legacy Records projection name → AD-21 event types.
# veto_ledger further filters decision.outcome == refused-by-door at project time.
_RECORDS_STREAM_MAPPING_RAW: dict[LegacyProjectionName, frozenset[JournalEventType]] = {
    LegacyProjectionName.VETO_LEDGER: frozenset({JournalEventType.DECISION}),
    LegacyProjectionName.TRADE_JOURNAL: frozenset(
        {
            JournalEventType.DECISION,
            JournalEventType.ORDER,
            JournalEventType.FILL,
            JournalEventType.RISK_TRANSITION,
        }
    ),
    LegacyProjectionName.BOOK_JOURNAL: frozenset(
        {
            JournalEventType.DECISION,
            JournalEventType.RISK_TRANSITION,
            JournalEventType.CONTROL_ACTION,
            JournalEventType.PROMOTION,
            JournalEventType.ORDER,
            JournalEventType.FILL,
            JournalEventType.DATA_QUALITY,
        }
    ),
    LegacyProjectionName.KSA_AUDIT_LOG: frozenset(
        {
            JournalEventType.CONTROL_ACTION,
            JournalEventType.PROMOTION,
            JournalEventType.RISK_TRANSITION,
        }
    ),
    LegacyProjectionName.CORRELATION_LEDGER: frozenset(
        {
            JournalEventType.DECISION,
            JournalEventType.ORDER,
            JournalEventType.FILL,
        }
    ),
}
RECORDS_STREAM_MAPPING: Final[Mapping[LegacyProjectionName, frozenset[JournalEventType]]] = (
    MappingProxyType(_RECORDS_STREAM_MAPPING_RAW)
)
LEGACY_PROJECTION_NAMES: Final[tuple[LegacyProjectionName, ...]] = tuple(LegacyProjectionName)


def event_class_of(event_type: object) -> Result[EventClass]:
    """Return the authoring class of an AD-21 event type (DEC-0145)."""
    resolved = coerce_enum(JournalEventType, event_type)
    if resolved is None:
        return invalid(
            "event_type",
            "event type is one of AD-21's seven journal event types",
            given=repr(event_type),
            allowed=[member.value for member in JournalEventType],
        )
    if resolved in RISK_AUTHORED_EVENT_TYPES:
        return _Ok(EventClass.RISK_AUTHORED)
    return _Ok(EventClass.VENUE_AUTHORED)


def map_legacy_projection(name: object) -> Result[frozenset[JournalEventType]]:
    """Map a legacy Records projection name onto AD-21 event types (DEC-0145).

    The mapping is the one versioned CT-25 table; no second event catalog is minted.
    """
    resolved = coerce_enum(LegacyProjectionName, name)
    if resolved is None:
        return invalid(
            "name",
            "legacy projection name is one of the five Records names surviving as "
            "projection names only",
            given=repr(name),
            allowed=[member.value for member in LegacyProjectionName],
        )
    return _Ok(RECORDS_STREAM_MAPPING[resolved])


# --- writer unit and entity selector -----------------------------------------


@dataclass(frozen=True, slots=True)
class RiskWriterUnit:
    """Risk-domain writer identity ``(machine, risk role, binding)`` (DEC-0145).

    Declared so AD-21's gapless per-(writer, boot-epoch) sequence has an owner for
    risk-authored events. Distinct from an :class:`EntitySelector` — an entity never
    holds a WriterId.
    """

    machine: str
    risk_role: str
    binding_identity: Fingerprint
    boot_epoch_id: str

    @classmethod
    def try_create(
        cls,
        machine: object,
        risk_role: object,
        binding_identity: object,
        boot_epoch_id: object,
    ) -> Result[RiskWriterUnit]:
        """Validate and build a :class:`RiskWriterUnit`, value-or-refusal."""
        machine_token = clean_str(machine)
        if machine_token is None:
            return invalid(
                "machine",
                "a risk writer unit names a non-blank machine",
                given=repr(machine),
            )
        role_token = clean_str(risk_role)
        if role_token is None:
            return invalid(
                "risk_role",
                "a risk writer unit names a non-blank risk role",
                given=repr(risk_role),
            )
        if not isinstance(binding_identity, Fingerprint):
            return invalid(
                "binding_identity",
                "a risk writer unit is scoped to a binding fingerprint",
                given=repr(binding_identity),
            )
        boot = clean_str(boot_epoch_id)
        if boot is None:
            return invalid(
                "boot_epoch_id",
                "a risk writer unit carries a non-blank boot/epoch id",
                given=repr(boot_epoch_id),
            )
        return _Ok(
            cls(
                machine=machine_token,
                risk_role=role_token,
                binding_identity=binding_identity,
                boot_epoch_id=boot,
            )
        )

    def as_writer_id(self, stream: object) -> Result[WriterId]:
        """Mint the AD-21 :class:`~qmf.core.WriterId` for one writer-scoped stream."""
        stream_token = clean_str(stream)
        if stream_token is None:
            return invalid(
                "stream",
                "a writer-scoped stream name is a non-blank token",
                given=repr(stream),
            )
        return WriterId.try_create(
            self.machine, self.risk_role, stream_token, self.boot_epoch_id
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this writer unit."""
        return {
            "class": "risk-writer-unit",
            "machine": self.machine,
            "risk_role": self.risk_role,
            "binding_identity": self.binding_identity.value,
            "boot_epoch_id": self.boot_epoch_id,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class EntitySelector:
    """Entity identity a projection resolves by — not a WriterId (DEC-0145).

    ``BOOK`` / ``BMS`` select by entity fingerprint; ``BOT`` additionally carries the
    seat binding when the act concerns one bot.
    """

    kind: EntityKind
    entity_identity: Fingerprint
    seat_binding: Fingerprint | None

    @classmethod
    def try_create(
        cls,
        kind: object,
        entity_identity: object,
        seat_binding: object = None,
    ) -> Result[EntitySelector]:
        """Validate and build an :class:`EntitySelector`, value-or-refusal."""
        resolved_kind = coerce_enum(EntityKind, kind)
        if resolved_kind is None:
            return invalid(
                "kind",
                "entity kind is book | bms | bot",
                given=repr(kind),
                allowed=[member.value for member in EntityKind],
            )
        if not isinstance(entity_identity, Fingerprint):
            return invalid(
                "entity_identity",
                "an entity selector names a fingerprinted entity identity, never a WriterId",
                given=repr(entity_identity),
            )
        seat: Fingerprint | None
        if seat_binding is None:
            seat = None
        elif isinstance(seat_binding, Fingerprint):
            seat = seat_binding
        else:
            return invalid(
                "seat_binding",
                "a bot seat binding is a Fingerprint when present",
                given=repr(seat_binding),
            )
        if resolved_kind is EntityKind.BOT and seat is None:
            return invalid(
                "seat_binding",
                "a per-bot journal selector carries the Bot seat binding",
            )
        if resolved_kind is not EntityKind.BOT and seat is not None:
            return invalid(
                "seat_binding",
                "seat binding is present only on a bot selector; Book/BMS omit the key",
            )
        return _Ok(cls(kind=resolved_kind, entity_identity=entity_identity, seat_binding=seat))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this selector."""
        content: dict[str, object] = {
            "class": "entity-selector",
            "kind": self.kind.value,
            "entity_identity": self.entity_identity.value,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }
        if self.seat_binding is not None:
            content["seat_binding"] = self.seat_binding.value
        return content


def reject_entity_as_writer(selector: object) -> Result[None]:
    """Refuse treating an entity selector as a writer (DEC-0145).

    An entity holds no WriterId and mints no stream — projecting by inventing a
    writer from the selector is ``invalid input``.
    """
    if isinstance(selector, WriterId):
        return invalid(
            "selector",
            "entity journals are read-time projections; an entity holds no WriterId and "
            "mints no stream of its own",
            given="WriterId",
        )
    if isinstance(selector, EntitySelector):
        return _Ok(None)
    return invalid(
        "selector",
        "a projection selects by EntitySelector, never by inventing a WriterId",
        given=type_name(selector),
    )


# --- events ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskAuthoredEvent:
    """A risk-authored AD-21 event minted by the risk/node layer (DEC-0145).

    Always carries Book-definition fingerprint and binding identity. Bot identity
    plus seat are present only where the act concerns one bot. A decision event
    always carries a closed :class:`DecisionOutcome`.
    """

    event_type: JournalEventType
    book_definition_fingerprint: Fingerprint
    binding_identity: Fingerprint
    role: AccountRole
    sequence: int
    recorded_at: Instant
    payload_fingerprint: Fingerprint
    decision_outcome: DecisionOutcome | None
    bot_identity: Fingerprint | None
    seat_binding: Fingerprint | None
    suppressing_authority_ref: Fingerprint | None
    refusing_door_ref: Fingerprint | None

    @classmethod
    def try_create(
        cls,
        event_type: object,
        book_definition_fingerprint: object,
        binding_identity: object,
        role: object,
        sequence: object,
        recorded_at: object,
        payload_fingerprint: object,
        *,
        decision_outcome: object = None,
        bot_identity: object = None,
        seat_binding: object = None,
        suppressing_authority_ref: object = None,
        refusing_door_ref: object = None,
    ) -> Result[RiskAuthoredEvent]:
        """Validate and build a :class:`RiskAuthoredEvent`, value-or-refusal."""
        resolved_type = coerce_enum(JournalEventType, event_type)
        if resolved_type is None or resolved_type not in RISK_AUTHORED_EVENT_TYPES:
            return invalid(
                "event_type",
                "a risk-authored event is decision | risk transition | control action | promotion",
                given=repr(event_type),
                allowed=[member.value for member in RISK_AUTHORED_EVENT_TYPES],
            )
        if not isinstance(book_definition_fingerprint, Fingerprint):
            return invalid(
                "book_definition_fingerprint",
                "a risk-authored event always carries the Book-definition fingerprint",
                given=repr(book_definition_fingerprint),
            )
        if not isinstance(binding_identity, Fingerprint):
            return invalid(
                "binding_identity",
                "a risk-authored event always carries the binding identity",
                given=repr(binding_identity),
            )
        resolved_role = coerce_enum(AccountRole, role)
        if resolved_role is None:
            return invalid(
                "role",
                "role is present on every projected row",
                given=repr(role),
                allowed=[member.value for member in AccountRole],
            )
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return invalid(
                "sequence",
                "sequence is a non-negative int64, gapless per (writer unit, boot-epoch)",
                given=repr(sequence),
            )
        if not isinstance(recorded_at, Instant):
            return invalid(
                "recorded_at",
                "the event instant is an Instant",
                given=repr(recorded_at),
            )
        if not isinstance(payload_fingerprint, Fingerprint):
            return invalid(
                "payload_fingerprint",
                "the event payload is content-fingerprinted",
                given=repr(payload_fingerprint),
            )

        outcome: DecisionOutcome | None
        if resolved_type is JournalEventType.DECISION:
            outcome = coerce_enum(DecisionOutcome, decision_outcome)
            if outcome is None:
                return invalid(
                    "decision_outcome",
                    "a decision event always carries a closed outcome "
                    "(authorized | refused-by-door | suppressed), never key-absent",
                    given=repr(decision_outcome),
                    allowed=[member.value for member in DecisionOutcome],
                )
        elif decision_outcome is not None:
            return invalid(
                "decision_outcome",
                "decision_outcome is present only on a decision event",
                given=repr(decision_outcome),
            )
        else:
            outcome = None

        bot = _optional_fp(bot_identity, "bot_identity")
        if isinstance(bot, TypedRefusal):
            return bot
        seat = _optional_fp(seat_binding, "seat_binding")
        if isinstance(seat, TypedRefusal):
            return seat
        if (bot is None) != (seat is None):
            return invalid(
                "bot_identity",
                "Bot identity and seat binding are both present where the act concerns "
                "one bot, and both omitted otherwise",
            )

        suppressing = _optional_fp(suppressing_authority_ref, "suppressing_authority_ref")
        if isinstance(suppressing, TypedRefusal):
            return suppressing
        refusing = _optional_fp(refusing_door_ref, "refusing_door_ref")
        if isinstance(refusing, TypedRefusal):
            return refusing
        if outcome is DecisionOutcome.REFUSED_BY_DOOR and refusing is None:
            return invalid(
                "refusing_door_ref",
                "refused-by-door carries the refusing-door reference",
            )
        if outcome is DecisionOutcome.SUPPRESSED and suppressing is None:
            return invalid(
                "suppressing_authority_ref",
                "suppressed carries the suppressing-authority reference",
            )

        return _Ok(
            cls(
                event_type=resolved_type,
                book_definition_fingerprint=book_definition_fingerprint,
                binding_identity=binding_identity,
                role=resolved_role,
                sequence=sequence,
                recorded_at=recorded_at,
                payload_fingerprint=payload_fingerprint,
                decision_outcome=outcome,
                bot_identity=bot,
                seat_binding=seat,
                suppressing_authority_ref=suppressing,
                refusing_door_ref=refusing,
            )
        )

    @property
    def event_class(self) -> EventClass:
        """Risk-authored by construction."""
        return EventClass.RISK_AUTHORED

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this event."""
        content: dict[str, object] = {
            "class": "risk-authored-event",
            "event_type": self.event_type.value,
            "event_class": self.event_class.value,
            "book_definition_fingerprint": self.book_definition_fingerprint.value,
            "binding_identity": self.binding_identity.value,
            "role": self.role.value,
            "sequence": self.sequence,
            "recorded_at": self.recorded_at.fp1_identity(),
            "payload_fingerprint": self.payload_fingerprint.value,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }
        if self.decision_outcome is not None:
            content["decision_outcome"] = self.decision_outcome.value
        if self.bot_identity is not None and self.seat_binding is not None:
            content["bot_identity"] = self.bot_identity.value
            content["seat_binding"] = self.seat_binding.value
        if self.suppressing_authority_ref is not None:
            content["suppressing_authority_ref"] = self.suppressing_authority_ref.value
        if self.refusing_door_ref is not None:
            content["refusing_door_ref"] = self.refusing_door_ref.value
        return content


@dataclass(frozen=True, slots=True)
class VenueAuthoredEvent:
    """A venue-authored AD-21 event minted under the connection manager's WriterId.

    Always carries the command record's content fingerprint. **Never** carries Book
    identity — threading Book identity into a venue payload is forbidden (DEC-0145).
    """

    event_type: JournalEventType
    command_fingerprint: Fingerprint
    role: AccountRole
    sequence: int
    recorded_at: Instant
    payload_fingerprint: Fingerprint

    @classmethod
    def try_create(
        cls,
        event_type: object,
        command_fingerprint: object,
        role: object,
        sequence: object,
        recorded_at: object,
        payload_fingerprint: object,
        *,
        book_identity: object = None,
    ) -> Result[VenueAuthoredEvent]:
        """Validate and build a :class:`VenueAuthoredEvent`, value-or-refusal.

        Passing ``book_identity`` is refused — Book identity must never enter a
        venue-authored payload.
        """
        if book_identity is not None:
            return reject_book_identity_in_venue_payload(book_identity)
        resolved_type = coerce_enum(JournalEventType, event_type)
        if resolved_type is None or resolved_type not in VENUE_AUTHORED_EVENT_TYPES:
            return invalid(
                "event_type",
                "a venue-authored event is order | fill | data quality",
                given=repr(event_type),
                allowed=[member.value for member in VENUE_AUTHORED_EVENT_TYPES],
            )
        if not isinstance(command_fingerprint, Fingerprint):
            return invalid(
                "command_fingerprint",
                "a venue-authored event always carries the command record's content fingerprint",
                given=repr(command_fingerprint),
            )
        resolved_role = coerce_enum(AccountRole, role)
        if resolved_role is None:
            return invalid(
                "role",
                "role is present on every projected row",
                given=repr(role),
                allowed=[member.value for member in AccountRole],
            )
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return invalid(
                "sequence",
                "sequence is a non-negative int64, gapless per (writer unit, boot-epoch)",
                given=repr(sequence),
            )
        if not isinstance(recorded_at, Instant):
            return invalid(
                "recorded_at",
                "the event instant is an Instant",
                given=repr(recorded_at),
            )
        if not isinstance(payload_fingerprint, Fingerprint):
            return invalid(
                "payload_fingerprint",
                "the event payload is content-fingerprinted",
                given=repr(payload_fingerprint),
            )
        return _Ok(
            cls(
                event_type=resolved_type,
                command_fingerprint=command_fingerprint,
                role=resolved_role,
                sequence=sequence,
                recorded_at=recorded_at,
                payload_fingerprint=payload_fingerprint,
            )
        )

    @property
    def event_class(self) -> EventClass:
        """Venue-authored by construction."""
        return EventClass.VENUE_AUTHORED

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this event."""
        return {
            "class": "venue-authored-event",
            "event_type": self.event_type.value,
            "event_class": self.event_class.value,
            "command_fingerprint": self.command_fingerprint.value,
            "role": self.role.value,
            "sequence": self.sequence,
            "recorded_at": self.recorded_at.fp1_identity(),
            "payload_fingerprint": self.payload_fingerprint.value,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


def reject_book_identity_in_venue_payload(book_identity: object) -> TypedRefusal:
    """Refuse threading Book identity into a venue-authored payload (DEC-0145).

    The neutral venue port cannot carry Book identity and must not learn it; the
    join is through the command fingerprint instead.
    """
    return policy(
        "book_identity",
        "venue-authored events never carry Book identity; threading Book identity into "
        "a venue payload creates the qmf-venue→qmf-risk coupling the dependency rule "
        "forbids — join through the command-fingerprint instead",
        given=repr(book_identity),
    )


def _optional_fp(value: object, field: str) -> Fingerprint | TypedRefusal | None:
    if value is None:
        return None
    if isinstance(value, Fingerprint):
        return value
    return invalid(field, f"{field} is a Fingerprint when present", given=repr(value))


# --- command-fingerprint join ------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommandFingerprintJoin:
    """Pinned versioned join of a venue event to its risk-authored decision (DEC-0145).

    The venue event's ``command_fingerprint`` equals the command record's content
    fingerprint; the command record supplies the binding identity as an identity
    field. This join is CT-25 surface, not implementer judgment.
    """

    venue_event: VenueAuthoredEvent
    command_fingerprint: Fingerprint
    binding_identity: Fingerprint
    risk_decision: RiskAuthoredEvent
    join_version: int

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this join."""
        return {
            "class": "command-fingerprint-join",
            "venue_event": self.venue_event.fp1_identity(),
            "command_fingerprint": self.command_fingerprint.value,
            "binding_identity": self.binding_identity.value,
            "risk_decision": self.risk_decision.fp1_identity(),
            "join_version": self.join_version,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


def join_via_command_fingerprint(
    venue_event: object,
    *,
    command_fingerprint: object,
    binding_identity: object,
    risk_decision: object,
) -> Result[CommandFingerprintJoin]:
    """Join a venue-authored event to its risk-authored decision (DEC-0145).

    Equality of fingerprints is the only legal join; Book identity never enters the
    venue side.
    """
    if not isinstance(venue_event, VenueAuthoredEvent):
        return invalid(
            "venue_event",
            "the join starts from a VenueAuthoredEvent",
            given=type_name(venue_event),
        )
    if not isinstance(command_fingerprint, Fingerprint):
        return invalid(
            "command_fingerprint",
            "the command record's content fingerprint is a Fingerprint",
            given=repr(command_fingerprint),
        )
    if not isinstance(binding_identity, Fingerprint):
        return invalid(
            "binding_identity",
            "the command record supplies the binding identity as an identity field",
            given=repr(binding_identity),
        )
    if not isinstance(risk_decision, RiskAuthoredEvent):
        return invalid(
            "risk_decision",
            "the join targets a RiskAuthoredEvent decision",
            given=type_name(risk_decision),
        )
    if risk_decision.event_type is not JournalEventType.DECISION:
        return invalid(
            "risk_decision",
            "the command-fingerprint join targets a decision event",
            given=risk_decision.event_type.value,
        )
    if venue_event.command_fingerprint != command_fingerprint:
        return invalid(
            "command_fingerprint",
            "venue-authored command_fingerprint must equal the command record's "
            "content fingerprint (pinned CT-25 join)",
            venue=venue_event.command_fingerprint.value,
            command=command_fingerprint.value,
        )
    if risk_decision.binding_identity != binding_identity:
        return invalid(
            "binding_identity",
            "the risk-authored decision's binding identity must equal the command "
            "record's binding identity",
            decision=risk_decision.binding_identity.value,
            command=binding_identity.value,
        )
    return _Ok(
        CommandFingerprintJoin(
            venue_event=venue_event,
            command_fingerprint=command_fingerprint,
            binding_identity=binding_identity,
            risk_decision=risk_decision,
            join_version=CT25_COMMAND_FINGERPRINT_JOIN_VERSION,
        )
    )


# --- projections -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectedJournalRow:
    """One row of an entity-journal projection — role always present (DEC-0145)."""

    event_type: JournalEventType
    event_class: EventClass
    role: AccountRole
    sequence: int
    recorded_at: Instant
    payload_fingerprint: Fingerprint
    source: RiskAuthoredEvent | VenueAuthoredEvent

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this projected row."""
        return {
            "class": "projected-journal-row",
            "event_type": self.event_type.value,
            "event_class": self.event_class.value,
            "role": self.role.value,
            "sequence": self.sequence,
            "recorded_at": self.recorded_at.fp1_identity(),
            "payload_fingerprint": self.payload_fingerprint.value,
            "source": self.source.fp1_identity(),
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class EntityJournalProjection:
    """A read-time projection over writer-scoped streams for one entity (DEC-0145)."""

    selector: EntitySelector
    role_scope: AccountRole
    cross_role_declared: bool
    rows: tuple[ProjectedJournalRow, ...]
    mapping_table_version: int

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of this projection declaration."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this projection."""
        return {
            "class": "entity-journal-projection",
            "selector": self.selector.fp1_identity(),
            "role_scope": self.role_scope.value,
            "cross_role_declared": self.cross_role_declared,
            "rows": [row.fp1_identity() for row in self.rows],
            "mapping_table_version": self.mapping_table_version,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class WriterScopedStream:
    """One AD-21 writer-scoped event stream a projection reads over (DEC-0145).

    The stream is owned by a :class:`~qmf.core.WriterId`; the entity never owns it.
    """

    writer_id: WriterId
    events: tuple[RiskAuthoredEvent | VenueAuthoredEvent, ...]

    @classmethod
    def try_create(cls, writer_id: object, events: object) -> Result[WriterScopedStream]:
        """Validate and build a :class:`WriterScopedStream`, value-or-refusal."""
        if not isinstance(writer_id, WriterId):
            return invalid(
                "writer_id",
                "a writer-scoped stream is owned by a WriterId; an entity holds none",
                given=type_name(writer_id),
            )
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            return invalid(
                "events",
                "a writer-scoped stream carries a sequence of journal events",
                given=type_name(events),
            )
        resolved: list[RiskAuthoredEvent | VenueAuthoredEvent] = []
        for index, item in enumerate(cast("Sequence[object]", events)):
            if not isinstance(item, (RiskAuthoredEvent, VenueAuthoredEvent)):
                return invalid(
                    "events",
                    "every stream member is a RiskAuthoredEvent or VenueAuthoredEvent",
                    index=index,
                    given=type_name(item),
                )
            resolved.append(item)
        return _Ok(cls(writer_id=writer_id, events=tuple(resolved)))


def reject_cross_role_silent_union(
    *,
    role_scope: object,
    observed_roles: object,
    cross_role_declared: object,
) -> Result[None]:
    """Refuse a silent cross-role aggregation (DEC-0145, DEC-0158).

    A projection resolves inside one role-scoped namespace. A cross-role read is
    permitted only with an explicit declaration; otherwise it is ``invalid input``.
    """
    resolved_scope = coerce_enum(AccountRole, role_scope)
    if resolved_scope is None:
        return invalid(
            "role_scope",
            "a projection resolves inside one role-scoped namespace",
            given=repr(role_scope),
            allowed=[member.value for member in AccountRole],
        )
    if not isinstance(cross_role_declared, bool):
        return invalid(
            "cross_role_declared",
            "cross_role_declared is a bool naming an explicit declaration",
            given=repr(cross_role_declared),
        )
    if not isinstance(observed_roles, Sequence) or isinstance(observed_roles, (str, bytes)):
        return invalid(
            "observed_roles",
            "observed_roles is a sequence of AccountRole values",
            given=type_name(observed_roles),
        )
    roles: set[AccountRole] = set()
    for index, item in enumerate(cast("Sequence[object]", observed_roles)):
        role = coerce_enum(AccountRole, item)
        if role is None:
            return invalid(
                "observed_roles",
                "every observed role is an AccountRole",
                index=index,
                given=repr(item),
            )
        roles.add(role)
    foreign = roles - {resolved_scope}
    if foreign and not cross_role_declared:
        return invalid(
            "cross_role_declared",
            "a cross-role projection without an explicit declaration is refused — "
            "never a silent union across roles",
            role_scope=resolved_scope.value,
            foreign_roles=sorted(role.value for role in foreign),
        )
    return _Ok(None)


def _row_from_event(event: RiskAuthoredEvent | VenueAuthoredEvent) -> ProjectedJournalRow:
    return ProjectedJournalRow(
        event_type=event.event_type,
        event_class=event.event_class,
        role=event.role,
        sequence=event.sequence,
        recorded_at=event.recorded_at,
        payload_fingerprint=event.payload_fingerprint,
        source=event,
    )


def _matches_selector(
    event: RiskAuthoredEvent | VenueAuthoredEvent, selector: EntitySelector
) -> bool:
    if isinstance(event, VenueAuthoredEvent):
        # Venue events join through the command fingerprint at project time; a bare
        # stream scan includes them when the projection asks for venue types — the
        # caller's joined set supplies the entity association. For an unjoined stream
        # scan, venue events pass through when the selector is Book/BMS (logbook
        # includes venue traffic) and are filtered for bot-only when seat is required
        # without a prior join. CT-25 pins the join; inclusion here is type-gated.
        return selector.kind is not EntityKind.BOT
    if selector.kind is EntityKind.BOOK:
        return event.book_definition_fingerprint == selector.entity_identity
    if selector.kind is EntityKind.BMS:
        # BMS identity rides the binding; the selector's entity_identity is the BMS
        # fingerprint the composition root associates — match binding for V1.
        return event.binding_identity == selector.entity_identity
    # BOT
    return (
        event.bot_identity == selector.entity_identity
        and event.seat_binding == selector.seat_binding
    )


def project_entity_journal(
    selector: object,
    streams: object,
    *,
    role_scope: object,
    cross_role_declared: object = False,
    event_types: object = None,
) -> Result[EntityJournalProjection]:
    """Project writer-scoped streams into an entity journal (DEC-0145).

    The selector is never a WriterId. Role rides every row; a foreign role without
    ``cross_role_declared=True`` is refused.
    """
    as_writer = reject_entity_as_writer(selector)
    if is_refusal(as_writer):
        return as_writer
    if not isinstance(selector, EntitySelector):
        return invalid(
            "selector",
            "project_entity_journal selects by EntitySelector",
            given=type_name(selector),
        )
    resolved_scope = coerce_enum(AccountRole, role_scope)
    if resolved_scope is None:
        return invalid(
            "role_scope",
            "a projection resolves inside one role-scoped namespace",
            given=repr(role_scope),
            allowed=[member.value for member in AccountRole],
        )
    if not isinstance(cross_role_declared, bool):
        return invalid(
            "cross_role_declared",
            "cross_role_declared is a bool",
            given=repr(cross_role_declared),
        )
    if not isinstance(streams, Sequence) or isinstance(streams, (str, bytes)):
        return invalid(
            "streams",
            "a projection reads a sequence of WriterScopedStream values",
            given=type_name(streams),
        )

    allowed_types: frozenset[JournalEventType] | None
    if event_types is None:
        allowed_types = None
    elif isinstance(event_types, (set, frozenset)):
        resolved_types: set[JournalEventType] = set()
        for item in cast("set[object] | frozenset[object]", event_types):
            et = coerce_enum(JournalEventType, item)
            if et is None:
                return invalid(
                    "event_types",
                    "event_types members are AD-21 journal event types",
                    given=repr(item),
                )
            resolved_types.add(et)
        allowed_types = frozenset(resolved_types)
    else:
        return invalid(
            "event_types",
            "event_types is a set of JournalEventType when provided",
            given=type_name(event_types),
        )

    rows: list[ProjectedJournalRow] = []
    observed_roles: list[AccountRole] = []
    for index, stream in enumerate(cast("Sequence[object]", streams)):
        if not isinstance(stream, WriterScopedStream):
            return invalid(
                "streams",
                "every member is a WriterScopedStream owned by a WriterId",
                index=index,
                given=type_name(stream),
            )
        for event in stream.events:
            if allowed_types is not None and event.event_type not in allowed_types:
                continue
            if not _matches_selector(event, selector):
                continue
            observed_roles.append(event.role)
            if event.role is not resolved_scope and not cross_role_declared:
                return invalid(
                    "cross_role_declared",
                    "a cross-role projection without an explicit declaration is refused — "
                    "never a silent union across roles",
                    role_scope=resolved_scope.value,
                    foreign_roles=[event.role.value],
                )
            if event.role is not resolved_scope and cross_role_declared:
                # Explicit cross-role: keep the row with its own role stamped.
                rows.append(_row_from_event(event))
                continue
            if event.role is resolved_scope:
                rows.append(_row_from_event(event))

    check = reject_cross_role_silent_union(
        role_scope=resolved_scope,
        observed_roles=observed_roles,
        cross_role_declared=cross_role_declared,
    )
    if is_refusal(check):
        return check

    rows.sort(key=lambda row: (row.recorded_at.value_ns, row.sequence))
    return _Ok(
        EntityJournalProjection(
            selector=selector,
            role_scope=resolved_scope,
            cross_role_declared=cross_role_declared,
            rows=tuple(rows),
            mapping_table_version=CT25_MAPPING_TABLE_VERSION,
        )
    )


def project_legacy(
    name: object,
    streams: object,
    *,
    selector: object,
    role_scope: object,
    cross_role_declared: object = False,
) -> Result[EntityJournalProjection]:
    """Project under a legacy Records name via the versioned mapping table (DEC-0145).

    ``veto_ledger`` further selects ``decision.outcome == refused-by-door``, never
    on key presence.
    """
    mapped = map_legacy_projection(name)
    if is_refusal(mapped):
        return mapped
    projected = project_entity_journal(
        selector,
        streams,
        role_scope=role_scope,
        cross_role_declared=cross_role_declared,
        event_types=mapped.value,
    )
    if is_refusal(projected):
        return projected
    resolved_name = coerce_enum(LegacyProjectionName, name)
    if resolved_name is LegacyProjectionName.VETO_LEDGER:
        filtered = tuple(
            row
            for row in projected.value.rows
            if isinstance(row.source, RiskAuthoredEvent)
            and row.source.decision_outcome is DecisionOutcome.REFUSED_BY_DOOR
        )
        return _Ok(
            EntityJournalProjection(
                selector=projected.value.selector,
                role_scope=projected.value.role_scope,
                cross_role_declared=projected.value.cross_role_declared,
                rows=filtered,
                mapping_table_version=projected.value.mapping_table_version,
            )
        )
    return projected


# --- block-on-unpersistable --------------------------------------------------


def block_dispatch_on_journal_failure(
    record: object, *, journal_result: object
) -> Result[ControlActionRecord]:
    """Journal a control action before dispatch — storage failure blocks it (DEC-0145).

    Block-on-unpersistable binds the risk dispatcher exactly as it binds the
    connection manager: the dispatcher must see a sink refusal rather than losing
    the intent. Delegates to :func:`~qmf.risk.control_action.journal_before_dispatch`
    and surfaces storage failure explicitly via :func:`~qmf.core.is_unpersistable`.
    """
    gated = journal_before_dispatch(record, journal_result=journal_result)
    if is_refusal(gated) and is_unpersistable(gated):
        return gated
    return gated
