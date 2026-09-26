"""CT-25 vocabulary: payload keys, event class, and role-scoped namespaces.

Split from :mod:`qmf.data.logbooks` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.logbooks`.
"""

from __future__ import annotations

from collections.abc import Mapping
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
)
from qmf.data.journal import JournalEventType
from qmf.data.store.refusals import invalid_input

__all__ = [
    "ACCOUNT_ID_KEY",
    "BMS_INSTANCE_ID_KEY",
    "BOOK_DEFINITION_FP_KEY",
    "BOOK_IDENTITY_FIELDS",
    "BOOK_INSTANCE_ID_KEY",
    "BOT_DEFINITION_FP_KEY",
    "COMMAND_FINGERPRINT_KEY",
    "CT25_CONTRACT_FORMAT_VERSION",
    "ROLE_KEY",
    "SEAT_BINDING_KEY",
    "VENUE_ID_KEY",
    "CrossRoleRead",
    "EventClass",
    "event_class_of",
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
BINDING_KEYS: Final[tuple[str, ...]] = (
    BOOK_INSTANCE_ID_KEY,
    BMS_INSTANCE_ID_KEY,
    VENUE_ID_KEY,
    ACCOUNT_ID_KEY,
)


def clean_token(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def coerce_venue_id(value: object) -> VenueId | None:
    """Resolve a :class:`~qmf.core.VenueId` (or its opaque string token), else ``None``."""
    if isinstance(value, VenueId):
        return value if value.value.strip() != "" else None
    if isinstance(value, str):
        built = VenueId.try_create(value)
        return built.value if is_ok(built) else None
    return None


def coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`~qmf.core.World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def coerce_role(value: object) -> AccountRole | None:
    """Resolve ``value`` to an :class:`~qmf.core.AccountRole` member, or ``None``."""
    if isinstance(value, AccountRole):
        return value
    if isinstance(value, str):
        try:
            return AccountRole(value)
        except ValueError:
            return None
    return None


def coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


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
    resolved = coerce_role(role)
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


def coerce_cross_role(value: object) -> CrossRoleRead | None:
    """Resolve ``value`` to a :class:`CrossRoleRead` member, or ``None``."""
    if isinstance(value, CrossRoleRead):
        return value
    if isinstance(value, str):
        try:
            return CrossRoleRead(value)
        except ValueError:
            return None
    return None
