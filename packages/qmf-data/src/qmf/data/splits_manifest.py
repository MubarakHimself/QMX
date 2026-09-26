"""CT-12 fingerprinted dataset-split manifest.

Split from :mod:`qmf.data.splits` so the public module stays under the
Skylos god-file limits. Callers keep importing :class:`SplitManifest` from
:mod:`qmf.data.splits`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from qmf.core import (
    CalendarIdentity,
    Duration,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    is_refusal,
)
from qmf.data.splits_build import (
    ManifestIdentity,
    ManifestShape,
    ManifestWidths,
    fingerprint_manifest,
    manifest_content,
    resolve_manifest_shape,
    resolve_manifest_widths,
)
from qmf.data.splits_partition import assign_instant_record
from qmf.data.splits_records import KnowledgeRecord, ProducerHorizon
from qmf.data.splits_types import (
    DEFAULT_SPLIT_ROLES,
    SegmentRole,
    SplitBoundary,
    SplitSegment,
)
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = ["SplitManifest"]


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
        shape = resolve_manifest_shape(
            calendar_identity=calendar_identity,
            segments=segments,
            seal_boundary=seal_boundary,
        )
        if is_refusal(shape):
            return shape
        widths = resolve_manifest_widths(
            purge_width=purge_width,
            embargo_width=embargo_width,
            cited_producers=cited_producers,
            world=world,
        )
        if is_refusal(widths):
            return widths
        return _mint_split_manifest(cls, shape.value, widths.value)

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
        return assign_instant_record(
            self.segments,
            self.embargo_width.value_ns,
            self.purge_width.value_ns,
            record.observed_at,
            record.knowledge_time,
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint` and its value is :attr:`split_id`."""
        return manifest_content(
            ManifestIdentity(
                calendar_identity=self.calendar_identity,
                segments=self.segments,
                seal_boundary=self.seal_boundary,
                purge_width=self.purge_width,
                embargo_width=self.embargo_width,
                world=self.world,
                cited_producers=self.cited_producers,
            )
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


def _mint_split_manifest(
    cls: type[SplitManifest],
    shape: ManifestShape,
    widths: ManifestWidths,
) -> Result[SplitManifest]:
    """Sort cited producers, fingerprint identity content, and construct the manifest."""
    ordered_producers = tuple(
        sorted(
            widths.cited_producers,
            key=lambda p: (p.producer, p.warmup_plus_confirmation.value_ns),
        )
    )
    fp = fingerprint_manifest(
        ManifestIdentity(
            calendar_identity=shape.calendar_identity,
            segments=shape.segments,
            seal_boundary=shape.seal_boundary,
            purge_width=widths.purge_width,
            embargo_width=widths.embargo_width,
            world=widths.world,
            cited_producers=ordered_producers,
        )
    )
    if is_refusal(fp):  # pragma: no cover - content is canonical by construction
        return fp
    return Ok(
        cls(
            calendar_identity=shape.calendar_identity,
            segments=shape.segments,
            seal_boundary=shape.seal_boundary,
            purge_width=widths.purge_width,
            embargo_width=widths.embargo_width,
            world=widths.world,
            cited_producers=ordered_producers,
            fingerprint=fp.value,
        )
    )
