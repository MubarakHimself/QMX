"""CT-12 split-manifest admission helpers.

Split from :mod:`qmf.data.splits` so the public module stays under the
Skylos god-file limits. :class:`~qmf.data.splits.SplitManifest` stays the
public factory.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple, cast

from qmf.core import (
    CalendarIdentity,
    Duration,
    Fingerprint,
    Ok,
    Result,
    TemporalOrder,
    World,
    fingerprint,
    is_refusal,
)
from qmf.data.splits_records import ProducerHorizon
from qmf.data.splits_types import (
    CONTRACT_FORMAT_VERSION,
    SplitBoundary,
    SplitSegment,
    as_duration,
    coerce_world,
)
from qmf.data.store.refusals import invalid_input, policy_rejection


class ManifestShape(NamedTuple):
    """Calendar, segments, and seal accepted together by :func:`resolve_manifest_shape`."""

    calendar_identity: CalendarIdentity
    segments: tuple[SplitSegment, ...]
    seal_boundary: SplitBoundary


class ManifestWidths(NamedTuple):
    """Purge, embargo, cited producers, and world accepted by :func:`resolve_manifest_widths`."""

    purge_width: Duration
    embargo_width: Duration
    cited_producers: tuple[ProducerHorizon, ...]
    world: World


class ManifestIdentity(NamedTuple):
    """Canonical identity parts fingerprinted into a split id (DEC-0108)."""

    calendar_identity: CalendarIdentity
    segments: tuple[SplitSegment, ...]
    seal_boundary: SplitBoundary
    purge_width: Duration
    embargo_width: Duration
    world: World
    cited_producers: tuple[ProducerHorizon, ...]


def segment_list(segments: object) -> Result[list[SplitSegment]]:
    """Materialize ``segments`` as a non-empty list of :class:`SplitSegment`."""
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
    return Ok(validated)


def align_segment_kind_and_calendar(
    validated: list[SplitSegment], calendar_identity: CalendarIdentity
) -> Result[list[SplitSegment]]:
    """Refuse mixed-kind or foreign-calendar segment boundaries (AC1, AC5)."""
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
    return Ok(validated)


def require_increasing_segments(
    validated: list[SplitSegment],
) -> Result[tuple[SplitSegment, ...]]:
    """Refuse a segment sequence whose boundaries are not strictly increasing (AC1)."""
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


def resolve_segments(
    segments: object, calendar_identity: CalendarIdentity
) -> Result[tuple[SplitSegment, ...]]:
    """Validate a segment sequence: non-empty, one kind, one calendar, strictly increasing.

    Every segment is a :class:`SplitSegment`; every boundary shares one kind; a trading-date
    boundary must carry the manifest's pinned calendar identity (a foreign one is a ``policy
    rejection``, AC5); and boundaries are strictly increasing, so segments are time-ordered
    and non-overlapping (AC1). Anything else is an ``invalid input`` refusal.
    """
    validated = segment_list(segments)
    if is_refusal(validated):
        return validated
    aligned = align_segment_kind_and_calendar(validated.value, calendar_identity)
    if is_refusal(aligned):
        return aligned
    return require_increasing_segments(aligned.value)


def resolve_manifest_shape(
    *,
    calendar_identity: object,
    segments: object,
    seal_boundary: object,
) -> Result[ManifestShape]:
    """Admit the pinned calendar, segments, and seal boundary (AC1, AC5)."""
    if not isinstance(calendar_identity, CalendarIdentity):
        return invalid_input(
            "calendar_identity",
            "a split manifest pins exactly one qmf-core CalendarIdentity in-band "
            "(rule set + version + tzdata) (DEC-0106, DEC-0119)",
            given=repr(calendar_identity),
        )
    resolved_segments = resolve_segments(segments, calendar_identity)
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
    return Ok(
        ManifestShape(
            calendar_identity=calendar_identity,
            segments=resolved_segments.value,
            seal_boundary=seal_boundary,
        )
    )


def admit_required_width(field: str, value: object) -> Result[Duration]:
    """Admit a required non-negative purge or embargo width (DEC-0131)."""
    resolved = as_duration(value)
    if resolved is not None:
        return Ok(resolved)
    if field == "purge_width":
        return invalid_input(
            field,
            "purge_width is a required manifest field entering the split fingerprint: a "
            "non-negative Duration (or int64 nanoseconds); omitting it is refused (DEC-0131)",
            given=repr(value),
        )
    return invalid_input(
        field,
        "embargo_width is a required manifest field entering the split fingerprint: a "
        "non-negative Duration (or int64 nanoseconds); omitting it is refused (DEC-0131)",
        given=repr(value),
    )


def require_width_covers_producers(
    field: str, width: Duration, widest: int
) -> Result[Duration]:
    """Refuse a width shorter than the maximum cited-producer bound (DEC-0131)."""
    if width.value_ns >= widest:
        return Ok(width)
    if field == "purge_width":
        return invalid_input(
            field,
            "purge_width must cover the maximum cited-producer warm-up-plus-confirmation "
            "bound; a shorter width would leak, so the manifest is refused (DEC-0131)",
            purge_ns=width.value_ns,
            required_ns=widest,
        )
    return invalid_input(
        field,
        "embargo_width must cover the maximum cited-producer warm-up-plus-confirmation "
        "bound; a shorter width would leak, so the manifest is refused (DEC-0131)",
        embargo_ns=width.value_ns,
        required_ns=widest,
    )


def resolve_manifest_widths(
    *,
    purge_width: object,
    embargo_width: object,
    cited_producers: Sequence[ProducerHorizon],
    world: object,
) -> Result[ManifestWidths]:
    """Admit required purge/embargo widths, producer coverage, and world (AC2)."""
    resolved_purge = admit_required_width("purge_width", purge_width)
    if is_refusal(resolved_purge):
        return resolved_purge
    resolved_embargo = admit_required_width("embargo_width", embargo_width)
    if is_refusal(resolved_embargo):
        return resolved_embargo
    producers = tuple(cited_producers)
    widest = ProducerHorizon.max_bound(producers).value_ns
    covered_purge = require_width_covers_producers("purge_width", resolved_purge.value, widest)
    if is_refusal(covered_purge):
        return covered_purge
    covered_embargo = require_width_covers_producers(
        "embargo_width", resolved_embargo.value, widest
    )
    if is_refusal(covered_embargo):
        return covered_embargo
    resolved_world = coerce_world(world)
    if resolved_world is None:
        return invalid_input(
            "world",
            "world is required and one of the closed set live | replay | simulated",
            given=repr(world),
        )
    return Ok(
        ManifestWidths(
            purge_width=covered_purge.value,
            embargo_width=covered_embargo.value,
            cited_producers=producers,
            world=resolved_world,
        )
    )


def manifest_content(identity: ManifestIdentity) -> dict[str, object]:
    """The manifest's canonical ``fp1`` identity content — the parts that ARE its identity.

    Built identically by :meth:`SplitManifest.try_create` (to derive the split id) and
    :meth:`SplitManifest.fp1_identity` (so a read-back re-fingerprints to the same value).
    Segments are order-significant; cited producers are pre-sorted so producer input order
    never forks the id.
    """
    return {
        "class": "dataset-split-manifest",
        "calendar_identity": identity.calendar_identity.fp1_identity(),
        "segments": [segment.fp1_identity() for segment in identity.segments],
        "seal_boundary": identity.seal_boundary.fp1_identity(),
        "purge_width": identity.purge_width.fp1_identity(),
        "embargo_width": identity.embargo_width.fp1_identity(),
        "world": identity.world.value,
        "cited_producers": [producer.fp1_identity() for producer in identity.cited_producers],
        "format_version": CONTRACT_FORMAT_VERSION,
    }


def fingerprint_manifest(identity: ManifestIdentity) -> Result[Fingerprint]:
    """Fingerprint canonical manifest identity content via ``qmf-core`` (DEC-0108)."""
    return fingerprint(manifest_content(identity))
