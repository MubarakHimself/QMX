"""CT-13 vocabulary types and small coercers for the durable journal.

Split from :mod:`qmf.data.journal` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.journal`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Instant, World, WriterId, is_ok

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "CORRELATION_ID_EXCLUDED_FROM_FP1",
    "DISPLAY_TIME_EXCLUDED_FROM_FP1",
    "DecisionOutcome",
    "JournalEventType",
]

# CT-13 carries its own integer contract format version, stamped into every journal
# artifact; its meaning never mutates — an incompatible change mints the next version
# plus a migration note (DEC-0103; versioning-from-birth L15). CT-13's own, not CT-05's.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The explicit, versioned declaration that correlation_id is a linking annotation
# EXCLUDED from fp1 identity (DEC-0112, DEC-0108). It is a named design choice recorded
# at source — never an implementer's per-call judgment — so two events differing only in
# correlation_id share one identity, while the annotation still propagates in the stored
# row and across package boundaries.
CORRELATION_ID_EXCLUDED_FROM_FP1: Final[bool] = True

# The optional display_time (ISO-8601-with-Z) is display-only and likewise excluded from
# identity — journals store the int64-ns instant, logs render the display time (DEC-0112).
DISPLAY_TIME_EXCLUDED_FROM_FP1: Final[bool] = True

# One shared immutable empty payload; an event always carries a present mapping, never a
# null (the same idiom qmf-core's SinkAck detail uses).
EMPTY_PAYLOAD: Final[Mapping[str, object]] = MappingProxyType({})

# The payload key a refused-by-door / suppressed decision carries its reference under.
REFUSING_DOOR_KEY: Final[str] = "refusing_door"
SUPPRESSING_AUTHORITY_KEY: Final[str] = "suppressing_authority"


class JournalEventType(StrEnum):
    """The seven ratified journal event types (CT-13 ``registry:journal_event_types``).

    A ``StrEnum`` so a later contract version may **add** a type; the seven V1 meanings
    are fixed and never redefined (DEC-0119). QMF's own wired producers are qmf-data
    (``DATA_QUALITY``, ``CONTROL_ACTION``); the other five are produced by qmf-registry
    (promotion), qmf-venue (order, fill), and qmf-risk (decision, risk transition,
    control action) through the core-defined ``JournalSink`` injected at the composition
    root (DEC-0116, DEC-0138, DEC-0145).
    """

    DECISION = "decision"
    ORDER = "order"
    FILL = "fill"
    RISK_TRANSITION = "risk transition"
    PROMOTION = "promotion"
    DATA_QUALITY = "data quality"
    CONTROL_ACTION = "control action"


class DecisionOutcome(StrEnum):
    """The mandatory closed outcome of a ``decision`` event (CT-13; DEC-0158, DEC-0150).

    Every decision event declares exactly one: ``AUTHORIZED`` (the act was permitted),
    ``REFUSED_BY_DOOR`` (a door refused it — the refusing-door reference rides the
    payload), or ``SUPPRESSED`` (a higher authority discarded an already-authorized act
    at arbitration — the suppressing-authority reference rides the payload). A projection
    selects on this declared field, never on key presence.
    """

    AUTHORIZED = "authorized"
    REFUSED_BY_DOOR = "refused-by-door"
    SUPPRESSED = "suppressed"


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


def as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def coerce_event_type(value: object) -> JournalEventType | None:
    """Resolve ``value`` to a :class:`JournalEventType`, or ``None`` (outside the seven)."""
    if isinstance(value, JournalEventType):
        return value
    if isinstance(value, str):
        try:
            return JournalEventType(value)
        except ValueError:
            return None
    return None


def coerce_decision_outcome(value: object) -> DecisionOutcome | None:
    """Resolve ``value`` to a :class:`DecisionOutcome`, or ``None``."""
    if isinstance(value, DecisionOutcome):
        return value
    if isinstance(value, str):
        try:
            return DecisionOutcome(value)
        except ValueError:
            return None
    return None


def coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def freeze_value(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    A ``Mapping`` becomes a :class:`~types.MappingProxyType` over frozen values and a
    list/tuple becomes a tuple, so a nested container reached through the caller's dict
    can never mutate the frozen event's payload (the same idiom qmf-core's SinkAck uses).
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: freeze_value(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(freeze_value(item) for item in sequence)
    return value


def writer_identity(writer: WriterId) -> dict[str, object]:
    """The writer's identity content — :class:`~qmf.core.WriterId` exposes no
    ``fp1_identity``, so its ``(machine, role, stream, boot_epoch_id)`` parts are folded
    in explicitly and consistently (the same shape the CT-10 boundary uses)."""
    return {
        "machine": writer.machine,
        "role": writer.role,
        "stream": writer.stream,
        "boot_epoch_id": writer.boot_epoch_id,
    }
