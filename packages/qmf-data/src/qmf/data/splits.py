"""CT-12 — dataset splits: fingerprinted, time-ordered manifests (AC1, AC2, AC3, AC5).

A CT-12 dataset split is a **fingerprinted, time-ordered, non-overlapping manifest** that
divides research evidence into named segments — by default ``train``, ``validation``, and
``sealed-test`` — so research can never consume its own held-out evaluation period
(DEC-0119, DEC-0046). This module pins the split-manifest value vocabulary; the newest
~12-month no-peek seal and its read-boundary enforcement live beside it in
:mod:`qmf.data.seal`.

Five things this module pins down.

**Identity is derived, never minted (AC1; DEC-0108, DEC-0119).** A :class:`SplitManifest`'s
``split_id`` is its ``fp1`` fingerprint — computed by the single ``qmf-core``
implementation over every identity-bearing field and **nowhere else**. Two manifests with
the same calendar, segments, seal, widths, world, and cited producers share one id; any
difference mints a distinct id. The manifest is never assigned an id by hand.

**Boundaries are TradingDates or Instants, never civil dates (AC1; DEC-0106).** A
:class:`SplitBoundary` wraps exactly one of a ``qmf-core`` :class:`~qmf.core.TradingDate`
(carrying its calendar identity in-band) or an :class:`~qmf.core.Instant` (int64 UTC ns) —
a :class:`~qmf.core.CivilDate` is refused. Segment boundaries are time-ordered and
non-overlapping; the manifest pins **exactly one** calendar identity and version in-band,
and a boundary or row carrying a *different* calendar identity is a ``policy rejection``,
never a silent rescale (AC5).

**Purge and embargo widths are required and leak-guarded (AC2; DEC-0131).**
``purge_width`` and ``embargo_width`` are required manifest fields that enter the split
fingerprint; omitting either is an ``invalid input`` refusal. Both must cover the maximum
declared warm-up-plus-confirmation-delay bound across every producer the split cites
(:class:`ProducerHorizon`), so a manifest that under-covers its own producers is refused at
construction, and a valid manifest **reused** with a longer-horizon producer refuses rather
than leaks (:meth:`SplitManifest.admits_producer`).

**Records partition by knowledge time (AC3; DEC-0131).** A :class:`KnowledgeRecord` carries
its ``observed_at`` and its ``knowledge_time`` — confirmed-at for a structure object, the
knowable-at of the last contributing input for an indicator result. The manifest partitions
a record by its knowledge time; a record whose ``observed_at`` precedes a segment boundary
while its ``knowledge_time`` follows it straddles the boundary and is refused unless the
declared embargo covers the gap.

Every value type follows the one CT-04 construction pattern: an unchecked frozen
constructor for trusted internal use, plus a validating ``try_create`` factory returning
value-or-refusal. Stdlib + qmf-core; ``fp1`` comes only from ``qmf-core``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Fingerprint,
    Instant,
    Ok,
    Result,
    TemporalOrder,
    TradingDate,
    TypedRefusal,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "DEFAULT_SPLIT_ROLES",
    "KnowledgeKind",
    "KnowledgeRecord",
    "ProducerHorizon",
    "SegmentRole",
    "SplitBoundary",
    "SplitManifest",
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


# --- coercion helpers -------------------------------------------------------


def _as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def _as_duration(value: object) -> Duration | None:
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


# --- boundaries -------------------------------------------------------------


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
        resolved = _as_instant(value)
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
        resolved_role = _coerce_role(role)
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


def _coerce_role(value: object) -> SegmentRole | None:
    """Resolve ``value`` to a :class:`SegmentRole` member, or ``None``."""
    if isinstance(value, SegmentRole):
        return value
    if isinstance(value, str):
        try:
            return SegmentRole(value)
        except ValueError:
            return None
    return None


# --- producer horizons ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProducerHorizon:
    """A cited producer and its warm-up-plus-confirmation-delay bound (AC2; DEC-0131).

    ``producer`` names the producer the split cites (a contract or configured-producer
    identity token); ``warmup_plus_confirmation`` is the maximum span between a fact
    becoming observable and the producer's output over it becoming knowable. A split's
    purge and embargo widths must cover the maximum such bound across every producer it
    cites, so a longer-horizon producer refuses rather than leaks.
    """

    producer: str
    warmup_plus_confirmation: Duration

    @classmethod
    def try_create(
        cls, producer: object, warmup_plus_confirmation: object
    ) -> Result[ProducerHorizon]:
        """Validate and build a :class:`ProducerHorizon`, returning value-or-refusal.

        ``producer`` must be a non-empty token; ``warmup_plus_confirmation`` a non-negative
        :class:`~qmf.core.Duration` (or int64 nanoseconds). Anything else is an
        ``invalid input`` refusal naming the offending field.
        """
        if not isinstance(producer, str) or producer.strip() == "":
            return invalid_input(
                "producer",
                "a cited producer is a non-empty identity token",
                given=repr(producer),
            )
        bound = _as_duration(warmup_plus_confirmation)
        if bound is None:
            return invalid_input(
                "warmup_plus_confirmation",
                "a producer's warm-up-plus-confirmation-delay bound is a non-negative "
                "Duration (or int64 nanoseconds)",
                given=repr(warmup_plus_confirmation),
            )
        return Ok(cls(producer=producer.strip(), warmup_plus_confirmation=bound))

    @staticmethod
    def max_bound(producers: Sequence[ProducerHorizon]) -> Duration:
        """The maximum warm-up-plus-confirmation-delay bound across ``producers``.

        The default purge and embargo widths a split citing these producers should carry
        (AC2; DEC-0131). An empty sequence yields a zero-nanosecond :class:`~qmf.core.Duration`.
        """
        widest = 0
        for producer in producers:
            widest = max(widest, producer.warmup_plus_confirmation.value_ns)
        return Duration(value_ns=widest)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — producer plus its bound."""
        return {
            "class": "producer-horizon",
            "producer": self.producer,
            "warmup_plus_confirmation": self.warmup_plus_confirmation.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- records ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """A record offered to a split, keyed by its knowledge time (AC3; DEC-0131).

    ``observed_at`` is when the underlying fact became observable; ``knowledge_time`` is when
    the record became fully knowable — confirmed-at for a structure object, the knowable-at
    of the last contributing input for an indicator result (the caller computes it; ``kind``
    records which rule applied). ``calendar_identity`` is optional: when set, a manifest
    refuses the record if it differs from the manifest's pinned identity (AC5).
    """

    observed_at: Instant
    knowledge_time: Instant
    kind: KnowledgeKind
    calendar_identity: CalendarIdentity | None = None

    @classmethod
    def try_create(
        cls,
        *,
        observed_at: object,
        knowledge_time: object,
        kind: object,
        calendar_identity: object | None = None,
    ) -> Result[KnowledgeRecord]:
        """Validate and build a :class:`KnowledgeRecord`, returning value-or-refusal.

        ``observed_at`` and ``knowledge_time`` are each an :class:`~qmf.core.Instant` (or an
        int64 UTC-nanosecond count); ``kind`` a :class:`KnowledgeKind`; ``calendar_identity``
        an optional :class:`~qmf.core.CalendarIdentity`. Anything else is an ``invalid input``
        refusal naming the offending field.
        """
        resolved_observed = _as_instant(observed_at)
        if resolved_observed is None:
            return invalid_input(
                "observed_at",
                "observed-at is required: an Instant or int64 UTC-nanosecond count",
                given=repr(observed_at),
            )
        resolved_knowledge = _as_instant(knowledge_time)
        if resolved_knowledge is None:
            return invalid_input(
                "knowledge_time",
                "knowledge-time is required: an Instant or int64 UTC-nanosecond count "
                "(confirmed-at for structure, last-input knowable-at for indicators)",
                given=repr(knowledge_time),
            )
        if resolved_knowledge.value_ns < resolved_observed.value_ns:
            return invalid_input(
                "knowledge_time",
                "knowledge-time cannot precede observed-at: a fact cannot become knowable "
                "before it becomes observable. A negative gap (knowledge < observed) would "
                "pass the straddle embargo check and slip sealed-region data into training "
                "(DEC-0131)",
                observed_ns=resolved_observed.value_ns,
                knowledge_ns=resolved_knowledge.value_ns,
            )
        resolved_kind = _coerce_kind(kind)
        if resolved_kind is None:
            return invalid_input(
                "kind",
                "kind is one of the closed set structure | indicator",
                given=repr(kind),
                allowed=[member.value for member in KnowledgeKind],
            )
        if calendar_identity is not None and not isinstance(calendar_identity, CalendarIdentity):
            return invalid_input(
                "calendar_identity",
                "a record's calendar identity, when set, is a qmf-core CalendarIdentity",
                given=repr(calendar_identity),
            )
        return Ok(
            cls(
                observed_at=resolved_observed,
                knowledge_time=resolved_knowledge,
                kind=resolved_kind,
                calendar_identity=calendar_identity,
            )
        )


def _coerce_kind(value: object) -> KnowledgeKind | None:
    """Resolve ``value`` to a :class:`KnowledgeKind` member, or ``None``."""
    if isinstance(value, KnowledgeKind):
        return value
    if isinstance(value, str):
        try:
            return KnowledgeKind(value)
        except ValueError:
            return None
    return None


# --- the split manifest -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class SplitManifest:
    """A fingerprinted CT-12 dataset-split manifest (AC1, AC2, AC3, AC5; DEC-0119).

    Its ``split_id`` is its ``fp1`` fingerprint, derived over the calendar identity, the
    time-ordered non-overlapping segments, the seal boundary, the required purge and embargo
    widths, the world, and every cited producer — never minted. The manifest pins exactly
    one calendar identity in-band and refuses any row carrying a different one (AC5). The
    frozen constructor is the trusted-internal path; :meth:`try_create` is the validating
    factory.
    """

    calendar_identity: CalendarIdentity
    segments: tuple[SplitSegment, ...]
    seal_boundary: SplitBoundary
    purge_width: Duration
    embargo_width: Duration
    world: World
    cited_producers: tuple[ProducerHorizon, ...]
    fingerprint: Fingerprint

    @property
    def split_id(self) -> str:
        """The stable split id — the manifest's ``fp1`` fingerprint string (DEC-0108)."""
        return self.fingerprint.value

    @property
    def boundary_kind(self) -> str:
        """The kind (``trading-date`` or ``instant``) shared by every segment boundary."""
        return self.segments[0].boundary.kind

    @classmethod
    def try_create(
        cls,
        *,
        calendar_identity: object,
        segments: object,
        seal_boundary: object,
        purge_width: object,
        embargo_width: object,
        world: object,
        cited_producers: Sequence[ProducerHorizon] = (),
    ) -> Result[SplitManifest]:
        """Validate every part, compute the ``fp1`` split id, and build the manifest.

        Refuses (``invalid input``): a non-``CalendarIdentity`` identity; empty, mixed-kind,
        mis-calendared, or non-strictly-increasing segments; a seal boundary of a foreign
        calendar identity; an omitted purge or embargo width; or a width that fails to cover
        the maximum cited-producer bound (so a manifest can never under-cover its own
        producers — it refuses rather than leaks, DEC-0131). The split id is **not** supplied
        — it is fingerprinted from the identity content by ``qmf-core`` (DEC-0108).
        """
        if not isinstance(calendar_identity, CalendarIdentity):
            return invalid_input(
                "calendar_identity",
                "a split manifest pins exactly one qmf-core CalendarIdentity in-band "
                "(rule set + version + tzdata) (DEC-0106, DEC-0119)",
                given=repr(calendar_identity),
            )
        resolved_segments = _resolve_segments(segments, calendar_identity)
        if is_refusal(resolved_segments):
            return resolved_segments
        if not isinstance(seal_boundary, SplitBoundary):
            return invalid_input(
                "seal_boundary",
                "the seal boundary is a SplitBoundary (a frozen TradingDate or Instant)",
                given=repr(seal_boundary),
            )
        seal_calendar = seal_boundary.calendar_identity
        if seal_calendar is not None and seal_calendar != calendar_identity:
            return policy_rejection(
                "seal_boundary",
                "the seal boundary carries a calendar identity different from the manifest's "
                "pinned one; it is refused, never rescaled (DEC-0106, DEC-0119)",
                pinned=repr(calendar_identity),
                given=repr(seal_calendar),
            )
        resolved_purge = _as_duration(purge_width)
        if resolved_purge is None:
            return invalid_input(
                "purge_width",
                "purge_width is a required manifest field entering the split fingerprint: a "
                "non-negative Duration (or int64 nanoseconds); omitting it is refused (DEC-0131)",
                given=repr(purge_width),
            )
        resolved_embargo = _as_duration(embargo_width)
        if resolved_embargo is None:
            return invalid_input(
                "embargo_width",
                "embargo_width is a required manifest field entering the split fingerprint: a "
                "non-negative Duration (or int64 nanoseconds); omitting it is refused (DEC-0131)",
                given=repr(embargo_width),
            )
        producers = tuple(cited_producers)
        widest = ProducerHorizon.max_bound(producers).value_ns
        if resolved_purge.value_ns < widest:
            return invalid_input(
                "purge_width",
                "purge_width must cover the maximum cited-producer warm-up-plus-confirmation "
                "bound; a shorter width would leak, so the manifest is refused (DEC-0131)",
                purge_ns=resolved_purge.value_ns,
                required_ns=widest,
            )
        if resolved_embargo.value_ns < widest:
            return invalid_input(
                "embargo_width",
                "embargo_width must cover the maximum cited-producer warm-up-plus-confirmation "
                "bound; a shorter width would leak, so the manifest is refused (DEC-0131)",
                embargo_ns=resolved_embargo.value_ns,
                required_ns=widest,
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return invalid_input(
                "world",
                "world is required and one of the closed set live | replay | simulated",
                given=repr(world),
            )
        ordered_producers = tuple(
            sorted(producers, key=lambda p: (p.producer, p.warmup_plus_confirmation.value_ns))
        )
        content = _manifest_content(
            calendar_identity=calendar_identity,
            segments=resolved_segments.value,
            seal_boundary=seal_boundary,
            purge_width=resolved_purge,
            embargo_width=resolved_embargo,
            world=resolved_world,
            cited_producers=ordered_producers,
        )
        fp = fingerprint(content)
        if is_refusal(fp):  # pragma: no cover - content is canonical by construction
            return fp
        return Ok(
            cls(
                calendar_identity=calendar_identity,
                segments=resolved_segments.value,
                seal_boundary=seal_boundary,
                purge_width=resolved_purge,
                embargo_width=resolved_embargo,
                world=resolved_world,
                cited_producers=ordered_producers,
                fingerprint=fp.value,
            )
        )

    @classmethod
    def default_split_segments(
        cls, boundaries: Sequence[object]
    ) -> Result[tuple[SplitSegment, ...]]:
        """Build the default ``train``/``validation``/``sealed-test`` segments (AC1).

        Pairs :data:`DEFAULT_SPLIT_ROLES` with exactly three time-ordered upper boundaries
        (each a :class:`SplitBoundary`, a :class:`~qmf.core.TradingDate`/:class:`~qmf.core.Instant`,
        or an int64 nanosecond count). A count other than three, or a boundary that does not
        resolve, is an ``invalid input`` refusal.
        """
        materialized = list(boundaries)
        if len(materialized) != len(DEFAULT_SPLIT_ROLES):
            return invalid_input(
                "boundaries",
                "the default split has exactly three segments (train, validation, sealed-test)",
                given=len(materialized),
            )
        built: list[SplitSegment] = []
        for role, raw in zip(DEFAULT_SPLIT_ROLES, materialized, strict=True):
            boundary = Ok(raw) if isinstance(raw, SplitBoundary) else SplitBoundary.try_create(raw)
            if is_refusal(boundary):
                return boundary
            segment = SplitSegment.try_create(role, boundary.value)
            if is_refusal(segment):
                return segment
            built.append(segment.value)
        return Ok(tuple(built))

    def admits_calendar(self, identity: object) -> Result[CalendarIdentity]:
        """Whether ``identity`` matches the manifest's pinned calendar identity (AC5).

        A row carrying a calendar identity different from the pinned one is a ``policy
        rejection`` — refused, never silently rescaled (DEC-0106, DEC-0119). A non-identity
        argument is an ``invalid input`` refusal.
        """
        if not isinstance(identity, CalendarIdentity):
            return invalid_input(
                "calendar_identity",
                "a calendar identity is a qmf-core CalendarIdentity",
                given=repr(identity),
            )
        denied = self._require_calendar(identity)
        if denied is not None:
            return denied
        return Ok(identity)

    def admits_producer(self, producer: object) -> Result[ProducerHorizon]:
        """Whether the manifest's widths cover ``producer`` on reuse (AC2; DEC-0131).

        A manifest is fingerprinted with fixed purge and embargo widths. Reusing it with a
        longer-horizon producer — one whose warm-up-plus-confirmation bound exceeds either
        declared width — would leak the held-out period, so it is a ``policy rejection``:
        the split refuses rather than leaks. A non-:class:`ProducerHorizon` argument is an
        ``invalid input`` refusal.
        """
        if not isinstance(producer, ProducerHorizon):
            return invalid_input(
                "producer",
                "a producer horizon is a ProducerHorizon",
                given=repr(producer),
            )
        bound = producer.warmup_plus_confirmation.value_ns
        if self.purge_width.value_ns < bound or self.embargo_width.value_ns < bound:
            return policy_rejection(
                "producer",
                "the producer's warm-up-plus-confirmation horizon exceeds the manifest's "
                "declared purge/embargo widths; the split refuses rather than leaks (DEC-0131)",
                producer=producer.producer,
                bound_ns=bound,
                purge_ns=self.purge_width.value_ns,
                embargo_ns=self.embargo_width.value_ns,
            )
        return Ok(producer)

    def partition_record(self, record: object) -> Result[SegmentRole]:
        """Assign ``record`` to a segment by its knowledge time (AC3, AC5; DEC-0131).

        A record carrying a calendar identity different from the manifest's pinned one is a
        ``policy rejection`` (AC5). Records are partitioned against instant-form segment
        boundaries by knowledge time; a trading-date split leaves record placement to the
        calendar extension, so it is an ``invalid input`` refusal here. A record whose
        knowledge time falls beyond the split's last boundary is an ``invalid input``
        refusal. A record that straddles a boundary — ``observed_at`` before it and
        ``knowledge_time`` after it — is a ``policy rejection`` unless the declared embargo
        covers the gap (DEC-0131).
        """
        if not isinstance(record, KnowledgeRecord):
            return invalid_input(
                "record", "a record offered to a split is a KnowledgeRecord", given=repr(record)
            )
        if record.calendar_identity is not None:
            denied = self._require_calendar(record.calendar_identity)
            if denied is not None:
                return denied
        if record.knowledge_time.value_ns < record.observed_at.value_ns:
            return invalid_input(
                "knowledge_time",
                "knowledge-time precedes observed-at; a negative gap can never be covered by "
                "an embargo and would leak sealed-region data across a boundary. A record is "
                "normally refused this at construction (KnowledgeRecord.try_create); this is "
                "the defensive guard for a trusted-internal-constructed record (DEC-0131)",
                observed_ns=record.observed_at.value_ns,
                knowledge_ns=record.knowledge_time.value_ns,
            )
        if self.boundary_kind != "instant":
            return invalid_input(
                "segments",
                "record partitioning by knowledge instant needs instant-form segment "
                "boundaries; a trading-date split is placed by the calendar extension",
                boundary_kind=self.boundary_kind,
            )
        knowledge_index = self._instant_segment_index(record.knowledge_time)
        if knowledge_index is None:
            return invalid_input(
                "knowledge_time",
                "the record's knowledge time falls beyond the split's last segment boundary",
                knowledge_ns=record.knowledge_time.value_ns,
            )
        observed_index = self._instant_segment_index(record.observed_at)
        if observed_index != knowledge_index:
            gap = record.knowledge_time.value_ns - record.observed_at.value_ns
            if self.embargo_width.value_ns < gap:
                return policy_rejection(
                    "record",
                    "the record's observed-at precedes a segment boundary its knowledge-time "
                    "follows, and the declared embargo does not cover the gap; it is refused "
                    "rather than leaked across the boundary (DEC-0131)",
                    observed_ns=record.observed_at.value_ns,
                    knowledge_ns=record.knowledge_time.value_ns,
                    gap_ns=gap,
                    embargo_ns=self.embargo_width.value_ns,
                )
        return Ok(self.segments[knowledge_index].role)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint` and its value is :attr:`split_id`."""
        return _manifest_content(
            calendar_identity=self.calendar_identity,
            segments=self.segments,
            seal_boundary=self.seal_boundary,
            purge_width=self.purge_width,
            embargo_width=self.embargo_width,
            world=self.world,
            cited_producers=self.cited_producers,
        )

    def _require_calendar(self, identity: CalendarIdentity) -> TypedRefusal | None:
        """A ``policy rejection`` if ``identity`` differs from the pinned one, else ``None``."""
        if identity != self.calendar_identity:
            return policy_rejection(
                "calendar_identity",
                "a row carrying a calendar identity different from the manifest's pinned one "
                "is refused, never silently rescaled (DEC-0106, DEC-0119)",
                pinned=repr(self.calendar_identity),
                given=repr(identity),
            )
        return None

    def _instant_segment_index(self, instant: Instant) -> int | None:
        """The index of the first segment whose instant boundary is strictly after ``instant``.

        ``None`` when ``instant`` is at or after the last segment's boundary (beyond the
        split). Only valid when :attr:`boundary_kind` is ``instant`` (guarded by the caller).
        """
        for index, segment in enumerate(self.segments):
            boundary = segment.boundary.instant
            if boundary is not None and instant.value_ns < boundary.value_ns:
                return index
        return None


def _resolve_segments(
    segments: object, calendar_identity: CalendarIdentity
) -> Result[tuple[SplitSegment, ...]]:
    """Validate a segment sequence: non-empty, one kind, one calendar, strictly increasing.

    Every segment is a :class:`SplitSegment`; every boundary shares one kind; a trading-date
    boundary must carry the manifest's pinned calendar identity (a foreign one is a ``policy
    rejection``, AC5); and boundaries are strictly increasing, so segments are time-ordered
    and non-overlapping (AC1). Anything else is an ``invalid input`` refusal.
    """
    if isinstance(segments, (str, bytes)) or not isinstance(segments, Sequence):
        return invalid_input(
            "segments",
            "segments are an ordered sequence of SplitSegment",
            given=repr(segments),
        )
    raw_items = list(cast("Sequence[object]", segments))
    if not raw_items:
        return invalid_input(
            "segments", "a split manifest carries at least one segment (default three)"
        )
    validated: list[SplitSegment] = []
    for position, item in enumerate(raw_items):
        if not isinstance(item, SplitSegment):
            return invalid_input(
                "segments", "each segment is a SplitSegment", index=position, given=repr(item)
            )
        validated.append(item)
    first_kind = validated[0].boundary.kind
    for position, segment in enumerate(validated):
        if segment.boundary.kind != first_kind:
            return invalid_input(
                "segments",
                "every segment boundary shares one kind (all trading-date or all instant)",
                index=position,
                expected=first_kind,
                given=segment.boundary.kind,
            )
        boundary_calendar = segment.boundary.calendar_identity
        if boundary_calendar is not None and boundary_calendar != calendar_identity:
            return policy_rejection(
                "segments",
                "a segment boundary carries a calendar identity different from the manifest's "
                "pinned one; it is refused, never rescaled (DEC-0106, DEC-0119)",
                index=position,
                pinned=repr(calendar_identity),
                given=repr(boundary_calendar),
            )
    for position in range(1, len(validated)):
        order = validated[position - 1].boundary.compare(validated[position].boundary)
        if is_refusal(order):
            return order
        if order.value is not TemporalOrder.BEFORE:
            return invalid_input(
                "segments",
                "segment boundaries are strictly increasing, so segments are time-ordered "
                "and non-overlapping (AC1)",
                index=position,
            )
    return Ok(tuple(validated))


def _manifest_content(
    *,
    calendar_identity: CalendarIdentity,
    segments: tuple[SplitSegment, ...],
    seal_boundary: SplitBoundary,
    purge_width: Duration,
    embargo_width: Duration,
    world: World,
    cited_producers: tuple[ProducerHorizon, ...],
) -> dict[str, object]:
    """The manifest's canonical ``fp1`` identity content — the parts that ARE its identity.

    Built identically by :meth:`SplitManifest.try_create` (to derive the split id) and
    :meth:`SplitManifest.fp1_identity` (so a read-back re-fingerprints to the same value).
    Segments are order-significant; cited producers are pre-sorted so producer input order
    never forks the id.
    """
    return {
        "class": "dataset-split-manifest",
        "calendar_identity": calendar_identity.fp1_identity(),
        "segments": [segment.fp1_identity() for segment in segments],
        "seal_boundary": seal_boundary.fp1_identity(),
        "purge_width": purge_width.fp1_identity(),
        "embargo_width": embargo_width.fp1_identity(),
        "world": world.value,
        "cited_producers": [producer.fp1_identity() for producer in cited_producers],
        "format_version": CONTRACT_FORMAT_VERSION,
    }
