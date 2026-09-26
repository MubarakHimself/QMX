"""CT-12 split roles, boundaries, and segments.

Split from :mod:`qmf.data.splits` so the public module stays under the
Skylos god-file limits. Callers keep importing these names from
:mod:`qmf.data.splits`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Instant,
    Ok,
    Result,
    TemporalOrder,
    TradingDate,
    World,
    is_ok,
)
from qmf.data.store.refusals import invalid_input

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "DEFAULT_SPLIT_ROLES",
    "KnowledgeKind",
    "SegmentRole",
    "SplitBoundary",
    "SplitSegment",
]

# CT-12 carries its own integer contract format version, stamped into every serialized
# split manifest; its meaning never mutates — an incompatible change mints the next version
# plus a migration note (DEC-0103, DEC-0119; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1


class SegmentRole(StrEnum):
    """The split role of a segment (CT-12 ``enums.segment.role``; DEC-0046, DEC-0119).

    Research data is split by default into ``train``, ``validation``, and ``sealed-test`` —
    the untouched-test split of DEC-0046, under DEC-0119's ``seal`` vocabulary. The set is
    addable in a later contract format version, never redefined.
    """

    TRAIN = "train"
    VALIDATION = "validation"
    SEALED_TEST = "sealed-test"


# The default research split, in time order: train, then validation, then sealed-test.
DEFAULT_SPLIT_ROLES: Final[tuple[SegmentRole, ...]] = (
    SegmentRole.TRAIN,
    SegmentRole.VALIDATION,
    SegmentRole.SEALED_TEST,
)


class KnowledgeKind(StrEnum):
    """How a record's knowledge time is derived (CT-12; DEC-0131).

    A ``structure`` object's knowledge time is its confirmed-at; an ``indicator`` result's
    is the knowable-at of the last contributing input. The kind labels which rule produced
    the ``knowledge_time`` a :class:`KnowledgeRecord` already carries — the caller computes
    the instant; this enum records the provenance for the register and the journal.
    """

    STRUCTURE = "structure"
    INDICATOR = "indicator"


def as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def as_duration(value: object) -> Duration | None:
    """Resolve ``value`` to a non-negative :class:`~qmf.core.Duration`, or ``None``.

    Accepts a :class:`~qmf.core.Duration` or an int64 nanosecond count; a negative width is
    rejected — a purge or embargo width is a non-negative span.
    """
    if isinstance(value, Duration):
        return value if value.value_ns >= 0 else None
    built = Duration.try_create(value)
    if not is_ok(built):
        return None
    return built.value if built.value.value_ns >= 0 else None


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


def coerce_role(value: object) -> SegmentRole | None:
    """Resolve ``value`` to a :class:`SegmentRole` member, or ``None``."""
    if isinstance(value, SegmentRole):
        return value
    if isinstance(value, str):
        try:
            return SegmentRole(value)
        except ValueError:
            return None
    return None


def coerce_kind(value: object) -> KnowledgeKind | None:
    """Resolve ``value`` to a :class:`KnowledgeKind` member, or ``None``."""
    if isinstance(value, KnowledgeKind):
        return value
    if isinstance(value, str):
        try:
            return KnowledgeKind(value)
        except ValueError:
            return None
    return None


@dataclass(frozen=True, slots=True)
class SplitBoundary:
    """An explicit split or seal boundary: a TradingDate or an Instant (CT-12; DEC-0106).

    Exactly one of :attr:`trading_date` or :attr:`instant` is set. A boundary is **never a
    civil date** — a :class:`~qmf.core.CivilDate` is refused at construction — and a
    trading-date boundary carries its :class:`~qmf.core.CalendarIdentity` in-band, so a
    manifest can pin one calendar identity and refuse any boundary carrying a different one.
    Comparison is defined only between like kinds (and, for trading dates, one calendar
    identity); a cross-kind comparison is an ``invalid input`` refusal.
    """

    trading_date: TradingDate | None = None
    instant: Instant | None = None

    @classmethod
    def try_create(cls, value: object) -> Result[SplitBoundary]:
        """Validate and build a :class:`SplitBoundary`, returning value-or-refusal.

        Accepts a :class:`~qmf.core.TradingDate`, an :class:`~qmf.core.Instant`, or an int64
        UTC-nanosecond count (built into an Instant). A :class:`~qmf.core.CivilDate` is a
        pointed refusal — boundaries are TradingDates or Instants, never civil dates
        (DEC-0106); anything else is an ``invalid input`` refusal.
        """
        if isinstance(value, TradingDate):
            return Ok(cls(trading_date=value))
        if isinstance(value, Instant):
            return Ok(cls(instant=value))
        if isinstance(value, CivilDate):
            return invalid_input(
                "boundary",
                "a split or seal boundary is a TradingDate or an Instant, never a civil "
                "date; a civil date carries no calendar identity (DEC-0106)",
                given=repr(value),
            )
        resolved = as_instant(value)
        if resolved is None:
            return invalid_input(
                "boundary",
                "a split or seal boundary is a TradingDate or an Instant (or int64 UTC ns)",
                given=repr(value),
            )
        return Ok(cls(instant=resolved))

    @property
    def kind(self) -> str:
        """``trading-date`` or ``instant`` — which representation this boundary carries."""
        return "trading-date" if self.trading_date is not None else "instant"

    @property
    def calendar_identity(self) -> CalendarIdentity | None:
        """The pinned calendar identity for a trading-date boundary, else ``None``."""
        return self.trading_date.calendar if self.trading_date is not None else None

    def compare(self, other: object) -> Result[TemporalOrder]:
        """Order this boundary against ``other`` (CT-12; DEC-0106).

        Two boundaries of different kinds are incomparable — a cross-kind comparison is an
        ``invalid input`` refusal — and two trading-date boundaries of different calendar
        identities are incomparable too (delegated to ``TradingDate.compare``, which refuses
        FM-3). Instant boundaries compare on their nanosecond count.
        """
        if not isinstance(other, SplitBoundary):
            return invalid_input(
                "other", "a boundary compares to another SplitBoundary", given=repr(other)
            )
        if self.trading_date is not None and other.trading_date is not None:
            return self.trading_date.compare(other.trading_date)
        if self.instant is not None and other.instant is not None:
            left, right = self.instant.value_ns, other.instant.value_ns
            if left < right:
                return Ok(TemporalOrder.BEFORE)
            if left > right:
                return Ok(TemporalOrder.AFTER)
            return Ok(TemporalOrder.EQUAL)
        return invalid_input(
            "kind",
            "boundaries of different kinds (trading-date vs instant) are incomparable; "
            "present both in the same representation",
            left=self.kind,
            right=other.kind,
        )

    def label(self) -> str:
        """A stable, human-legible label for logging, indexing, and the journal.

        A convenience string, not identity — fp1 identity comes from :meth:`fp1_identity`,
        computed only by ``qmf-core``. A trading-date reads ``rule:version:tzdata:date``; an
        instant reads its nanosecond count.
        """
        if self.trading_date is not None:
            calendar = self.trading_date.calendar
            return (
                f"{calendar.rule_set}:{calendar.rule_set_version}:{calendar.tzdata_version}:"
                f"{self.trading_date.date_value.isoformat()}"
            )
        instant = self.instant
        return str(instant.value_ns) if instant is not None else "0"

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the one representation set."""
        content: dict[str, object] = {
            "class": "split-boundary",
            "kind": self.kind,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.trading_date is not None:
            content["trading_date"] = self.trading_date.fp1_identity()
        elif self.instant is not None:
            content["instant"] = self.instant.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class SplitSegment:
    """One time-ordered segment of a split: a role and its exclusive upper boundary (AC1).

    A segment covers ``[previous boundary, boundary)`` — its :attr:`boundary` is the
    exclusive upper cut, and segments in a manifest are strictly increasing, so they are
    time-ordered and non-overlapping by construction. The earliest segment covers everything
    up to its boundary.
    """

    role: SegmentRole
    boundary: SplitBoundary

    @classmethod
    def try_create(cls, role: object, boundary: object) -> Result[SplitSegment]:
        """Validate and build a :class:`SplitSegment`, returning value-or-refusal.

        ``role`` must be a :class:`SegmentRole` (or its value string) and ``boundary`` a
        :class:`SplitBoundary`; anything else is an ``invalid input`` refusal.
        """
        resolved_role = coerce_role(role)
        if resolved_role is None:
            return invalid_input(
                "role",
                "a segment role is one of the closed set train | validation | sealed-test",
                given=repr(role),
                allowed=[member.value for member in SegmentRole],
            )
        if not isinstance(boundary, SplitBoundary):
            return invalid_input(
                "boundary",
                "a segment's boundary is a SplitBoundary (a TradingDate or Instant)",
                given=repr(boundary),
            )
        return Ok(cls(role=resolved_role, boundary=boundary))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — role plus boundary."""
        return {
            "class": "split-segment",
            "role": self.role.value,
            "boundary": self.boundary.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
