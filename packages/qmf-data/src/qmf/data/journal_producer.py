"""CT-13 — the journal producer and reader over the store seam (AC1, AC2, AC5).

qmf-data's data-policy surface for the durable journal, one layer above the Story 3.1
store seam (:class:`~qmf.data.store.JournalStore`, which owns physical persistence, the
one-writer discipline, idempotent re-append, and storage-failure translation). This
module owns the policy the store seam does not: minting the **gapless per-(writer,
boot-epoch) sequence**, stamping the seven ratified event types, the qmf-data wired
producer surface (data quality, control action), and — above all — **block-on-
unpersistable**.

Two classes.

:class:`JournalWriter` — the producer for **one** stream under **one**
:class:`~qmf.core.WriterId` (one per producing component; AC1). It mints the strictly-
increasing sequence, appends :class:`~qmf.data.journal.JournalEvent`\\ s through the
store, and enforces block-on-unpersistable:

* an event that **cannot be durably persisted** — or a **partial multi-room write**
  (the journal event landed but a linked causal-edge write failed) — is a ``storage
  failure`` refusal that **blocks the command stream** in this writer: the failed event
  is retained (never silently lost) and no later event proceeds until
  :meth:`~JournalWriter.retry_blocked` durably journals it on recovery (AC5; DEC-0137);
* the sequence is **not advanced** on a failed append, so the retry reuses the same
  sequence and the stream stays gapless (AC2);
* the store seam's own second-writer refusal is inherited — a distinct WriterId reaching
  for a held stream does not proceed (AC2; DEC-0113).

:class:`JournalReader` — an **unlimited reader** that reconstructs typed events and
surfaces a detected sequence gap as loss (AC2), never a silent success.

Stdlib + qmf-core + the qmf-data journal vocabulary and store journal seam.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    Retryability,
    World,
    WriterId,
    is_refusal,
    is_unpersistable,
)
from qmf.data.journal import JournalEvent, JournalEventType, detect_sequence_gaps
from qmf.data.store import JournalStore, StoreReceipt
from qmf.data.store.refusals import invalid_input, storage_failure

__all__ = [
    "EdgeWrite",
    "JournalAppendReceipt",
    "JournalReader",
    "JournalWriter",
    "LineageEdgeAppender",
]

# A secondary room write in a multi-room journal operation: given the just-appended
# event's identity fp1, it performs one additional room's write (typically a causal
# lineage edge referencing that fp1) and returns its store receipt or a refusal. A
# partial failure — the journal event committed, a secondary refused — blocks the stream.
EdgeWrite = Callable[[Fingerprint], Result[StoreReceipt]]


@runtime_checkable
class LineageEdgeAppender(Protocol):
    """The typed seam for appending a causal lineage edge (AC4; DEC-0114, DEC-0120).

    A ``typing.Protocol`` the store's :class:`~qmf.data.store.RegistryRoom` satisfies
    structurally, so a multi-room journal-plus-edge write never names the concrete room in
    a signature and stays swappable. Cross-stream causal linkage rides these typed edge
    records — never a timestamp or the ordering key.
    """

    def append_lineage_edge(
        self, edge_stream: object, writer: WriterId, edge: Mapping[str, object]
    ) -> Result[StoreReceipt]:  # pragma: no cover - protocol seam
        """Append one typed lineage edge to a one-writer stream (value-or-refusal)."""
        ...


@dataclass(frozen=True, slots=True)
class JournalAppendReceipt:
    """The receipt of a durably journaled event (AC1, AC5).

    ``event`` is the durable :class:`~qmf.data.journal.JournalEvent` that landed — its
    identity fp1 is ``event.fingerprint``, the value a causal edge references and a
    projection cites. ``store_receipt`` is the Story 3.1 store receipt for the physical
    journal-stream artifact (its content-addressed key, world, and stored/idempotent
    outcome). ``edge_receipts`` carries the store receipts for any linked causal-edge
    writes in a multi-room operation (empty for a single-room append).
    """

    event: JournalEvent
    store_receipt: StoreReceipt
    edge_receipts: tuple[StoreReceipt, ...] = ()


@dataclass(frozen=True, slots=True)
class _PendingWrite:
    """The retained operation of a blocked stream, so recovery loses nothing (AC5)."""

    event: JournalEvent
    extra_writes: tuple[EdgeWrite, ...] = ()


class JournalWriter:
    """The CT-13 producer for one stream under one WriterId (AC1, AC2, AC5).

    Constructed over a :class:`~qmf.data.store.JournalStore` (one world), the holding
    :class:`~qmf.core.WriterId`, and the stream name. Mints the gapless per-(writer,
    boot-epoch) sequence, appends the seven ratified event types, and blocks the command
    stream on an unpersistable or partial-multi-room write until recovery.
    """

    def __init__(
        self,
        journal: JournalStore,
        writer: WriterId,
        *,
        stream_name: str | None = None,
        start: int = 0,
    ) -> None:
        self._journal = journal
        self._writer = writer
        self._stream_name = stream_name if stream_name is not None else writer.stream
        self._next_sequence = start
        self._blocked: _PendingWrite | None = None

    @classmethod
    def resume(
        cls,
        journal: JournalStore,
        writer: WriterId,
        *,
        stream_name: str | None = None,
    ) -> Result[JournalWriter]:
        """Construct a writer whose next sequence resumes past the persisted stream tail (AC2).

        A plain ``JournalWriter(...)`` cannot discover its resume point: on a restart under the
        **same** ``(machine, role, stream, boot_epoch_id)`` it re-mints from ``start = 0`` and
        re-issues sequences already on disk, which :func:`detect_sequence_gaps` then reports as
        permanent ``duplicate`` loss (L10). This factory reads the recorded stream, finds the
        highest sequence *this exact writer* already persisted for its boot-epoch, and starts
        one past it — so a resumed writer never re-issues a sequence and the per-(writer,
        boot-epoch) stream stays gapless. A never-written stream, or a fresh boot-epoch with no
        prior events, resumes at ``0`` (its own independent run). A corrupt stream surfaces as
        the reader's ``storage failure`` refusal, never a silent resume-at-zero that would then
        re-issue and manufacture duplicates.
        """
        name = stream_name if stream_name is not None else writer.stream
        existing = JournalReader(journal).read(name, for_world=journal.world)
        if is_refusal(existing):
            return existing
        start = _resume_sequence(existing.value, writer)
        return Ok(cls(journal, writer, stream_name=name, start=start))

    @property
    def world(self) -> World:
        """The world this writer's journal stream is instantiated for."""
        return self._journal.world

    @property
    def writer(self) -> WriterId:
        """The single :class:`~qmf.core.WriterId` holding this stream."""
        return self._writer

    @property
    def stream_name(self) -> str:
        """The name of the one stream this writer owns."""
        return self._stream_name

    @property
    def next_sequence(self) -> int:
        """The sequence the next successful append will use (unchanged while blocked)."""
        return self._next_sequence

    @property
    def is_blocked(self) -> bool:
        """Whether the command stream is blocked on an unpersistable event (AC5)."""
        return self._blocked is not None

    @property
    def blocked_event(self) -> JournalEvent | None:
        """The retained event whose write is blocked, or ``None`` — never lost (AC5)."""
        return self._blocked.event if self._blocked is not None else None

    # --- append (write) -----------------------------------------------------

    def record(
        self,
        event_type: object,
        payload: Mapping[str, object] | None = None,
        *,
        instant: object,
        outcome: object | None = None,
        correlation_id: object | None = None,
        display_time: object | None = None,
    ) -> Result[JournalAppendReceipt]:
        """Stamp and append one journal event to this writer's stream (AC1, AC2, AC5).

        Builds a :class:`~qmf.data.journal.JournalEvent` at the next gapless sequence and
        appends it. While the stream is **blocked** on a prior unpersistable event, this
        refuses (a ``storage failure``) and consumes no sequence — no later event proceeds
        (AC5). A malformed event (a type outside the seven, a decision without its outcome,
        a float in the payload) is an ``invalid input`` refusal and changes no state. An
        unpersistable append blocks the stream and retains the event; the store's own
        second-writer / cross-world / simulated refusals surface unchanged.
        """
        return self.record_multiroom(
            event_type,
            payload,
            instant=instant,
            outcome=outcome,
            correlation_id=correlation_id,
            display_time=display_time,
        )

    def record_multiroom(
        self,
        event_type: object,
        payload: Mapping[str, object] | None = None,
        *,
        instant: object,
        outcome: object | None = None,
        correlation_id: object | None = None,
        display_time: object | None = None,
        extra_writes: Sequence[EdgeWrite] = (),
    ) -> Result[JournalAppendReceipt]:
        """Append the event plus zero or more linked room writes as one operation (AC5).

        Each entry in ``extra_writes`` is called with the just-appended event's identity
        fp1 and performs one additional room's write (typically a causal lineage edge
        referencing that fp1). A **partial multi-room write** — the journal event committed
        but a secondary refused — blocks the stream and retains the whole operation, so a
        retry re-runs it idempotently and nothing is silently lost (AC5, AC4).
        """
        if self._blocked is not None:
            return self._blocked_refusal()
        built = JournalEvent.try_create(
            event_type=event_type,
            writer=self._writer,
            sequence=self._next_sequence,
            instant=instant,
            world=self.world,
            payload=payload,
            outcome=outcome,
            correlation_id=correlation_id,
            display_time=display_time,
        )
        if is_refusal(built):
            return built
        return self._commit(built.value, tuple(extra_writes))

    def record_data_quality(
        self,
        payload: Mapping[str, object] | None = None,
        *,
        instant: object,
        correlation_id: object | None = None,
        display_time: object | None = None,
    ) -> Result[JournalAppendReceipt]:
        """Record a ``data quality`` event — one of qmf-data's two wired types (AC1)."""
        return self.record(
            JournalEventType.DATA_QUALITY,
            payload,
            instant=instant,
            correlation_id=correlation_id,
            display_time=display_time,
        )

    def record_control_action(
        self,
        subtype: object,
        *,
        instant: object,
        payload: Mapping[str, object] | None = None,
        correlation_id: object | None = None,
        display_time: object | None = None,
    ) -> Result[JournalAppendReceipt]:
        """Record a ``control action`` event — qmf-data's other wired type (AC1).

        ``subtype`` names the declared control-action subtype (e.g. the CT-12 sealed-period
        final look, an adapter-initiated state change) and rides the payload under
        ``control_action_subtype``, so a projection selects on a declared field. A blank
        subtype is an ``invalid input`` refusal.
        """
        if not isinstance(subtype, str) or subtype.strip() == "":
            return invalid_input(
                "control_action_subtype",
                "a control action carries a non-blank declared subtype so a projection "
                "selects on a declared field (DEC-0150)",
                given=repr(subtype),
            )
        merged: dict[str, object] = dict(payload) if payload is not None else {}
        merged["control_action_subtype"] = subtype
        return self.record(
            JournalEventType.CONTROL_ACTION,
            merged,
            instant=instant,
            correlation_id=correlation_id,
            display_time=display_time,
        )

    def retry_blocked(self) -> Result[JournalAppendReceipt]:
        """Retry the blocked write once the store has recovered (AC5).

        The block-on-unpersistable recovery step the component holding the WriterId calls
        after a ``storage failure``: it re-runs the exact retained operation (the journal
        append is idempotent on a byte-identical re-append, and any linked edge writes are
        idempotent too). On success the previously-unpersistable event **is journaled on
        recovery**, the stream unblocks, and the sequence advances; on a still-failing store
        the stream stays blocked. Calling it with nothing blocked is an ``invalid input``
        refusal.
        """
        pending = self._blocked
        if pending is None:
            return invalid_input(
                "retry_blocked",
                "there is no blocked journal write to retry; the command stream is not blocked",
            )
        result, _committed = self._attempt(pending.event, pending.extra_writes)
        if is_refusal(result):
            return result
        self._blocked = None
        self._next_sequence += 1
        return result

    # --- internals ----------------------------------------------------------

    def _commit(
        self, event: JournalEvent, extra_writes: tuple[EdgeWrite, ...]
    ) -> Result[JournalAppendReceipt]:
        """Attempt the operation; block on an unpersistable or partial-multi-room write."""
        result, primary_committed = self._attempt(event, extra_writes)
        if is_refusal(result):
            # Block when the event did not durably land (storage failure) OR a partial
            # multi-room state exists (the journal event committed, a secondary refused):
            # either way the intent must not be silently lost and no later event proceeds.
            if primary_committed or is_unpersistable(result):
                self._blocked = _PendingWrite(event=event, extra_writes=extra_writes)
            return result
        self._next_sequence += 1
        return result

    def _attempt(
        self, event: JournalEvent, extra_writes: tuple[EdgeWrite, ...]
    ) -> tuple[Result[JournalAppendReceipt], bool]:
        """Run the journal append then the secondary writes; report primary-committed.

        Returns ``(result, primary_committed)``. ``primary_committed`` is ``True`` once the
        journal event's append succeeded, so the caller can tell a partial multi-room write
        (secondary refused after the primary landed) from a clean primary failure.
        """
        appended = self._journal.append(self._stream_name, self._writer, event.to_row())
        if is_refusal(appended):
            return appended, False
        edge_receipts: list[StoreReceipt] = []
        for write in extra_writes:
            edge_result = write(event.fingerprint)
            if is_refusal(edge_result):
                return edge_result, True
            edge_receipts.append(edge_result.value)
        receipt = JournalAppendReceipt(
            event=event,
            store_receipt=appended.value,
            edge_receipts=tuple(edge_receipts),
        )
        return Ok(receipt), True

    def _blocked_refusal(self) -> Result[JournalAppendReceipt]:
        """The refusal a new append gets while the stream is blocked (AC5)."""
        pending = self._blocked
        blocked_sequence = pending.event.sequence if pending is not None else self._next_sequence
        return storage_failure(
            "the command stream is blocked on an unpersistable journal event and does not "
            "proceed until that event is durably journaled on recovery (call retry_blocked); "
            "no later event is written and none is silently lost (DEC-0137, DEC-0109)",
            retryability=Retryability.YES,
            context={
                "blocked_stream": self._stream_name,
                "blocked_sequence": blocked_sequence,
                "world": self.world.value,
            },
        )


@dataclass(frozen=True, slots=True)
class JournalReader:
    """An unlimited reader over one writer-scoped journal stream (AC2).

    Reconstructs typed :class:`~qmf.data.journal.JournalEvent`\\ s from the store stream,
    re-verifying each event's fp1, and surfaces a detected sequence gap as loss — never a
    silent success. Constructed over the same :class:`~qmf.data.store.JournalStore` a
    writer appends to; readers are unlimited and take no one-writer hold.
    """

    journal: JournalStore

    def read(self, stream_name: object, *, for_world: object) -> Result[list[JournalEvent]]:
        """Read every event in a stream in order, as typed events (AC2).

        Reconstructs each row through :meth:`JournalEvent.from_row`, which re-verifies the
        fp1 so a corrupt or tampered row is refused rather than read back valid. A
        cross-world read and a never-written stream (``Ok([])``) follow the store seam's
        rules. This does **not** check for gaps — call :meth:`read_checked` for that.
        """
        rows = self.journal.read_stream(stream_name, for_world=for_world)
        if is_refusal(rows):
            return rows
        events: list[JournalEvent] = []
        for row in rows.value:
            built = JournalEvent.from_row(row)
            if is_refusal(built):
                return built
            events.append(built.value)
        return Ok(events)

    def read_checked(
        self, stream_name: object, *, for_world: object, expected_start: int | None = None
    ) -> Result[list[JournalEvent]]:
        """Read a stream and refuse if a per-(writer, boot-epoch) sequence gap is found (AC2).

        Reads the typed events, then runs :func:`detect_sequence_gaps`; a detected gap is a
        ``storage failure`` that **signals loss and is surfaced**, never a silent success.
        On a gapless stream the events are returned in order.

        When ``expected_start`` is not supplied it is **derived from the stream** — its own
        minimum observed sequence — rather than defaulting to ``0`` (L10). A writer legitimately
        resumed from ``start = N`` (see :meth:`resume`) begins its stream at N, and a fixed
        ``expected_start = 0`` would falsely alarm a "gap" from 0 to N; deriving the base still
        surfaces every interior gap and any duplicate. Pass an explicit ``expected_start`` to
        assert a specific base (e.g. ``0`` to require a from-zero stream).
        """
        events = self.read(stream_name, for_world=for_world)
        if is_refusal(events):
            return events
        if expected_start is None:
            expected_start = _derived_expected_start(events.value)
        gap = detect_sequence_gaps(events.value, expected_start=expected_start)
        if is_refusal(gap):
            return gap
        return events


def _resume_sequence(events: Sequence[JournalEvent], writer: WriterId) -> int:
    """One past the highest sequence ``writer`` already persisted, or ``0`` if none (L10).

    Matches on the full :class:`~qmf.core.WriterId` identity (machine, role, stream,
    boot_epoch_id): resuming under the same boot-epoch continues that epoch's gapless
    sequence, while a fresh boot-epoch (no matching events) starts its own run at ``0``.
    """
    persisted = [event.sequence for event in events if event.writer == writer]
    return max(persisted) + 1 if persisted else 0


def _derived_expected_start(events: Sequence[JournalEvent]) -> int:
    """The stream's own first sequence — the base :meth:`JournalReader.read_checked` checks
    contiguity from when the caller declares none (L10).

    A stream legitimately resumed from ``start = N`` begins at N; defaulting the expected start
    to ``0`` would falsely alarm a "gap" from 0 to N. Deriving the base from the minimum
    observed sequence still surfaces every interior gap and any duplicate — only an
    undetectable missing prefix (a lost sequence 0 that leaves no trace) is not conjured into
    a false alarm.
    """
    return min((event.sequence for event in events), default=0)
