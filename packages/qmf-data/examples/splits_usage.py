"""Reference usage — CT-12 dataset splits and the no-peek seal (Story 3.4; COMP-QMF-DATA).

Executable::

    python packages/qmf-data/examples/splits_usage.py

Shows the six things Story 3.4 pins down:

1. A fingerprinted, time-ordered, non-overlapping split manifest whose ``split_id`` is
   derived from its fp1 (never minted), split by default into train/validation/sealed-test.
2. Purge and embargo widths are required and default to the maximum warm-up-plus-
   confirmation-delay bound across every cited producer, so a longer-horizon producer
   refuses rather than leaks.
3. Records partition by knowledge time; a record straddling a boundary is refused unless
   the declared embargo covers the gap.
4. The newest sealed window is a no-peek lock enforced as a policy rejection at every read
   boundary (raw archive, processed, research door, restored backup) — never a silent empty.
5. The one authorized final look is journaled as a named control-action subtype in CT-13,
   a second look is refused, and the sealed set is never recycled.
6. A row carrying a calendar identity different from the manifest's pinned one is refused,
   never rescaled.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Instant,
    Result,
    TradingDate,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data import (
    FINAL_LOOK_SUBTYPE,
    SEAL_CONTROL_STREAM,
    EvidenceStore,
    HoldoutSeal,
    KnowledgeKind,
    KnowledgeRecord,
    ProducerHorizon,
    ReadBoundary,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
)

T = TypeVar("T")

# The holdout window length is configuration (registry:historical_holdout_months), taken as
# a value here — never a hardcoded literal inside qmf-data (DEC-0119).
HISTORICAL_HOLDOUT_MONTHS = 12


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a call we require to succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    """A real check (not a bare ``assert``, which ``-O`` strips) for a demonstrated fact."""
    if not condition:
        raise AssertionError(f"expected {what}")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"), "calendar")


def _instant_boundary(value_ns: int) -> SplitBoundary:
    return _unwrap(
        SplitBoundary.try_create(_unwrap(Instant.try_create(value_ns), "instant")), "bound"
    )


def _trading_boundary(calendar: CalendarIdentity, year: int, month: int, day: int) -> SplitBoundary:
    civil = _unwrap(CivilDate.try_create(year, month, day), "civil date")
    trading = _unwrap(TradingDate.try_create(calendar, civil), "trading date")
    return _unwrap(SplitBoundary.try_create(trading), "trading boundary")


def build_manifest() -> tuple[SplitManifest, int]:
    """A default three-way split whose widths default to the max cited-producer bound."""
    calendar = _calendar()
    segments = _unwrap(
        SplitManifest.default_split_segments(
            [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
        ),
        "default segments",
    )
    producers = [
        _unwrap(ProducerHorizon.try_create("indicator:sma-20", 40), "producer sma"),
        _unwrap(ProducerHorizon.try_create("structure:swing", 50), "producer swing"),
    ]
    default_width = ProducerHorizon.max_bound(producers)
    manifest = _unwrap(
        SplitManifest.try_create(
            calendar_identity=calendar,
            segments=segments,
            seal_boundary=_trading_boundary(calendar, 2025, 1, 1),
            purge_width=default_width,
            embargo_width=default_width,
            world=World.REPLAY,
            cited_producers=producers,
        ),
        "manifest",
    )
    _require(manifest.split_id.startswith("fp1:sha256:"), "split_id is an fp1 fingerprint")
    _require([seg.role for seg in manifest.segments] == list(SegmentRole), "default three roles")
    # The id is derived, so a re-fingerprint of the read-back identity content matches it.
    _require(
        _unwrap(fingerprint(manifest.fp1_identity()), "re-fingerprint").value == manifest.split_id,
        "split_id is derived from fp1, never minted",
    )
    return manifest, default_width.value_ns


def partition_records(manifest: SplitManifest) -> tuple[str, str]:
    """Knowledge-time partitioning; a straddling record refuses without embargo cover."""
    clean = _unwrap(
        KnowledgeRecord.try_create(
            observed_at=1_500, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR
        ),
        "clean record",
    )
    placed = _unwrap(manifest.partition_record(clean), "partitioned")
    _require(placed is SegmentRole.VALIDATION, "knowledge-time 1500 lands in validation")

    straddle = _unwrap(
        KnowledgeRecord.try_create(
            observed_at=1_900, knowledge_time=2_100, kind=KnowledgeKind.STRUCTURE
        ),
        "straddling record",
    )
    refused = manifest.partition_record(straddle)
    _require(is_refusal(refused), "a straddling record beyond the embargo is refused")
    category = refused.category.value if is_refusal(refused) else "unexpected-ok"
    return placed.value, category


def seal_enforced_everywhere(
    seal: HoldoutSeal, calendar: CalendarIdentity
) -> tuple[list[str], str]:
    """The seal refuses a sealed read at every read boundary; a pre-seal read is allowed."""
    sealed_position = _trading_boundary(calendar, 2025, 6, 1)
    outcomes: list[str] = []
    for boundary in ReadBoundary:
        result = seal.guard(sealed_position, boundary=boundary)
        _require(is_refusal(result), f"sealed read refused at {boundary.value}")
        outcomes.append(result.category.value if is_refusal(result) else "unexpected-ok")
    pre_seal = _trading_boundary(calendar, 2024, 6, 1)
    allowed = seal.guard(pre_seal, boundary=ReadBoundary.RESEARCH_DOOR)
    _require(is_ok(allowed), "a pre-seal read is allowed")
    return outcomes, "allowed" if is_ok(allowed) else "unexpected-refusal"


def one_final_look(
    seal: HoldoutSeal, manifest: SplitManifest, store: EvidenceStore
) -> tuple[str, str, str]:
    """Exactly one authorized final look, journaled as a control-action subtype."""
    bundle = _unwrap(store.for_world(World.REPLAY), "world store")
    journal = bundle.journal
    writer = _unwrap(
        WriterId.try_create("workstation", "qmf-data", SEAL_CONTROL_STREAM, "boot-1"), "writer"
    )
    at = _unwrap(Instant.try_create(1_700_000_000_000_000_000), "at")
    first = _unwrap(
        seal.authorize_final_look(journal, writer, at=at, split_id=manifest.split_id),
        "first final look",
    )
    _require(first.room_role.value == "journal", "the final look lands in the journal room")

    events = _unwrap(journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.REPLAY), "events")
    _require(len(events) == 1, "exactly one journaled final look")
    subtype = events[0].get("control_action_subtype")
    _require(subtype == FINAL_LOOK_SUBTYPE, "journaled as the sealed-period-final-look subtype")

    second = seal.authorize_final_look(journal, writer, at=at, split_id=manifest.split_id)
    _require(is_refusal(second), "a second final look is refused")
    second_category = second.category.value if is_refusal(second) else "unexpected-ok"

    still = seal.guard(
        _trading_boundary(seal.calendar_identity, 2025, 6, 1), boundary=ReadBoundary.RESEARCH_DOOR
    )
    _require(is_refusal(still), "the sealed set is never recycled by the final look")
    still_category = still.category.value if is_refusal(still) else "unexpected-ok"
    return str(subtype), second_category, still_category


def foreign_calendar_refused(manifest: SplitManifest) -> str:
    """A row carrying a different calendar identity is refused, never rescaled."""
    foreign = _unwrap(CalendarIdentity.try_create("forex-17NY", "v4", "2025a"), "foreign calendar")
    refused = manifest.admits_calendar(foreign)
    _require(is_refusal(refused), "a foreign calendar identity is refused")
    return refused.category.value if is_refusal(refused) else "unexpected-ok"


def main() -> None:
    manifest, width_ns = build_manifest()
    print(f"split manifest: 3 default segments, split_id derived from fp1 (widths={width_ns} ns)")

    placed, straddle_category = partition_records(manifest)
    print(f"record partition: knowledge-time 1500 -> {placed}; straddle -> {straddle_category}")

    seal = _unwrap(
        HoldoutSeal.from_manifest(manifest, HISTORICAL_HOLDOUT_MONTHS), "seal from manifest"
    )
    outcomes, pre_seal = seal_enforced_everywhere(seal, manifest.calendar_identity)
    print(f"seal at {len(outcomes)} read boundaries: {outcomes[0]}; pre-seal read: {pre_seal}")

    with tempfile.TemporaryDirectory(prefix="qmf-splits-") as tmp:
        store = EvidenceStore(Path(tmp))
        subtype, second_category, still_category = one_final_look(seal, manifest, store)
    print(f"final look: {subtype}; second look: {second_category}; after look: {still_category}")

    foreign = foreign_calendar_refused(manifest)
    print(f"foreign calendar row: {foreign}")


if __name__ == "__main__":
    main()
