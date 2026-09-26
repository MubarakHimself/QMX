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

Boundaries, records, construction, and placement live in sibling modules;
this module re-exports the public names so existing import paths keep working.
"""

from __future__ import annotations

from qmf.data.splits_manifest import SplitManifest
from qmf.data.splits_records import KnowledgeRecord, ProducerHorizon
from qmf.data.splits_types import (
    CONTRACT_FORMAT_VERSION,
    DEFAULT_SPLIT_ROLES,
    KnowledgeKind,
    SegmentRole,
    SplitBoundary,
    SplitSegment,
)

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
