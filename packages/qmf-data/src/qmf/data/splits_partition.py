"""CT-12 knowledge-time record placement helpers.

Split from :mod:`qmf.data.splits` so :class:`~qmf.data.splits.SplitManifest`
stays under the Skylos function-length limits. Callers keep using
:meth:`~qmf.data.splits.SplitManifest.partition_record`.
"""

from __future__ import annotations

from qmf.core import Instant, Ok, Result, TypedRefusal
from qmf.data.splits_types import SegmentRole, SplitSegment
from qmf.data.store.refusals import invalid_input, policy_rejection


def instant_segment_index(
    segments: tuple[SplitSegment, ...], instant: Instant
) -> int | None:
    """The index of the first segment whose instant boundary is strictly after ``instant``.

    ``None`` when ``instant`` is at or after the last segment's boundary (beyond the
    split). Only valid when every segment boundary is instant-form (guarded by the caller).
    """
    for index, segment in enumerate(segments):
        boundary = segment.boundary.instant
        if boundary is not None and instant.value_ns < boundary.value_ns:
            return index
    return None


def purged_record(knowledge_ns: int, boundary_ns: int, purge_ns: int) -> TypedRefusal:
    """The purge-zone ``policy rejection`` naming the boundary and the width (DEC-0131)."""
    return policy_rejection(
        "record",
        "the record's knowledge time lands within the declared purge width of a split "
        "boundary; a boundary-adjacent record is excluded from BOTH adjacent segments "
        "rather than admitted to either and leaked across the boundary (CT-12, DEC-0131)",
        knowledge_ns=knowledge_ns,
        boundary_ns=boundary_ns,
        purge_ns=purge_ns,
        distance_ns=abs(knowledge_ns - boundary_ns),
    )


def purge_zone_refusal(
    segments: tuple[SplitSegment, ...],
    purge_ns: int,
    knowledge_time: Instant,
    knowledge_index: int,
) -> TypedRefusal | None:
    """A ``policy rejection`` if ``knowledge_time`` sits within ``purge_width`` of an
    inter-segment boundary, else ``None`` (AC2, AC3; CT-12, DEC-0131).

    ``purge_width`` is a required, fingerprinted manifest field; this is where it is
    **applied** (previously only ``embargo_width`` was, so a fingerprinted purge width had
    no effect). A cleanly-placed (non-straddling) record whose knowledge time lands within
    the purge width of the boundary between two adjacent segments is excluded from **both**:
    its warm-up-plus-confirmation window brushes the boundary, so admitting it to either
    adjacent split would leak across it, and it is quarantined (refused) instead. A record
    exactly ``purge_width`` away is at the edge and is admitted (the width covers strictly
    inside it). A zero purge width has no purge zone. The split's terminal boundary (the
    last segment's upper bound) is the end of the split — records past it are refused as
    beyond, and it is not a boundary between two adjacent segments — so it is never a purge
    edge.
    """
    if purge_ns <= 0:
        return None
    knowledge_ns = knowledge_time.value_ns
    # The inter-segment boundary BELOW this segment (between the previous segment and it).
    if knowledge_index > 0:
        lower = segments[knowledge_index - 1].boundary.instant
        if lower is not None and knowledge_ns - lower.value_ns < purge_ns:
            return purged_record(knowledge_ns, lower.value_ns, purge_ns)
    # The inter-segment boundary ABOVE this segment (the terminal boundary excluded).
    if knowledge_index < len(segments) - 1:
        upper = segments[knowledge_index].boundary.instant
        if upper is not None and upper.value_ns - knowledge_ns < purge_ns:
            return purged_record(knowledge_ns, upper.value_ns, purge_ns)
    return None


def assign_instant_record(
    segments: tuple[SplitSegment, ...],
    embargo_ns: int,
    purge_ns: int,
    observed: Instant,
    knowledge: Instant,
) -> Result[SegmentRole]:
    """Place an instant-form record by knowledge time, applying embargo then purge."""
    knowledge_index = instant_segment_index(segments, knowledge)
    if knowledge_index is None:
        return invalid_input(
            "knowledge_time",
            "the record's knowledge time falls beyond the split's last segment boundary",
            knowledge_ns=knowledge.value_ns,
        )
    observed_index = instant_segment_index(segments, observed)
    if observed_index != knowledge_index:
        gap = knowledge.value_ns - observed.value_ns
        if embargo_ns < gap:
            return policy_rejection(
                "record",
                "the record's observed-at precedes a segment boundary its knowledge-time "
                "follows, and the declared embargo does not cover the gap; it is refused "
                "rather than leaked across the boundary (DEC-0131)",
                observed_ns=observed.value_ns,
                knowledge_ns=knowledge.value_ns,
                gap_ns=gap,
                embargo_ns=embargo_ns,
            )
        # A straddle the embargo covers is governed by the embargo (the forward
        # observed-at -> knowledge-time gap): place it by knowledge time. The purge zone
        # below governs the complementary case — a record that sits cleanly inside one
        # segment but brushes a boundary — so it is not re-applied here (DEC-0131).
        return Ok(segments[knowledge_index].role)
    purged = purge_zone_refusal(segments, purge_ns, knowledge, knowledge_index)
    if purged is not None:
        return purged
    return Ok(segments[knowledge_index].role)
