"""CT-25 — read-time entity-journal projections (logbooks), owned by COMP-QMF-DATA.

The Book journal, the BMS journal, and the per-bot journal — the operator's logbook —
are **declared read-time projections** over the AD-21 writer-scoped journal streams
Story 3.5 records, selected by **entity identity**. An entity holds no ``WriterId`` and
mints no stream of its own; per-entity, per-binding, and combined views are all extracted
on demand from the one recorded set of writer-scoped streams (AC1; DEC-0145). This module
is **read-only**: it never writes, and nothing here becomes an additional journal writer.

Four things this module pins down.

**Entity journals are projections, never writers (AC1; DEC-0145, DEC-0158).** A projection
is a selection over the recorded :class:`~qmf.data.journal.JournalEvent` streams keyed by
an :class:`EntitySelector` — a Book instance, a BMS instance, a Bot definition + seat, or a
full binding. :func:`entity_journal` (and the :func:`book_journal` / :func:`bms_journal` /
:func:`bot_logbook` conveniences) resolves the one recorded set of streams into a
:class:`Logbook`; the same recorded set yields many views, and no view is a stream.

**Two event classes, split because the neutral venue port cannot carry Book identity and
must not learn it (AC2; DEC-0145, DEC-0143, DEC-0173).** :func:`event_class_of` maps each
of the seven types to a :class:`EventClass`. **Risk-authored** events (decision, risk
transition, control action, promotion) carry the Book-definition fingerprint, the binding
identity ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)``, and — where one
bot is concerned — the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding, as
identity fields modelled generically on ``qmf-core`` nouns (no risk/QML type is imported —
they arrive in later epics). **Venue-authored** events (order, fill, data quality) carry
**only** the command record's content fingerprint; threading Book identity into the neutral
venue payload is a refusal (:func:`guard_neutral_venue_payload`). A Book projection that
must include orders and fills joins venue-authored events through the pinned versioned
command-fingerprint join (:class:`CommandIndex`), never by learning Book identity.

**Paper and live are separated by construction (AC3; FM-11, DEC-0145, DEC-0158).** A
projection resolves inside one **role-scoped namespace** (:func:`role_namespace`): the live
evidence namespace admits only ``role = live`` rows; demo, paper-validation, and
paper-benched rows resolve in their own role-scoped namespaces. Aggregating across account
roles **without** an explicitly-declared cross-role read is a ``policy rejection`` refusal
(FM-11). Only the two declared exceptions span roles — the AD-35 decay-cohort read
(:func:`decay_cohort_read`, DEC-0149) and the multi-role entity projection
(``cross_role=MULTI_ROLE_ENTITY``) — each carrying ``role`` on every projected row. There
is no write exception ever; this module never writes.

**The legacy five Records streams survive as projection names only (AC4; DEC-0145).**
``veto_ledger``, ``trade_journal``, ``book_journal``, ``ksa_audit_log``, and
``correlation_ledger`` are :class:`RecordsStreamName` projection names mapped onto the seven
journal event types by the **one** versioned :data:`RECORDS_STREAM_MAPPING` table — no
second event catalog is minted (:func:`records_stream`). ``veto_ledger`` selects on the
decision event's declared ``outcome = refused-by-door`` field, never on key presence.

Stdlib + qmf-core + the qmf-data journal vocabulary; frozen, immutable values throughout.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import (
    LIVE_EVIDENCE_NAMESPACE,
    AccountRole,
    Fingerprint,
    Ok,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.data.journal import (
    DecisionOutcome,
    JournalEvent,
    JournalEventType,
    select_decisions,
)
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ACCOUNT_ID_KEY",
    "BMS_INSTANCE_ID_KEY",
    "BOOK_DEFINITION_FP_KEY",
    "BOOK_IDENTITY_FIELDS",
    "BOOK_INSTANCE_ID_KEY",
    "BOT_DEFINITION_FP_KEY",
    "COMMAND_FINGERPRINT_KEY",
    "CT25_CONTRACT_FORMAT_VERSION",
    "RECORDS_STREAM_MAPPING",
    "ROLE_KEY",
    "SEAT_BINDING_KEY",
    "VENUE_ID_KEY",
    "BindingIdentity",
    "BotSeat",
    "CommandAttribution",
    "CommandIndex",
    "CrossRoleRead",
    "EntityKind",
    "EntitySelector",
    "EventClass",
    "Logbook",
    "ProjectedRow",
    "RecordsStreamName",
    "RecordsStreamRule",
    "bms_journal",
    "book_journal",
    "bot_logbook",
    "decay_cohort_read",
    "entity_journal",
    "event_class_of",
    "guard_neutral_venue_payload",
    "read_binding",
    "read_bot_seat",
    "read_command_fingerprint",
    "read_role",
    "records_stream",
    "role_namespace",
]

# CT-25's own integer contract format version (the yaml's version: 1). The
# records-stream mapping table and the command-fingerprint join are each pinned
# versioned surface; a change to either is a format-version mint plus a migration
# note (DEC-0145; versioning-from-birth L15). CT-25's own, not CT-13's.
CT25_CONTRACT_FORMAT_VERSION: Final[int] = 1

# --- the pinned CT-25 payload-key surface -----------------------------------
# The identity fields ride the journal event's fp1-identity payload under these
# exact keys. They are the versioned CT-25 surface a producer (qmf-risk / qmf-venue,
# in later epics) stamps and a projection reads — never an implementer's per-call
# choice (DEC-0145). Modelled generically on qmf-core nouns: VenueId and World are
# qmf-core types; the instance ids and seat binding are opaque tokens (the same
# shape qmf-core uses for account_id and venue tokens); the definition/command
# fingerprints are qmf-core Fingerprints.
BOOK_DEFINITION_FP_KEY: Final[str] = "book_definition_fp"
BOOK_INSTANCE_ID_KEY: Final[str] = "book_instance_id"
BMS_INSTANCE_ID_KEY: Final[str] = "bms_instance_id"
VENUE_ID_KEY: Final[str] = "venue_id"
ACCOUNT_ID_KEY: Final[str] = "account_id"
BOT_DEFINITION_FP_KEY: Final[str] = "bot_definition_fp"
SEAT_BINDING_KEY: Final[str] = "seat_binding"
ROLE_KEY: Final[str] = "role"
COMMAND_FINGERPRINT_KEY: Final[str] = "command_fingerprint"

# The Book/Bot identity fields that must NEVER appear in a venue-authored payload:
# Book identity is joined through the command fingerprint, never threaded into the
# neutral venue port (AC2; DEC-0145, DEC-0120). VenueId, account_id, and role are
# NOT in this set — a venue legitimately knows the account/venue it acted for, and
# role rides every projected row.
BOOK_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        BOOK_DEFINITION_FP_KEY,
        BOOK_INSTANCE_ID_KEY,
        BMS_INSTANCE_ID_KEY,
        BOT_DEFINITION_FP_KEY,
        SEAT_BINDING_KEY,
    }
)

# The four keys that together make one binding identity; a projection reads all four
# or none (a partial binding is a malformed risk-authored payload).
_BINDING_KEYS: Final[tuple[str, ...]] = (
    BOOK_INSTANCE_ID_KEY,
    BMS_INSTANCE_ID_KEY,
    VENUE_ID_KEY,
    ACCOUNT_ID_KEY,
)


# --- small coercers (return value-or-None; the caller mints the one refusal) --


def _clean_token(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _coerce_venue_id(value: object) -> VenueId | None:
    """Resolve a :class:`~qmf.core.VenueId` (or its opaque string token), else ``None``."""
    if isinstance(value, VenueId):
        return value if value.value.strip() != "" else None
    if isinstance(value, str):
        built = VenueId.try_create(value)
        return built.value if is_ok(built) else None
    return None


def _coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`~qmf.core.World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _coerce_role(value: object) -> AccountRole | None:
    """Resolve ``value`` to an :class:`~qmf.core.AccountRole` member, or ``None``."""
    if isinstance(value, AccountRole):
        return value
    if isinstance(value, str):
        try:
            return AccountRole(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


# --- event class (the CT-25 risk-authored / venue-authored split) -----------


class EventClass(StrEnum):
    """Which authoring layer minted an AD-21 event (CT-25 ``event_class``; DEC-0145).

    ``RISK_AUTHORED`` events (decision, risk transition, control action, promotion) are
    minted by the risk/node layer and carry the Book-definition fingerprint and binding
    identity as identity fields. ``VENUE_AUTHORED`` events (order, fill, data quality) are
    minted by the connection manager under its own ``WriterId`` and carry only the command
    record's content fingerprint — never Book identity.
    """

    RISK_AUTHORED = "risk-authored"
    VENUE_AUTHORED = "venue-authored"


_EVENT_CLASS_OF: Final[Mapping[JournalEventType, EventClass]] = MappingProxyType(
    {
        JournalEventType.DECISION: EventClass.RISK_AUTHORED,
        JournalEventType.RISK_TRANSITION: EventClass.RISK_AUTHORED,
        JournalEventType.CONTROL_ACTION: EventClass.RISK_AUTHORED,
        JournalEventType.PROMOTION: EventClass.RISK_AUTHORED,
        JournalEventType.ORDER: EventClass.VENUE_AUTHORED,
        JournalEventType.FILL: EventClass.VENUE_AUTHORED,
        JournalEventType.DATA_QUALITY: EventClass.VENUE_AUTHORED,
    }
)


def event_class_of(event_type: JournalEventType) -> EventClass:
    """The CT-25 event class of one of the seven journal event types (AC2; DEC-0145).

    A total mapping over :class:`~qmf.data.journal.JournalEventType`; every one of the
    seven ratified types resolves to exactly one :class:`EventClass`.
    """
    return _EVENT_CLASS_OF[event_type]


# --- role-scoped namespaces (AC3) -------------------------------------------


def role_namespace(role: object) -> Result[str]:
    """The role-scoped namespace a projected row of this account role resolves in (AC3).

    Paper and live are separated by construction: ``role = live`` resolves to the
    :data:`~qmf.core.LIVE_EVIDENCE_NAMESPACE` (which admits **only** ``role = live`` rows),
    and every other role — demo, paper-validation, paper-benched, prop-firm — resolves to
    its **own** role-scoped namespace named by the role. Because the namespace is derived
    from the role, a non-live role can never resolve to the live evidence namespace, so
    paper and demo evidence never lands in the live namespace (DEC-0145, DEC-0158). A value
    outside the closed :class:`~qmf.core.AccountRole` set is an ``invalid input`` refusal.
    """
    resolved = _coerce_role(role)
    if resolved is None:
        return invalid_input(
            "role",
            "role is one of the closed AccountRole set; a role-scoped namespace exists for "
            "each so paper and live never share a namespace (DEC-0158)",
            given=repr(role),
            allowed=[member.value for member in AccountRole],
        )
    if resolved is AccountRole.LIVE:
        return Ok(LIVE_EVIDENCE_NAMESPACE)
    return Ok(resolved.value)


class CrossRoleRead(StrEnum):
    """The two — and only two — declared cross-role reads permitted (AC3; DEC-0145).

    A projection spanning account roles exists only as one of these explicitly-declared
    reads, never a silent union. ``DECAY_COHORT`` is the AD-35 decay-cohort read (DEC-0149);
    ``MULTI_ROLE_ENTITY`` is the entity projection over an entity that operated in more than
    one role — a benched seat inside a live Book is the ordinary case. Both carry ``role`` on
    every projected row; there is no write exception ever (DEC-0158).
    """

    DECAY_COHORT = "decay-cohort"
    MULTI_ROLE_ENTITY = "multi-role-entity"


def _coerce_cross_role(value: object) -> CrossRoleRead | None:
    """Resolve ``value`` to a :class:`CrossRoleRead` member, or ``None``."""
    if isinstance(value, CrossRoleRead):
        return value
    if isinstance(value, str):
        try:
            return CrossRoleRead(value)
        except ValueError:
            return None
    return None


# --- binding identity and bot seat (generic qmf-core-noun identity) ---------


@dataclass(frozen=True, slots=True)
class BindingIdentity:
    """The binding identity ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)``
    carried by every risk-authored event as identity fields (AC2; DEC-0145, DEC-0143).

    Modelled generically on ``qmf-core`` nouns — :class:`~qmf.core.VenueId` and
    :class:`~qmf.core.World` are qmf-core types; the Book and BMS instance ids and the
    account id are opaque tokens (the same shape qmf-core uses for account and venue
    tokens). No risk/QML type is imported: those arrive in later epics, and this value is
    the generic carrier a projection resolves by. The unchecked constructor is the
    trusted-internal path; :meth:`try_create` validates every part.
    """

    book_instance_id: str
    bms_instance_id: str
    venue_id: VenueId
    account_id: str
    world: World

    @classmethod
    def try_create(
        cls,
        *,
        book_instance_id: object,
        bms_instance_id: object,
        venue_id: object,
        account_id: object,
        world: object,
    ) -> Result[BindingIdentity]:
        """Validate and build a :class:`BindingIdentity`, returning value-or-refusal."""
        book = _clean_token(book_instance_id)
        if book is None:
            return invalid_input(
                "book_instance_id",
                "a binding identity carries a non-blank opaque BookInstanceId",
                given=repr(book_instance_id),
            )
        bms = _clean_token(bms_instance_id)
        if bms is None:
            return invalid_input(
                "bms_instance_id",
                "a binding identity carries a non-blank opaque BmsInstanceId",
                given=repr(bms_instance_id),
            )
        venue = _coerce_venue_id(venue_id)
        if venue is None:
            return invalid_input(
                "venue_id",
                "a binding identity carries a valid qmf-core VenueId (or its opaque token)",
                given=repr(venue_id),
            )
        account = _clean_token(account_id)
        if account is None:
            return invalid_input(
                "account_id",
                "a binding identity carries a non-blank opaque AccountId",
                given=repr(account_id),
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return invalid_input(
                "world",
                "a binding identity carries one of the closed set live | replay | simulated",
                given=repr(world),
            )
        return Ok(
            cls(
                book_instance_id=book,
                bms_instance_id=bms,
                venue_id=venue,
                account_id=account,
                world=resolved_world,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The binding's canonical ``fp1`` identity content (the parts that ARE its identity)."""
        return {
            "class": "binding-identity",
            "book_instance_id": self.book_instance_id,
            "bms_instance_id": self.bms_instance_id,
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "world": self.world.value,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class BotSeat:
    """A per-bot identity — the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding
    (AC2; DEC-0145, DEC-0173).

    Carried on a risk-authored event **where one bot is concerned**, and the identity a
    per-bot journal (the operator's logbook) resolves by. The Bot definition ``fp1`` is a
    qmf-core :class:`~qmf.core.Fingerprint`; the seat binding is an opaque AD-41 token — no
    QML type is imported.
    """

    bot_definition_fp: Fingerprint
    seat_binding: str


# --- reading the pinned identity fields off an event ------------------------


def read_role(event: JournalEvent) -> Result[AccountRole]:
    """Read the account ``role`` a projected row carries (AC3; DEC-0158).

    Every projected row carries ``role`` under the pinned :data:`ROLE_KEY`, so a projection
    can never silently aggregate across roles. A missing or out-of-set role is an ``invalid
    input`` refusal — a matched row without a declared role must not be projected.
    """
    resolved = _coerce_role(event.payload.get(ROLE_KEY))
    if resolved is None:
        return invalid_input(
            "role",
            "every projected journal row carries a closed AccountRole under the pinned "
            "'role' key so a projection never aggregates across roles silently (DEC-0158)",
            given=repr(event.payload.get(ROLE_KEY)),
            allowed=[member.value for member in AccountRole],
        )
    return Ok(resolved)


def read_binding(event: JournalEvent) -> Result[BindingIdentity]:
    """Read the binding identity a risk-authored event carries (AC2; DEC-0145, DEC-0143).

    Reads the four binding tokens from the event's payload under the pinned keys and folds
    in the event's own ``world`` as the binding's world (the event already carries world in
    identity, so it is never duplicated into the payload). A missing or malformed part is an
    ``invalid input`` refusal; callers that must tolerate a risk-authored event carrying no
    binding at all (e.g. a qmf-data control action) check presence first.
    """
    payload = event.payload
    return BindingIdentity.try_create(
        book_instance_id=payload.get(BOOK_INSTANCE_ID_KEY),
        bms_instance_id=payload.get(BMS_INSTANCE_ID_KEY),
        venue_id=payload.get(VENUE_ID_KEY),
        account_id=payload.get(ACCOUNT_ID_KEY),
        world=event.world,
    )


def read_bot_seat(event: JournalEvent) -> Result[BotSeat | None]:
    """Read the optional per-bot identity a risk-authored event carries (AC2; DEC-0173).

    Returns ``Ok(None)`` when neither bot key is present (the act concerns no single bot),
    ``Ok(BotSeat)`` when both are present and valid, and an ``invalid input`` refusal for a
    **partial** bot identity (one key without the other, or a malformed fingerprint / blank
    seat) — a half-declared bot seat is a producer wiring mistake, not an omitted key.
    """
    fp_raw = event.payload.get(BOT_DEFINITION_FP_KEY)
    seat_raw = event.payload.get(SEAT_BINDING_KEY)
    if fp_raw is None and seat_raw is None:
        return Ok(None)
    fp = _coerce_fingerprint(fp_raw)
    if fp is None:
        return invalid_input(
            "bot_definition_fp",
            "a per-bot identity carries the CT-33 Bot definition fp1 (fp1:sha256:<hex>) "
            "alongside its AD-41 seat binding (DEC-0173)",
            given=repr(fp_raw),
        )
    seat = _clean_token(seat_raw)
    if seat is None:
        return invalid_input(
            "seat_binding",
            "a per-bot identity carries a non-blank AD-41 seat binding alongside the "
            "Bot definition fp1 (DEC-0173)",
            given=repr(seat_raw),
        )
    return Ok(BotSeat(bot_definition_fp=fp, seat_binding=seat))


def guard_neutral_venue_payload(event: JournalEvent) -> Result[None]:
    """Refuse a venue-authored event whose payload carries Book/Bot identity (AC2; DEC-0145).

    The neutral venue port cannot carry Book identity and must not learn it: Book identity
    is joined through the command fingerprint (:class:`CommandIndex`), never threaded into
    the venue payload — doing so would create the ``qmf-venue -> qmf-risk`` coupling
    default-deny forbids (DEC-0120). Any :data:`BOOK_IDENTITY_FIELDS` key found in the
    payload is an ``invalid input`` refusal naming the leaked fields.
    """
    leaked = sorted(key for key in BOOK_IDENTITY_FIELDS if key in event.payload)
    if leaked:
        return invalid_input(
            "payload",
            "a venue-authored event's neutral payload must never carry Book/Bot identity; "
            "Book identity is joined through the command fingerprint (CT-25), never threaded "
            "into the venue payload (DEC-0145, DEC-0120)",
            leaked_fields=leaked,
            event_type=event.event_type.value,
        )
    return Ok(None)


def read_command_fingerprint(event: JournalEvent) -> Result[Fingerprint]:
    """Read the command record's content fingerprint a venue-authored event carries (AC2).

    First guards the neutral payload (:func:`guard_neutral_venue_payload`) — a leaked Book
    identity is refused — then reads the command fingerprint under the pinned
    :data:`COMMAND_FINGERPRINT_KEY`. A missing or malformed fingerprint is an ``invalid
    input`` refusal. This is the venue half of the pinned versioned command-fingerprint join
    (DEC-0145, DEC-0143).
    """
    guard = guard_neutral_venue_payload(event)
    if is_refusal(guard):
        return guard
    fp = _coerce_fingerprint(event.payload.get(COMMAND_FINGERPRINT_KEY))
    if fp is None:
        return invalid_input(
            "command_fingerprint",
            "a venue-authored event carries the command record's content fingerprint "
            "(fp1:sha256:<hex>), the join key to its risk-authored decision (DEC-0145)",
            given=repr(event.payload.get(COMMAND_FINGERPRINT_KEY)),
        )
    return Ok(fp)


def _binding_presence(payload: Mapping[str, object]) -> int:
    """How many of the four binding-identity keys the payload carries."""
    return sum(1 for key in _BINDING_KEYS if key in payload)


def _optional_binding(event: JournalEvent) -> BindingIdentity | None:
    """The binding identity if the event carries all four keys validly, else ``None``.

    A risk-authored event that declares no binding (zero binding keys) is not attributable
    to a binding and returns ``None``; a fully-present, valid binding is returned. A partial
    binding is treated as absent here (the strict :func:`read_binding` surfaces the malformed
    case where the selection path needs it).
    """
    if _binding_presence(event.payload) == 0:
        return None
    built = read_binding(event)
    return built.value if is_ok(built) else None


def _optional_bot_seat(event: JournalEvent) -> BotSeat | None:
    """The per-bot identity if validly present, else ``None`` (a malformed seat reads None)."""
    built = read_bot_seat(event)
    return built.value if is_ok(built) else None


# --- entity selection -------------------------------------------------------


class EntityKind(StrEnum):
    """The kind of entity a projection is selected by (AC1; DEC-0145).

    ``BOOK`` / ``BMS`` resolve from the binding identity every risk-authored event carries;
    ``BOT`` resolves from the CT-33 Bot definition fp1 plus seat binding; ``BINDING`` is the
    combined view selected by the full binding tuple.
    """

    BOOK = "book"
    BMS = "bms"
    BOT = "bot"
    BINDING = "binding"


@dataclass(frozen=True, slots=True)
class EntitySelector:
    """The entity identity a read-time projection selects by (AC1; DEC-0145, DEC-0158).

    A selector is **not** a ``WriterId`` and names no stream — it is the identity a
    projection resolves over the recorded writer-scoped streams. Build one through a factory:
    :meth:`for_book`, :meth:`for_bms`, :meth:`for_bot`, or :meth:`for_binding` (the combined
    view). The unchecked constructor is the trusted-internal path.
    """

    kind: EntityKind
    book_instance_id: str | None = None
    bms_instance_id: str | None = None
    bot_seat: BotSeat | None = None
    binding: BindingIdentity | None = None

    @classmethod
    def for_book(cls, book_instance_id: object) -> Result[EntitySelector]:
        """Select the Book journal for one Book instance (AC1; DEC-0145)."""
        book = _clean_token(book_instance_id)
        if book is None:
            return invalid_input(
                "book_instance_id",
                "a Book projection is selected by a non-blank BookInstanceId",
                given=repr(book_instance_id),
            )
        return Ok(cls(kind=EntityKind.BOOK, book_instance_id=book))

    @classmethod
    def for_bms(cls, bms_instance_id: object) -> Result[EntitySelector]:
        """Select the BMS journal for one BMS instance (AC1; DEC-0145)."""
        bms = _clean_token(bms_instance_id)
        if bms is None:
            return invalid_input(
                "bms_instance_id",
                "a BMS projection is selected by a non-blank BmsInstanceId",
                given=repr(bms_instance_id),
            )
        return Ok(cls(kind=EntityKind.BMS, bms_instance_id=bms))

    @classmethod
    def for_bot(cls, bot_definition_fp: object, seat_binding: object) -> Result[EntitySelector]:
        """Select the per-bot journal (the operator's logbook) for one bot seat (AC1)."""
        fp = _coerce_fingerprint(bot_definition_fp)
        if fp is None:
            return invalid_input(
                "bot_definition_fp",
                "a per-bot projection is selected by the CT-33 Bot definition fp1 "
                "(fp1:sha256:<hex>) plus its AD-41 seat binding (DEC-0173)",
                given=repr(bot_definition_fp),
            )
        seat = _clean_token(seat_binding)
        if seat is None:
            return invalid_input(
                "seat_binding",
                "a per-bot projection is selected by a non-blank AD-41 seat binding "
                "alongside the Bot definition fp1 (DEC-0173)",
                given=repr(seat_binding),
            )
        return Ok(
            cls(kind=EntityKind.BOT, bot_seat=BotSeat(bot_definition_fp=fp, seat_binding=seat))
        )

    @classmethod
    def for_binding(cls, binding: object) -> Result[EntitySelector]:
        """Select the combined per-binding view for a full binding tuple (AC1; DEC-0145)."""
        if not isinstance(binding, BindingIdentity):
            return invalid_input(
                "binding",
                "a combined per-binding projection is selected by a BindingIdentity value",
                given=repr(binding),
            )
        return Ok(cls(kind=EntityKind.BINDING, binding=binding))


def _binding_matches(selector: EntitySelector, binding: BindingIdentity) -> bool:
    """Whether a binding identity matches a Book / BMS / combined-binding selector.

    Only ever called for a non-BOT selector (a BOT selector is matched by :func:`_bot_matches`
    on the per-bot identity); the trailing comparison serves the combined ``BINDING`` view.
    """
    if selector.kind is EntityKind.BOOK:
        return binding.book_instance_id == selector.book_instance_id
    if selector.kind is EntityKind.BMS:
        return binding.bms_instance_id == selector.bms_instance_id
    return binding == selector.binding


def _bot_matches(selector: EntitySelector, bot_seat: BotSeat | None) -> bool:
    """Whether a per-bot identity matches a BOT selector."""
    return bot_seat is not None and bot_seat == selector.bot_seat


# --- the command-fingerprint join (pinned versioned CT-25 surface) ----------


@dataclass(frozen=True, slots=True)
class CommandAttribution:
    """The binding (and optional bot) a command record attributes a venue event to (AC2).

    Built from a risk-authored event carrying the command's content fingerprint: the command
    record supplies the binding identity as an identity field, so a venue-authored event that
    shares the command fingerprint inherits that binding through the join, and never learns
    Book identity itself (DEC-0145, DEC-0143).
    """

    binding: BindingIdentity
    bot_seat: BotSeat | None = None


def _empty_command_index() -> Mapping[str, CommandAttribution]:
    """A shared-safe empty command-fingerprint map (the default for an unbuilt index)."""
    empty: dict[str, CommandAttribution] = {}
    return MappingProxyType(empty)


@dataclass(frozen=True, slots=True)
class CommandIndex:
    """The pinned versioned command-fingerprint join surface (AC2; DEC-0145, DEC-0143).

    Maps a command record's content fingerprint to the :class:`CommandAttribution` a
    venue-authored event inherits when it shares that fingerprint. Built from the
    risk-authored events that carry a command fingerprint (a decision or control action that
    authorized a command), so a Book projection joins orders and fills to their authorizing
    decision without threading Book identity into the neutral venue payload. The join key and
    table are CT-25 surface, not implementer judgment.
    """

    by_command: Mapping[str, CommandAttribution] = field(default_factory=_empty_command_index)

    @classmethod
    def build(cls, events: Iterable[JournalEvent]) -> Result[CommandIndex]:
        """Index every risk-authored event that carries a command fingerprint (AC2).

        A risk-authored event carrying the pinned :data:`COMMAND_FINGERPRINT_KEY` plus a
        binding is a command record; its ``command_fingerprint -> attribution`` entry is
        added. A repeated fingerprint with an **equal** attribution is idempotent; a repeated
        fingerprint with a **conflicting** attribution is an ``invalid input`` refusal — one
        command fingerprint must never attribute to two bindings (an integrity fault). A
        risk-authored event that carries a command fingerprint but no valid binding is
        refused; venue-authored events are ignored here (they consume the index, not build
        it).
        """
        index: dict[str, CommandAttribution] = {}
        for event in events:
            if event_class_of(event.event_type) is not EventClass.RISK_AUTHORED:
                continue
            raw = event.payload.get(COMMAND_FINGERPRINT_KEY)
            if raw is None:
                continue
            command_fp = _coerce_fingerprint(raw)
            if command_fp is None:
                return invalid_input(
                    "command_fingerprint",
                    "a command record's command fingerprint is fp1:sha256:<hex> (DEC-0145)",
                    given=repr(raw),
                )
            binding = read_binding(event)
            if is_refusal(binding):
                return binding
            attribution = CommandAttribution(
                binding=binding.value, bot_seat=_optional_bot_seat(event)
            )
            existing = index.get(command_fp.value)
            if existing is not None and existing != attribution:
                return invalid_input(
                    "command_fingerprint",
                    "one command fingerprint attributes to two different bindings; a command "
                    "record must resolve to a single binding identity (DEC-0145, DEC-0143)",
                    command_fingerprint=command_fp.value,
                )
            index[command_fp.value] = attribution
        return Ok(cls(by_command=MappingProxyType(dict(index))))

    def attribution_for(self, command_fingerprint: Fingerprint) -> CommandAttribution | None:
        """The binding a venue-authored event inherits for this command fingerprint, or ``None``."""
        return self.by_command.get(command_fingerprint.value)


# --- projected rows and the logbook result ----------------------------------


@dataclass(frozen=True, slots=True)
class ProjectedRow:
    """One row of a resolved projection (AC1, AC2, AC3).

    ``event`` is the underlying :class:`~qmf.data.journal.JournalEvent`; ``event_class`` is
    its CT-25 authoring class; ``role`` is the account role the row carries (on **every**
    row, AC3); ``binding`` is the binding identity the row resolved by (from the event for a
    risk-authored row, from the command attribution for a joined venue-authored row);
    ``bot_seat`` is the per-bot identity where one bot is concerned.
    """

    event: JournalEvent
    event_class: EventClass
    role: AccountRole
    binding: BindingIdentity | None = None
    bot_seat: BotSeat | None = None


@dataclass(frozen=True, slots=True)
class Logbook:
    """A resolved read-time projection over the recorded writer-scoped streams (AC1).

    Carries the projected :class:`ProjectedRow`\\ s (in stream order), the
    :class:`EntitySelector` it resolved by (``None`` for the cohort read), and the declared
    :class:`CrossRoleRead` when the projection spanned roles. A logbook is a **view**, never
    a stream: the same recorded set of streams yields many logbooks and no logbook writes.
    """

    rows: tuple[ProjectedRow, ...]
    selector: EntitySelector | None = None
    cross_role: CrossRoleRead | None = None

    @property
    def roles(self) -> frozenset[AccountRole]:
        """The distinct account roles present across the projected rows."""
        return frozenset(row.role for row in self.rows)

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        """The underlying journal events of the projected rows, in order."""
        return tuple(row.event for row in self.rows)


# --- the projection engine --------------------------------------------------


def _match_risk_authored(
    event: JournalEvent, selector: EntitySelector
) -> Result[ProjectedRow | None]:
    """Project a risk-authored event if it matches the selector (value-or-refusal).

    Returns ``Ok(None)`` when the event does not match (including a risk-authored event that
    carries no binding, e.g. a qmf-data control action). A partial/malformed binding, a
    partial bot seat, or a matched row missing its role is a refusal.
    """
    bot_seat_result = read_bot_seat(event)
    if is_refusal(bot_seat_result):
        return bot_seat_result
    bot_seat = bot_seat_result.value

    binding: BindingIdentity | None = None
    if _binding_presence(event.payload) != 0:
        built = read_binding(event)
        if is_refusal(built):
            return built
        binding = built.value

    if selector.kind is EntityKind.BOT:
        matched = _bot_matches(selector, bot_seat)
    else:
        matched = binding is not None and _binding_matches(selector, binding)
    if not matched:
        return Ok(None)

    role = read_role(event)
    if is_refusal(role):
        return role
    return Ok(
        ProjectedRow(
            event=event,
            event_class=EventClass.RISK_AUTHORED,
            role=role.value,
            binding=binding,
            bot_seat=bot_seat,
        )
    )


def _match_venue_authored(
    event: JournalEvent, selector: EntitySelector, command_index: CommandIndex
) -> Result[ProjectedRow | None]:
    """Project a venue-authored event via the command-fingerprint join (value-or-refusal).

    Guards the neutral payload (a leaked Book identity is a refusal), then joins the event's
    command fingerprint through the index. Returns ``Ok(None)`` when the event carries no
    command fingerprint or the command is not indexed or the attribution does not match; a
    leaked Book identity or a matched row missing its role is a refusal.
    """
    guard = guard_neutral_venue_payload(event)
    if is_refusal(guard):
        return guard
    command_fp = _coerce_fingerprint(event.payload.get(COMMAND_FINGERPRINT_KEY))
    if command_fp is None:
        return Ok(None)
    attribution = command_index.attribution_for(command_fp)
    if attribution is None:
        return Ok(None)

    if selector.kind is EntityKind.BOT:
        matched = _bot_matches(selector, attribution.bot_seat)
    else:
        matched = _binding_matches(selector, attribution.binding)
    if not matched:
        return Ok(None)

    role = read_role(event)
    if is_refusal(role):
        return role
    return Ok(
        ProjectedRow(
            event=event,
            event_class=EventClass.VENUE_AUTHORED,
            role=role.value,
            binding=attribution.binding,
            bot_seat=attribution.bot_seat,
        )
    )


def _select_rows(
    events: Iterable[JournalEvent],
    selector: EntitySelector,
    command_index: CommandIndex | None,
) -> Result[list[ProjectedRow]]:
    """Select every projected row matching the selector, in stream order (value-or-refusal)."""
    rows: list[ProjectedRow] = []
    for event in events:
        if event_class_of(event.event_type) is EventClass.RISK_AUTHORED:
            matched = _match_risk_authored(event, selector)
        elif command_index is not None:
            matched = _match_venue_authored(event, selector, command_index)
        else:
            # A venue-authored event with no join supplied is simply not included: a Book
            # projection without the command-fingerprint join holds decisions and control
            # actions but no orders or fills (exactly the AC2 point).
            continue
        if is_refusal(matched):
            return matched
        if matched.value is not None:
            rows.append(matched.value)
    return Ok(rows)


def _apply_role_scope(
    rows: list[ProjectedRow],
    selector: EntitySelector,
    role: object | None,
    cross_role: object | None,
) -> Result[Logbook]:
    """Resolve the role scope over the selected rows (AC3; FM-11, DEC-0145, DEC-0158).

    Exactly one of three scopes applies. A single ``role`` resolves inside that one
    role-scoped namespace (rows of other roles are simply outside it). A declared
    ``cross_role`` read admits every role, carrying ``role`` on each row. Neither given:
    rows of a single role (or none) are returned, but rows spanning more than one role are a
    ``policy rejection`` refusal (FM-11) — aggregating across roles requires an explicit
    declaration. Passing both ``role`` and ``cross_role`` is a contradiction (``invalid
    input``).
    """
    if role is not None and cross_role is not None:
        return invalid_input(
            "role",
            "declare either a single role-scoped namespace or a cross-role read, not both",
            role=repr(role),
            cross_role=repr(cross_role),
        )
    if role is not None:
        scoped = _coerce_role(role)
        if scoped is None:
            return invalid_input(
                "role",
                "role is one of the closed AccountRole set",
                given=repr(role),
                allowed=[member.value for member in AccountRole],
            )
        in_scope = tuple(row for row in rows if row.role is scoped)
        return Ok(Logbook(rows=in_scope, selector=selector, cross_role=None))
    if cross_role is not None:
        declared = _coerce_cross_role(cross_role)
        if declared is None:
            return invalid_input(
                "cross_role",
                "a cross-role read is one of the two declared exceptions: the decay-cohort "
                "read or a multi-role entity projection (DEC-0145, DEC-0149)",
                given=repr(cross_role),
                allowed=[member.value for member in CrossRoleRead],
            )
        return Ok(Logbook(rows=tuple(rows), selector=selector, cross_role=declared))
    distinct = frozenset(row.role for row in rows)
    if len(distinct) > 1:
        return policy_rejection(
            "role",
            "an entity-journal projection spans more than one account role; aggregating "
            "across roles requires an explicitly-declared cross-role read (the decay-cohort "
            "read or a multi-role entity projection), else it is refused (FM-11, DEC-0158)",
            roles=sorted(member.value for member in distinct),
            selector=selector.kind.value,
        )
    return Ok(Logbook(rows=tuple(rows), selector=selector, cross_role=None))


def entity_journal(
    events: Iterable[JournalEvent],
    *,
    selector: object,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """Resolve an entity journal as a read-time projection over recorded streams (AC1-AC3).

    Selects every event matching ``selector`` from the one recorded set of writer-scoped
    streams — risk-authored events by their declared identity fields, and (when a
    ``command_index`` is supplied) venue-authored orders and fills joined through the pinned
    command-fingerprint join. The result resolves inside one role-scoped namespace: pass a
    single ``role`` to read one namespace, a declared ``cross_role`` for the two permitted
    cross-role reads, or neither — in which case a projection spanning more than one role is
    an FM-11 ``policy rejection`` refusal (AC3). Every returned row carries ``role``. This
    never writes and mints no stream (AC1).
    """
    if not isinstance(selector, EntitySelector):
        return invalid_input(
            "selector",
            "an entity journal is selected by an EntitySelector (Book, BMS, Bot, or binding)",
            given=repr(selector),
        )
    selected = _select_rows(events, selector, command_index)
    if is_refusal(selected):
        return selected
    return _apply_role_scope(selected.value, selector, role, cross_role)


def book_journal(
    events: Iterable[JournalEvent],
    book_instance_id: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The Book journal for one Book instance (AC1) — a convenience over :func:`entity_journal`.

    Selected by ``BookInstanceId``. Supply a ``command_index`` to include the Book's orders
    and fills via the command-fingerprint join; without one the projection holds the Book's
    decisions, risk transitions, control actions, and promotions.
    """
    selector = EntitySelector.for_book(book_instance_id)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def bms_journal(
    events: Iterable[JournalEvent],
    bms_instance_id: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The BMS journal for one BMS instance (AC1) — a convenience over :func:`entity_journal`."""
    selector = EntitySelector.for_bms(bms_instance_id)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def bot_logbook(
    events: Iterable[JournalEvent],
    bot_definition_fp: object,
    seat_binding: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The per-bot journal — the operator's logbook — for one bot seat (AC1).

    Selected by the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding. Supply a
    ``command_index`` to include the bot's orders and fills via the command-fingerprint join.
    """
    selector = EntitySelector.for_bot(bot_definition_fp, seat_binding)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def decay_cohort_read(events: Iterable[JournalEvent]) -> Result[Logbook]:
    """The AD-35 decay-cohort read — the first declared cross-role read (AC3; DEC-0149).

    One of the two — and only two — reads permitted to span account roles. It projects every
    cohort event that carries a ``role`` across roles (live and paper alike, so alpha-decay
    is sensed across the roles a strategy operated in), carrying ``role`` on every row and
    declaring :attr:`CrossRoleRead.DECAY_COHORT`. An event that carries no declared role is
    not a cohort row and is skipped; this never writes and never crosses roles on write
    (DEC-0158).
    """
    rows: list[ProjectedRow] = []
    for event in events:
        role = read_role(event)
        if is_refusal(role):
            continue
        rows.append(
            ProjectedRow(
                event=event,
                event_class=event_class_of(event.event_type),
                role=role.value,
                binding=_optional_binding(event),
                bot_seat=_optional_bot_seat(event),
            )
        )
    return Ok(Logbook(rows=tuple(rows), selector=None, cross_role=CrossRoleRead.DECAY_COHORT))


# --- the legacy five Records streams (projection names only) -----------------


class RecordsStreamName(StrEnum):
    """The legacy five Records stream names, surviving as **projection names only** (AC4).

    Each maps onto the seven journal event types by the one versioned
    :data:`RECORDS_STREAM_MAPPING` table — no second event catalog is minted (DEC-0145).
    None of these is a stream an entity writes; they are read-time selections over the
    recorded writer-scoped streams.
    """

    VETO_LEDGER = "veto_ledger"
    TRADE_JOURNAL = "trade_journal"
    BOOK_JOURNAL = "book_journal"
    KSA_AUDIT_LOG = "ksa_audit_log"
    CORRELATION_LEDGER = "correlation_ledger"


@dataclass(frozen=True, slots=True)
class RecordsStreamRule:
    """One legacy Records projection's mapping onto the seven event types (AC4; DEC-0145).

    ``event_types`` is the subset of the seven this projection name selects; ``outcome`` is
    the decision-outcome filter a decision-selecting projection applies (only ``veto_ledger``
    sets it — to ``refused-by-door``, so the projection selects on the decision event's
    declared ``outcome`` field, never on key presence).
    """

    event_types: frozenset[JournalEventType]
    outcome: DecisionOutcome | None = None


# The ONE versioned mapping table (AC4; DEC-0145). Each legacy Records name maps onto a
# subset of AD-21's seven event types; no second event catalog exists. Rationale, from the
# recovered node/wiki material:
#   * veto_ledger      -> a refused (vetoed) decision: the decision event with declared
#                         outcome = refused-by-door (never key presence) (DEC-0158).
#   * trade_journal    -> the trade lifecycle: order + fill (venue-authored).
#   * book_journal     -> the Book lifecycle: decision (commit_decision_with_evidence),
#                         risk transition (book_mode_changed), promotion (book_definition
#                         created/registered).
#   * ksa_audit_log    -> the BMS kill-switch/safety audit stream: control action.
#   * correlation_ledger -> BMS cohort/chorus correlation observations. Historically its
#                         payload/event-type detail was OPEN; among the seven types these
#                         BMS-authored risk-domain observations map onto risk transition.
#                         The table is versioned, so the cohort-correlation-evidence sitting
#                         can re-mint this row without a second event catalog.
RECORDS_STREAM_MAPPING: Final[Mapping[RecordsStreamName, RecordsStreamRule]] = MappingProxyType(
    {
        RecordsStreamName.VETO_LEDGER: RecordsStreamRule(
            event_types=frozenset({JournalEventType.DECISION}),
            outcome=DecisionOutcome.REFUSED_BY_DOOR,
        ),
        RecordsStreamName.TRADE_JOURNAL: RecordsStreamRule(
            event_types=frozenset({JournalEventType.ORDER, JournalEventType.FILL}),
        ),
        RecordsStreamName.BOOK_JOURNAL: RecordsStreamRule(
            event_types=frozenset(
                {
                    JournalEventType.DECISION,
                    JournalEventType.RISK_TRANSITION,
                    JournalEventType.PROMOTION,
                }
            ),
        ),
        RecordsStreamName.KSA_AUDIT_LOG: RecordsStreamRule(
            event_types=frozenset({JournalEventType.CONTROL_ACTION}),
        ),
        RecordsStreamName.CORRELATION_LEDGER: RecordsStreamRule(
            event_types=frozenset({JournalEventType.RISK_TRANSITION}),
        ),
    }
)


def _coerce_records_stream_name(value: object) -> RecordsStreamName | None:
    """Resolve ``value`` to a :class:`RecordsStreamName` member, or ``None``."""
    if isinstance(value, RecordsStreamName):
        return value
    if isinstance(value, str):
        try:
            return RecordsStreamName(value)
        except ValueError:
            return None
    return None


def records_stream(events: Iterable[JournalEvent], name: object) -> Result[list[JournalEvent]]:
    """Resolve one legacy Records projection name onto the seven event types (AC4; DEC-0145).

    The legacy five Records streams survive as projection names only. This resolves a
    :class:`RecordsStreamName` (or its string) through the one versioned
    :data:`RECORDS_STREAM_MAPPING` table — no second event catalog. ``veto_ledger`` selects
    on the decision event's declared ``outcome = refused-by-door`` field (via
    :func:`~qmf.data.journal.select_decisions`), never on key presence; every other name
    selects on its declared event types. An unknown name is an ``invalid input`` refusal.
    """
    resolved = _coerce_records_stream_name(name)
    if resolved is None:
        return invalid_input(
            "name",
            "a Records projection is one of the legacy five names, mapped onto the seven "
            "event types by the one versioned CT-25 table (DEC-0145)",
            given=repr(name),
            allowed=[member.value for member in RecordsStreamName],
        )
    rule = RECORDS_STREAM_MAPPING[resolved]
    materialized = list(events)
    if rule.outcome is not None:
        return Ok(select_decisions(materialized, outcome=rule.outcome))
    return Ok([event for event in materialized if event.event_type in rule.event_types])
