"""CT-12 producer horizons and knowledge-time records.

Split from :mod:`qmf.data.splits` so the public module stays under the
Skylos god-file limits. Callers keep importing these names from
:mod:`qmf.data.splits`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Duration,
    Instant,
    Ok,
    Result,
    is_refusal,
)
from qmf.data.splits_types import (
    CONTRACT_FORMAT_VERSION,
    KnowledgeKind,
    as_duration,
    as_instant,
    coerce_kind,
)
from qmf.data.store.refusals import invalid_input

__all__ = ["KnowledgeRecord", "ProducerHorizon"]

TKnowledge = TypeVar("TKnowledge", bound="KnowledgeRecord")


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
        bound = as_duration(warmup_plus_confirmation)
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


def resolve_knowledge_times(
    observed_at: object, knowledge_time: object
) -> Result[tuple[Instant, Instant]]:
    """Admit observed-at and knowledge-time, refusing a negative gap (DEC-0131)."""
    resolved_observed = as_instant(observed_at)
    if resolved_observed is None:
        return invalid_input(
            "observed_at",
            "observed-at is required: an Instant or int64 UTC-nanosecond count",
            given=repr(observed_at),
        )
    resolved_knowledge = as_instant(knowledge_time)
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
    return Ok((resolved_observed, resolved_knowledge))


def resolve_knowledge_kind_and_calendar(
    kind: object, calendar_identity: object | None
) -> Result[tuple[KnowledgeKind, CalendarIdentity | None]]:
    """Admit the closed knowledge kind and optional calendar identity."""
    resolved_kind = coerce_kind(kind)
    if resolved_kind is None:
        return invalid_input(
            "kind",
            "kind is one of the closed set structure | indicator",
            given=repr(kind),
            allowed=[member.value for member in KnowledgeKind],
        )
    if calendar_identity is None:
        return Ok((resolved_kind, None))
    if isinstance(calendar_identity, CalendarIdentity):
        return Ok((resolved_kind, calendar_identity))
    return invalid_input(
        "calendar_identity",
        "a record's calendar identity, when set, is a qmf-core CalendarIdentity",
        given=repr(calendar_identity),
    )


def admit_knowledge_record(
    cls: type[TKnowledge],
    *,
    observed_at: object,
    knowledge_time: object,
    kind: object,
    calendar_identity: object | None,
) -> Result[TKnowledge]:
    """Validate KnowledgeRecord parts in construction order, returning value-or-refusal."""
    times = resolve_knowledge_times(observed_at, knowledge_time)
    if is_refusal(times):
        return times
    extras = resolve_knowledge_kind_and_calendar(kind, calendar_identity)
    if is_refusal(extras):
        return extras
    resolved_observed, resolved_knowledge = times.value
    resolved_kind, resolved_calendar = extras.value
    return Ok(
        cls(
            observed_at=resolved_observed,
            knowledge_time=resolved_knowledge,
            kind=resolved_kind,
            calendar_identity=resolved_calendar,
        )
    )


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
        return admit_knowledge_record(
            cls,
            observed_at=observed_at,
            knowledge_time=knowledge_time,
            kind=kind,
            calendar_identity=calendar_identity,
        )
