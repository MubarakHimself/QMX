"""Single append-only journal with global monotonic ``journal_seq`` (FR-Q23–FR-Q25).

Daemon-owned durable events write only here. ``journal_seq`` is the system's sole
total-order key; per-scope streams are filtered projections whose ``seq`` is a
derived index. Evidence-store appends emit announcement events carrying the
record ``fp1`` (telemetry exempt). Durable rows carry ``occurred_at`` /
``recorded_at`` from the injected qmf-core clock (FR-Q25).
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.daemon.journal.clock import (
    DaemonClock,
    DurableTimestamps,
    refuse_worker_evidence_timestamp,
)
from qma.daemon.journal.fold_contracts import FoldContract, FoldContractRegistry
from qma.daemon.journal.stores import (
    ANNOUNCEMENT_REQUIRED_STORES,
    TELEMETRY_STORE,
    FoldMetadata,
    StoreDeclaration,
    StoreRegistry,
    announce_event_for_store,
)
from qma.daemon.persistence.substrate import PersistenceSubstrate
from qma.wire.envelope import ScopePathError, ScopeSegment, parse_scope_path
from qmf.core import (
    Clock,
    Fingerprint,
    Instant,
    Ok,
    Result,
    World,
    WriterId,
    fingerprint,
    is_refusal,
)
from qmf.data.store.journal import JournalStore
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_JOURNAL_STREAM",
    "AnnouncementOutcome",
    "AuthoritativeJournal",
    "JournalAppendReceipt",
    "JournalEventRecord",
    "ScopeProjectionCursor",
]

DAEMON_JOURNAL_STREAM: Final[str] = "qma-daemon-events"
_EVENT_CLASS: Final[str] = "qma-journal-event"
_FIRST_JOURNAL_SEQ: Final[int] = 1


@dataclass(frozen=True, slots=True)
class JournalEventRecord:
    """One durable daemon journal event, ordered by ``journal_seq``."""

    journal_seq: int
    event: str
    scope_path: tuple[ScopeSegment, ...]
    payload: Mapping[str, object]
    world: str
    fingerprint: str
    occurred_at: int
    recorded_at: int

    def to_row(self) -> dict[str, object]:
        """JSON-native row for the single append-only journal stream."""
        return {
            "class": _EVENT_CLASS,
            "world": self.world,
            "event": self.event,
            "journal_seq": self.journal_seq,
            "occurred_at": self.occurred_at,
            "recorded_at": self.recorded_at,
            "scope_path": [segment.to_dict() for segment in self.scope_path],
            "payload": dict(self.payload),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class JournalAppendReceipt:
    """Receipt for a durable append that allocated the next ``journal_seq``."""

    record: JournalEventRecord
    store_receipt: StoreReceipt
    scope_seq: int


@dataclass(frozen=True, slots=True)
class AnnouncementOutcome:
    """Result of the announcement law for one evidence-store append."""

    status: Literal["announced", "exempted"]
    store: str
    record_fp1: str
    journal_seq: int | None = None
    append: JournalAppendReceipt | None = None


@dataclass(frozen=True, slots=True)
class ScopeProjectionCursor:
    """Derived per-scope projection index — never ``journal_seq`` itself."""

    scope_path: tuple[ScopeSegment, ...]
    seq: int


def _freeze_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(payload))


def _scope_key(scope_path: Sequence[ScopeSegment]) -> tuple[tuple[str, str], ...]:
    return tuple((segment.kind, segment.id) for segment in scope_path)


def _coerce_fingerprint(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid_input(
        "record_fp1",
        "an evidence announcement carries the record's fp1:sha256:<hex> fingerprint (FR-Q24; AD-6)",
        given=repr(value),
    )


def _identity_content(
    *,
    journal_seq: int,
    event: str,
    scope_path: Sequence[ScopeSegment],
    payload: Mapping[str, object],
    world: str,
    occurred_at: int,
    recorded_at: int,
) -> dict[str, object]:
    return {
        "class": _EVENT_CLASS,
        "event": event,
        "journal_seq": journal_seq,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "scope_path": [segment.to_dict() for segment in scope_path],
        "payload": dict(payload),
        "world": world,
    }


class AuthoritativeJournal:
    """Sole durable append target for daemon-owned events (FR-Q23–FR-Q25; AD-6).

    Allocates the global monotonic ``journal_seq``, stamps ``occurred_at`` /
    ``recorded_at`` from the injected qmf-core clock, writes one JSONL stream
    through the persistence substrate's ``JournalStore``, derives per-scope
    projection indices, validates the closed store list and v1 fold contracts,
    and emits evidence announcements.
    """

    def __init__(
        self,
        *,
        journal_store: JournalStore,
        writer: WriterId,
        world: World,
        clock: DaemonClock,
        stores: StoreRegistry | None = None,
        folds: FoldContractRegistry | None = None,
        next_journal_seq: int = _FIRST_JOURNAL_SEQ,
        scope_seq_state: dict[tuple[tuple[str, str], ...], int] | None = None,
    ) -> None:
        self._journal = journal_store
        self._writer = writer
        self._world = world
        self._clock = clock
        self._stores = stores if stores is not None else StoreRegistry()
        self._folds = folds if folds is not None else FoldContractRegistry()
        self._next_seq = next_journal_seq
        self._scope_seq = scope_seq_state if scope_seq_state is not None else {}
        self._lock = threading.Lock()
        self._closed = False

    @classmethod
    def bind(
        cls,
        substrate: PersistenceSubstrate,
        *,
        clock: Clock | DaemonClock,
    ) -> Result[AuthoritativeJournal]:
        """Bind the authoritative journal to the sole-writer persistence substrate.

        Resumes ``journal_seq`` from the durable stream so restarts continue the
        global monotonic total order. ``clock`` is the injected qmf-core clock
        (or a :class:`DaemonClock` wrapping one) — never host local time.
        """
        journal = substrate.journal
        writer = substrate.writer
        world = substrate.world_store.world
        daemon_clock = clock if isinstance(clock, DaemonClock) else DaemonClock(clock)
        resume = cls._resume_state(journal, world=world)
        if is_refusal(resume):
            return resume
        next_seq, scope_state = resume.value
        return Ok(
            cls(
                journal_store=journal,
                writer=writer,
                world=world,
                clock=daemon_clock,
                next_journal_seq=next_seq,
                scope_seq_state=scope_state,
            )
        )

    @staticmethod
    def _resume_state(
        journal: JournalStore, *, world: World
    ) -> Result[tuple[int, dict[tuple[tuple[str, str], ...], int]]]:
        rows = journal.read_stream(DAEMON_JOURNAL_STREAM, for_world=world)
        if is_refusal(rows):
            return rows
        max_seq = 0
        scope_seq: dict[tuple[tuple[str, str], ...], int] = {}
        for row in rows.value:
            raw_seq = row.get("journal_seq")
            if isinstance(raw_seq, int) and not isinstance(raw_seq, bool) and raw_seq > max_seq:
                max_seq = raw_seq
            raw_scope = row.get("scope_path")
            if isinstance(raw_scope, list):
                try:
                    segments = parse_scope_path(cast("list[object]", raw_scope))
                except ScopePathError:
                    segments = None
                if segments is not None:
                    key = _scope_key(segments)
                    scope_seq[key] = scope_seq.get(key, 0) + 1
        return Ok((max_seq + 1 if max_seq >= _FIRST_JOURNAL_SEQ else _FIRST_JOURNAL_SEQ, scope_seq))

    @property
    def stores(self) -> StoreRegistry:
        """Closed-store declaration registry (list + fold metadata)."""
        return self._stores

    @property
    def folds(self) -> FoldContractRegistry:
        """V1 fold-contract registry (FR-Q25)."""
        return self._folds

    @property
    def clock(self) -> DaemonClock:
        """Daemon clock facade over the injected qmf-core clock (FR-Q25)."""
        return self._clock

    @property
    def next_journal_seq(self) -> int:
        """The ``journal_seq`` the next append will allocate."""
        return self._next_seq

    @property
    def stream_name(self) -> str:
        """The single append-only journal stream name."""
        return DAEMON_JOURNAL_STREAM

    def declare_store(
        self,
        name: object,
        *,
        fold_metadata: FoldMetadata | None = None,
    ) -> Result[StoreDeclaration]:
        """Validate and commit a closed-list store/projection declaration."""
        return self._stores.declare(name, fold_metadata=fold_metadata)

    def register_fold(self, fold_id: object) -> Result[FoldContract]:
        """Register a ratified v1 fold contract; refuse undeclared folds."""
        return self._folds.register(fold_id)

    def stamp_durable(
        self,
        *,
        occurred_at: Instant | int | None = None,
        worker_authored_timestamp: object = None,
    ) -> Result[DurableTimestamps]:
        """Stamp ``occurred_at`` / ``recorded_at`` from the injected clock."""
        return self._clock.stamp_durable(
            occurred_at=occurred_at,
            worker_authored_timestamp=worker_authored_timestamp,
        )

    def stamp_evidence_record(
        self,
        record: dict[str, object],
        *,
        occurred_at: Instant | int | None = None,
        journal_seq: int | None = None,
        announcement_bound: bool = True,
        worker_authored_timestamp: object = None,
    ) -> Result[dict[str, object]]:
        """Stamp a durable evidence record; refuse worker-authored timestamps."""
        return self._clock.stamp_evidence_record(
            record,
            occurred_at=occurred_at,
            journal_seq=journal_seq,
            announcement_bound=announcement_bound,
            worker_authored_timestamp=worker_authored_timestamp,
        )

    def append_event(
        self,
        event: object,
        *,
        scope_path: object = (),
        payload: Mapping[str, object] | None = None,
        occurred_at: Instant | int | None = None,
        worker_authored_timestamp: object = None,
    ) -> Result[JournalAppendReceipt]:
        """Append one daemon-owned event, allocating the next ``journal_seq``.

        Writes only to the single append-only journal. Per-scope ``seq`` is a
        derived projection index of the scope named last — never ``journal_seq``.
        Stamps ``occurred_at`` / ``recorded_at`` from the injected clock.
        """
        if self._closed:
            return policy_rejection(
                "authoritative_journal",
                "the authoritative journal is closed and accepts no further appends",
            )
        if not isinstance(event, str) or event.strip() == "" or "." not in event:
            return invalid_input(
                "event",
                "a daemon journal event is a non-empty noun.verb name (FR-Q23; AD-6)",
                given=repr(event),
            )
        try:
            segments = parse_scope_path(scope_path)
        except Exception as exc:
            return invalid_input(
                "scope_path",
                f"scope_path must obey the fixed ancestor order: {exc}",
                given=repr(scope_path),
            )
        body: Mapping[str, object] = payload if payload is not None else {}

        stamps = self._clock.stamp_durable(
            occurred_at=occurred_at,
            worker_authored_timestamp=worker_authored_timestamp,
        )
        if is_refusal(stamps):
            return stamps

        with self._lock:
            journal_seq = self._next_seq
            key = _scope_key(segments)
            scope_seq = self._scope_seq.get(key, 0) + 1
            identity = _identity_content(
                journal_seq=journal_seq,
                event=event,
                scope_path=segments,
                payload=body,
                world=self._world.value,
                occurred_at=stamps.value.occurred_at,
                recorded_at=stamps.value.recorded_at,
            )
            fp_result = fingerprint(identity)
            if is_refusal(fp_result):
                return fp_result
            record = JournalEventRecord(
                journal_seq=journal_seq,
                event=event,
                scope_path=segments,
                payload=_freeze_payload(body),
                world=self._world.value,
                fingerprint=fp_result.value.value,
                occurred_at=stamps.value.occurred_at,
                recorded_at=stamps.value.recorded_at,
            )
            # Store fingerprints the full row (including the embedded identity fp1);
            # do not present the identity-only fingerprint — it would mismatch.
            written = self._journal.append(
                DAEMON_JOURNAL_STREAM,
                self._writer,
                record.to_row(),
            )
            if is_refusal(written):
                return written
            self._next_seq = journal_seq + 1
            self._scope_seq[key] = scope_seq
            return Ok(
                JournalAppendReceipt(
                    record=record,
                    store_receipt=written.value,
                    scope_seq=scope_seq,
                )
            )

    def announce_evidence_append(
        self,
        store: object,
        record_fp1: object,
        *,
        scope_path: object = (),
        extra_payload: Mapping[str, object] | None = None,
        worker_authored_timestamp: object = None,
    ) -> Result[AnnouncementOutcome]:
        """Emit a journal announcement for a declared evidence-store append (FR-Q24).

        Covers ledger, artifact, staging, and admitted MemoryProvider stores.
        The telemetry store is the one exemption — no journal announcement is
        emitted and no ``journal_seq`` is allocated for that path. Worker-authored
        evidence timestamps are refused (FR-Q25).
        """
        if worker_authored_timestamp is not None:
            return refuse_worker_evidence_timestamp(attempted=worker_authored_timestamp)
        if not isinstance(store, str) or store.strip() == "":
            return invalid_input(
                "store",
                "an evidence announcement names a declared store (FR-Q24; AD-6)",
                given=repr(store),
            )
        fp = _coerce_fingerprint(record_fp1)
        if is_refusal(fp):
            return fp

        if store == TELEMETRY_STORE:
            return Ok(
                AnnouncementOutcome(
                    status="exempted",
                    store=store,
                    record_fp1=fp.value.value,
                )
            )

        if store not in ANNOUNCEMENT_REQUIRED_STORES:
            # Outside the announcement-bound set: either not closed, or a
            # journal-derived projection that is not an independent evidence store.
            if store not in self._stores.closed_list:
                return policy_rejection(
                    "evidence_announcement",
                    "an evidence announcement names a closed independent evidence "
                    "store; a store outside the closed list may not be announced "
                    "(FR-Q23, FR-Q24; AD-6)",
                    store=store,
                )
            return policy_rejection(
                "evidence_announcement",
                "the announcement law binds only ledger, artifact, staging, and "
                "admitted MemoryProvider stores; other closed stores are not "
                "announcement targets (FR-Q24; AD-6, AD-23)",
                store=store,
            )

        event_name = announce_event_for_store(store)
        if event_name is None:
            return policy_rejection(
                "evidence_announcement",
                "no announcement event is registered for this store",
                store=store,
            )

        # Materialize the independent-store schema on first in-scope write.
        materialized = self._stores.materialize_on_first_write(store)
        if is_refusal(materialized):
            return materialized

        payload: dict[str, object] = {
            "store": store,
            "record_fp1": fp.value.value,
        }
        if extra_payload:
            for key, value in extra_payload.items():
                if key in {"store", "record_fp1"}:
                    continue
                payload[key] = value

        appended = self.append_event(event_name, scope_path=scope_path, payload=payload)
        if is_refusal(appended):
            return appended
        return Ok(
            AnnouncementOutcome(
                status="announced",
                store=store,
                record_fp1=fp.value.value,
                journal_seq=appended.value.record.journal_seq,
                append=appended.value,
            )
        )

    def read_all(self) -> Result[list[dict[str, object]]]:
        """Read the single journal stream in durable append order."""
        return self._journal.read_stream(DAEMON_JOURNAL_STREAM, for_world=self._world)

    def scope_projection(self, scope_path: object) -> Result[list[tuple[int, dict[str, object]]]]:
        """Filtered per-scope projection with derived ``seq`` (not ``journal_seq``).

        Returns ``(scope_seq, row)`` pairs in ``journal_seq`` order for rows whose
        ``scope_path`` equals or extends the requested scope prefix.
        """
        try:
            wanted = parse_scope_path(scope_path)
        except ScopePathError as exc:
            return invalid_input(
                "scope_path",
                f"scope_path must obey the fixed ancestor order: {exc}",
                given=repr(scope_path),
            )
        rows = self.read_all()
        if is_refusal(rows):
            return rows
        projected: list[tuple[int, dict[str, object]]] = []
        scope_seq = 0
        for row in rows.value:
            raw_scope = row.get("scope_path", [])
            try:
                row_scope = parse_scope_path(raw_scope)
            except ScopePathError:
                row_scope = None
            if row_scope is None:
                continue
            # Prefix filter: include events at or under the requested scope.
            if wanted and (len(row_scope) < len(wanted) or row_scope[: len(wanted)] != wanted):
                continue
            scope_seq += 1
            projected.append((scope_seq, row))
        return Ok(projected)

    def close(self) -> None:
        """Mark the journal closed; the substrate still owns the underlying store."""
        self._closed = True
