"""Task-owned Task Ledger store under ``dispatch_lease`` (CT-51; FR-Q57, FR-Q58).

One ledger per Task for life, persisted in the daemon through the wire so it
survives the worker. Append rights follow ``dispatch_lease`` alone.
``before_ledger_append`` validates every append without discarding evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.content import content_address
from qma.core.ontology import ActorId
from qma.core.plugins.hooks import HookResult
from qma.core.ports.ledgers import (
    TaskLedgerEntry,
    missing_task_completed_fields,
    named_lease_kind,
    parse_task_ledger_entry,
    stamp_hook_returned_ledger_entry,
)
from qma.core.vocabulary.enums import LeaseKind, TaskLedgerEntryKind
from qma.daemon.hooks.ledger_gate import (
    LedgerQuarantineStream,
    evaluate_before_ledger_append,
)
from qma.daemon.journal.authoritative import AnnouncementOutcome, AuthoritativeJournal
from qma.daemon.journal.clock import refuse_worker_evidence_timestamp
from qma.daemon.taskgraph.records import DispatchLease, TaskLedger, TaskRecord
from qma.wire.envelope import WireEnvelope
from qma.wire.vocabulary import WireEvent, WireQuery
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "TASK_LEDGER_STORE_NAME",
    "TaskCompletionAppendResult",
    "TaskLedgerStore",
    "TaskLedgerWireReceipt",
]


TASK_LEDGER_STORE_NAME: Final[str] = "task_ledger"
_WIRE_PROTOCOL: Final[str] = "1.0.0"
_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(
        boot_epoch_id="task-ledger",
        wall_instants=walls,
        monotonic_ns=monos,
    )


@dataclass(frozen=True, slots=True)
class TaskCompletionAppendResult:
    """TaskCompleted append outcome: the entry is written even when completion is refused."""

    ledger: TaskLedger
    entry: Mapping[str, object]
    completion_admitted: bool
    missing_fields: tuple[str, ...] = ()
    refusal: TypedRefusal | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "ledger": dict(self.ledger.to_payload()),
            "entry": dict(self.entry),
            "completion_admitted": self.completion_admitted,
            "missing_fields": list(self.missing_fields),
            "discarded": False,
        }
        if self.refusal is not None:
            payload["refusal"] = {
                "category": self.refusal.category.value,
                "field": self.refusal.context.get("field"),
                "reason": self.refusal.context.get("reason"),
            }
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class TaskLedgerWireReceipt:
    """Daemon persist result: store row plus the ``ledger.updated`` wire event."""

    ledger: TaskLedger
    entry: Mapping[str, object]
    event: WireEnvelope
    announcement: AnnouncementOutcome | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "store": TASK_LEDGER_STORE_NAME,
            "ledger": dict(self.ledger.to_payload()),
            "entry": dict(self.entry),
            "event": self.event.to_dict(),
            "survives_worker": True,
        }
        if self.announcement is not None:
            payload["announcement"] = {
                "status": self.announcement.status,
                "store": self.announcement.store,
                "record_fp1": self.announcement.record_fp1,
            }
        return MappingProxyType(payload)


def _task_id_from_scope(envelope: WireEnvelope) -> str | None:
    for segment in envelope.scope_path:
        if segment.kind == "task":
            return segment.id
    return None


@dataclass
class TaskLedgerStore:
    """Independent Task Ledger store — one ledger per Task, daemon-owned."""

    _ledgers: dict[str, TaskLedger] = field(default_factory=dict[str, TaskLedger])
    _leases: dict[str, DispatchLease] = field(default_factory=dict[str, DispatchLease])
    _owners: dict[str, ActorId] = field(default_factory=dict[str, ActorId])
    _clock: Clock = field(default_factory=_default_clock)
    _journal: AuthoritativeJournal | None = None
    _entry_seq: dict[str, int] = field(default_factory=dict[str, int])
    _quarantine: LedgerQuarantineStream = field(default_factory=LedgerQuarantineStream)

    def __post_init__(self) -> None:
        if self._journal is not None:
            self._quarantine.bind_projection(self._journal.stores)

    @property
    def quarantine(self) -> LedgerQuarantineStream:
        return self._quarantine

    def open_for_task(self, task: TaskRecord | str, *, owner: ActorId | None = None) -> TaskLedger:
        """Create or return the one Task-owned ledger for this Task's life."""
        if isinstance(task, TaskRecord):
            task_id = task.id
            resolved_owner = owner if owner is not None else task.owner
            seed = task.ledger if task.ledger is not None else TaskLedger(task_id=task_id)
        else:
            task_id = task
            resolved_owner = owner
            seed = TaskLedger(task_id=task_id)
        existing = self._ledgers.get(task_id)
        if existing is not None:
            return existing
        if seed.task_id != task_id:
            msg = "TaskLedger.task_id must equal the Task id"
            raise ValueError(msg)
        self._ledgers[task_id] = seed
        if resolved_owner is not None:
            self._owners[task_id] = resolved_owner
        return seed

    def get(self, task_id: str) -> TaskLedger | None:
        return self._ledgers.get(task_id)

    def lease_for(self, task_id: str) -> DispatchLease | None:
        return self._leases.get(task_id)

    def grant(self, lease: DispatchLease) -> Result[DispatchLease]:
        """Record ``dispatch_lease`` without writing a ``reassigned`` entry."""
        kind = named_lease_kind(lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.DISPATCH_LEASE:
            return self._refuse_wrong_lease(kind.value)
        self.open_for_task(lease.task_id, owner=lease.owner)
        self._leases[lease.task_id] = lease
        self._owners[lease.task_id] = lease.owner
        return Ok(lease)

    def append(
        self,
        entry: Mapping[str, object],
        *,
        lease: object,
        task_id: str | None = None,
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
    ) -> Result[TaskLedger]:
        """Persist one entry. Agent appends require this Task's ``dispatch_lease``."""
        kind = named_lease_kind(lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.DISPATCH_LEASE:
            return self._refuse_wrong_lease(kind.value)
        if not isinstance(lease, DispatchLease):
            return invalid_input(
                "dispatch_lease",
                "Task Ledger append requires a dispatch_lease (CT-51; FR-Q57)",
            )
        resolved_task = task_id if task_id is not None else lease.task_id
        if lease.task_id != resolved_task:
            return policy_rejection(
                "dispatch_lease",
                "no Task Ledger spans two Tasks; append rights follow that Task's "
                "dispatch_lease (CT-51; FR-Q57)",
                ledger_task_id=resolved_task,
                lease_task_id=lease.task_id,
            )
        self.open_for_task(resolved_task, owner=lease.owner)
        held = self._leases.get(resolved_task)
        if held is None:
            self._leases[resolved_task] = lease
            held = lease
        return self._append_validated(
            entry,
            lease=held,
            task_id=resolved_task,
            timed_out=timed_out,
            attempted_result=attempted_result,
        )

    def record_reassignment(
        self,
        *,
        task_id: str,
        new_lease: DispatchLease,
        previous_holder_agent_id: str | None = None,
    ) -> Result[TaskLedger]:
        """Daemon-authored ``reassigned`` entry; increments ``attempt_no``."""
        kind = named_lease_kind(new_lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.DISPATCH_LEASE:
            return self._refuse_wrong_lease(kind.value)
        if new_lease.task_id != task_id:
            return policy_rejection(
                "dispatch_lease",
                "no Task Ledger spans two Tasks (CT-51; FR-Q57)",
                ledger_task_id=task_id,
                lease_task_id=new_lease.task_id,
            )
        ledger = self.open_for_task(task_id, owner=new_lease.owner)
        current = self._leases.get(task_id)
        previous = previous_holder_agent_id
        if previous is None and current is not None:
            previous = current.holder_agent_id
        if current is not None and current.holder_agent_id == new_lease.holder_agent_id:
            return Ok(ledger)
        recorded_at = self._stamp_recorded_at()
        if is_refusal(recorded_at):
            return recorded_at
        new_attempt = ledger.attempt_no + 1
        entry = {
            "id": f"{task_id}:reassigned:{new_attempt}",
            "kind": TaskLedgerEntryKind.REASSIGNED.value,
            "attempt_no": new_attempt,
            "authored_by": "daemon",
            "recorded_at": recorded_at.value,
            "previous_holder_agent_id": previous or "",
            "holder_agent_id": new_lease.holder_agent_id,
        }
        if not previous:
            entry.pop("previous_holder_agent_id")
        gated = self._gate_and_parse(entry, dispatch_lease_holder=None)
        if is_refusal(gated):
            return gated
        payload, _parsed = gated.value
        updated = ledger.append(payload).with_attempt_no(new_attempt)
        self._ledgers[task_id] = updated
        self._leases[task_id] = new_lease
        self._owners[task_id] = new_lease.owner
        announced = self._announce(updated, payload, task_id=task_id)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def resume_from_defer(
        self,
        *,
        task_id: str,
        dispatch_lease: DispatchLease,
    ) -> Result[TaskLedger]:
        """Retain ``dispatch_lease``; write no ``reassigned``; leave ``attempt_no``."""
        kind = named_lease_kind(dispatch_lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.DISPATCH_LEASE:
            return self._refuse_wrong_lease(kind.value)
        held = self._leases.get(task_id)
        if held is None:
            return policy_rejection(
                "dispatch_lease",
                "resume from defer retains dispatch_lease; none held for Task (CT-51; FR-Q57)",
                task_id=task_id,
            )
        if held.holder_agent_id != dispatch_lease.holder_agent_id or held.task_id != task_id:
            return policy_rejection(
                "dispatch_lease",
                "resume from defer is not a lease change; reassignment is a "
                "daemon-authored reassigned entry (CT-51; FR-Q57)",
                task_id=task_id,
            )
        ledger = self.open_for_task(task_id, owner=dispatch_lease.owner)
        return Ok(ledger)

    def record_unknown_tail(
        self,
        *,
        task_id: str,
        last_acked_id: str,
        owner: ActorId | None = None,
        timed_out: bool = False,
    ) -> Result[TaskLedger]:
        """Daemon-authored ``unknown_tail``; lease-exempt and schema-validated."""
        if not last_acked_id.strip():
            return invalid_input(
                "last_acked_id",
                "unknown_tail marks the last acknowledged id and never fabricates the tail "
                "(CT-51; FR-Q58)",
            )
        ledger = self.open_for_task(task_id, owner=owner)
        recorded_at = self._stamp_recorded_at()
        if is_refusal(recorded_at):
            return recorded_at
        entry = {
            "id": f"{task_id}:unknown_tail:{ledger.attempt_no}",
            "kind": TaskLedgerEntryKind.UNKNOWN_TAIL.value,
            "attempt_no": ledger.attempt_no,
            "authored_by": "daemon",
            "recorded_at": recorded_at.value,
            "last_acked_id": last_acked_id.strip(),
        }
        gated = self._gate_and_parse(
            entry,
            dispatch_lease_holder=None,
            timed_out=timed_out,
        )
        if is_refusal(gated):
            return gated
        payload, _parsed = gated.value
        updated = ledger.append(payload)
        self._ledgers[task_id] = updated
        announced = self._announce(updated, payload, task_id=task_id)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def record_hook_ledger_entry(
        self,
        entry: Mapping[str, object],
        *,
        task_id: str,
        hook_registry_id: str,
        owner: ActorId | None = None,
        timed_out: bool = False,
    ) -> Result[TaskLedger]:
        """Persist a ``ledger_entry`` from ``before_task_complete`` / ``review_required``."""
        ledger = self.open_for_task(task_id, owner=owner)
        inbound = dict(stamp_hook_returned_ledger_entry(entry, hook_registry_id=hook_registry_id))
        if "recorded_at" not in inbound:
            stamped = self._stamp_recorded_at()
            if is_refusal(stamped):
                return stamped
            inbound["recorded_at"] = stamped.value
        if "id" not in inbound:
            inbound["id"] = self._next_entry_id(task_id)
        if "attempt_no" not in inbound:
            inbound["attempt_no"] = ledger.attempt_no
        gated = self._gate_and_parse(
            inbound,
            dispatch_lease_holder=None,
            timed_out=timed_out,
            hook_registry_id=hook_registry_id,
        )
        if is_refusal(gated):
            return gated
        payload, record = gated.value
        if record.attempt_no != ledger.attempt_no:
            return policy_rejection(
                "attempt_no",
                "non-reassignment appends leave attempt_no unchanged (CT-51; FR-Q57)",
                current=ledger.attempt_no,
                given=record.attempt_no,
            )
        updated = ledger.append(payload)
        self._ledgers[task_id] = updated
        announced = self._announce(updated, payload, task_id=task_id)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def propose_completion(
        self,
        entry: Mapping[str, object],
        *,
        lease: object,
        task_id: str | None = None,
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
    ) -> Result[TaskCompletionAppendResult]:
        """Write a TaskCompleted append; refuse only the completion when fields are omitted."""
        inbound = dict(entry)
        inbound["kind"] = TaskLedgerEntryKind.TASK_COMPLETED.value
        appended = self.append(
            inbound,
            lease=lease,
            task_id=task_id,
            timed_out=timed_out,
            attempted_result=attempted_result,
        )
        if is_refusal(appended):
            return appended
        ledger = appended.value
        persisted = dict(ledger.entries[-1]) if ledger.entries else {}
        missing = missing_task_completed_fields(persisted.get("task_completed"))
        refusal: TypedRefusal | None = None
        if missing:
            refusal = policy_rejection(
                "task_completed",
                "a task-completion transition requires the five-field TaskCompleted "
                "append; the completion is refused and the entry is still written "
                "(CT-51; FR-Q58)",
                missing=list(missing),
                discarded=False,
            )
        return Ok(
            TaskCompletionAppendResult(
                ledger=ledger,
                entry=MappingProxyType(persisted),
                completion_admitted=not missing,
                missing_fields=missing,
                refusal=refusal,
            )
        )

    def persist_via_wire(
        self,
        envelope: WireEnvelope,
        *,
        dispatch_lease: DispatchLease,
    ) -> Result[TaskLedgerWireReceipt]:
        """Persist a ``ledger_append`` host_request; emit ``ledger.updated``."""
        if envelope.type != "ledger_append":
            return invalid_input(
                "type",
                "Task Ledger persist through the wire uses host_request ledger_append "
                "(CT-51; FR-Q57)",
                given=envelope.type,
            )
        task_id = _task_id_from_scope(envelope)
        if task_id is None:
            return invalid_input(
                "scope_path",
                "ledger_append is Task-scoped so the ledger survives the worker",
            )
        args = envelope.payload.get("args")
        if not isinstance(args, Mapping):
            return invalid_input("args", "ledger_append args must be an object")
        raw_entry = cast("Mapping[str, object]", args).get("entry")
        if not isinstance(raw_entry, Mapping):
            return invalid_input("entry", "ledger_append args.entry is the Task Ledger entry")
        inbound = dict(cast("Mapping[str, object]", raw_entry))
        if "recorded_at" in inbound:
            return refuse_worker_evidence_timestamp(attempted=inbound.get("recorded_at"))
        appended = self.append(inbound, lease=dispatch_lease, task_id=task_id)
        if is_refusal(appended):
            return appended
        ledger = appended.value
        entry = dict(ledger.entries[-1]) if ledger.entries else {}
        event = self._ledger_updated_event(
            envelope,
            task_id=task_id,
            entry=entry,
            attempt_no=ledger.attempt_no,
        )
        if is_refusal(event):
            return event
        announcement = self._announce(ledger, entry, task_id=task_id)
        if is_refusal(announcement):
            return announcement
        return Ok(
            TaskLedgerWireReceipt(
                ledger=ledger,
                entry=MappingProxyType(entry),
                event=event.value,
                announcement=announcement.value,
            )
        )

    def inspect_via_wire(self, envelope: WireEnvelope) -> Result[WireEnvelope]:
        """Serve ``inspect_ledger`` from daemon state — independent of any worker."""
        if envelope.type != WireQuery.INSPECT_LEDGER.value:
            return invalid_input(
                "type",
                "inspect_ledger reads the Task-owned Task Ledger (CT-51; FR-Q57)",
                given=envelope.type,
            )
        task_id = _task_id_from_scope(envelope)
        if task_id is None:
            requested = envelope.payload.get("task_id")
            if isinstance(requested, str) and requested.strip():
                task_id = requested.strip()
        if task_id is None:
            return invalid_input("task_id", "inspect_ledger names the Task")
        ledger = self._ledgers.get(task_id)
        if ledger is None:
            return invalid_input("task_id", "unknown Task Ledger", given=task_id)
        payload: dict[str, object] = {
            "store": TASK_LEDGER_STORE_NAME,
            "task_id": task_id,
            "attempt_no": ledger.attempt_no,
            "entries": [dict(item) for item in ledger.entries],
            "survives_worker": True,
        }
        inspected = WireEnvelope.try_create(
            v=envelope.v,
            type=WireQuery.INSPECT_LEDGER.value,
            id=f"inspect-ledger:{task_id}:{envelope.id}",
            producer_id="qma-daemon",
            scope_path=[segment.to_dict() for segment in envelope.scope_path],
            payload=payload,
            correlation_id=envelope.correlation_id,
            seq=envelope.seq,
        )
        return inspected

    def _ensure_quarantine_projection(self) -> None:
        if self._journal is not None:
            self._quarantine.bind_projection(self._journal.stores)

    def _gate_and_parse(
        self,
        inbound: Mapping[str, object],
        *,
        dispatch_lease_holder: str | None,
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
        hook_registry_id: str | None = None,
    ) -> Result[tuple[dict[str, object], TaskLedgerEntry]]:
        self._ensure_quarantine_projection()
        gate = evaluate_before_ledger_append(
            inbound,
            dispatch_lease_holder=dispatch_lease_holder,
            timed_out=timed_out,
            attempted_result=attempted_result,
            quarantine=self._quarantine,
            hook_registry_id=hook_registry_id,
            ct51_schema=True,
        )
        if gate.disposition == "quarantine":
            field = (
                "entry"
                if gate.quarantine is not None and gate.quarantine.denial_source == "schema"
                else "dispatch_lease"
            )
            return policy_rejection(
                field,
                "before_ledger_append refused a schema-invalid entry or one not "
                "authored by the holder of the named append right; the entry is "
                "quarantined and not discarded (CT-51; FR-Q58)",
                gate_reason=gate.result.reason,
                discarded=False,
                quarantine_materialized=self._quarantine.projection_materialized,
            )
        parsed = parse_task_ledger_entry(gate.entry)
        if is_refusal(parsed):
            self._quarantine.write(gate.entry, reason="schema_invalid", denial_source="schema")
            return parsed
        payload = dict(parsed.value.to_payload())
        annotations = gate.entry.get("annotations")
        if isinstance(annotations, list):
            payload["annotations"] = [str(item) for item in cast("list[object]", annotations)]
        if gate.entry.get("hook_timeout"):
            payload["hook_timeout"] = True
        return Ok((payload, parsed.value))

    def _append_validated(
        self,
        entry: Mapping[str, object],
        *,
        lease: DispatchLease,
        task_id: str,
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
    ) -> Result[TaskLedger]:
        ledger = self.open_for_task(task_id, owner=lease.owner)
        inbound = dict(entry)
        if "recorded_at" not in inbound:
            stamped = self._stamp_recorded_at()
            if is_refusal(stamped):
                return stamped
            inbound["recorded_at"] = stamped.value
        if "id" not in inbound:
            inbound["id"] = self._next_entry_id(task_id)
        if "attempt_no" not in inbound:
            inbound["attempt_no"] = ledger.attempt_no
        gated = self._gate_and_parse(
            inbound,
            dispatch_lease_holder=lease.holder_agent_id,
            timed_out=timed_out,
            attempted_result=attempted_result,
        )
        if is_refusal(gated):
            return gated
        payload, record = gated.value
        if record.kind is TaskLedgerEntryKind.REASSIGNED:
            return policy_rejection(
                "kind",
                "a change of dispatch_lease holder is recorded as a daemon-authored "
                "reassigned entry that increments attempt_no (CT-51; FR-Q57)",
            )
        if record.attempt_no != ledger.attempt_no:
            return policy_rejection(
                "attempt_no",
                "non-reassignment appends leave attempt_no unchanged; reassignment "
                "increments it via a daemon-authored reassigned entry (CT-51; FR-Q57)",
                current=ledger.attempt_no,
                given=record.attempt_no,
            )
        if not record.authored_by.daemon:
            agent_ref = record.authored_by.agent_ref
            if agent_ref != lease.holder_agent_id:
                return policy_rejection(
                    "dispatch_lease",
                    "an Agent appends only while holding that Task's dispatch_lease "
                    "(CT-51; FR-Q57)",
                    holder_agent_id=lease.holder_agent_id,
                    authored_by=agent_ref,
                )
            owner = record.authored_by.quant
            if owner is not None and owner != lease.owner:
                return policy_rejection(
                    "authored_by",
                    "authored_by carries the owning Quant ActorId (CT-51; FR-Q57)",
                    owner=lease.owner.value,
                    given=owner.value,
                )
        elif record.kind not in {
            TaskLedgerEntryKind.REASSIGNED,
            TaskLedgerEntryKind.UNKNOWN_TAIL,
            TaskLedgerEntryKind.LEDGER_ENTRY,
        }:
            return policy_rejection(
                "authored_by",
                "daemon authorship is closed to reassigned, unknown_tail, and "
                "hook-returned ledger_entry (CT-51; DEC-0308)",
                kind=record.kind.value,
            )
        updated = ledger.append(payload)
        self._ledgers[task_id] = updated
        announced = self._announce(updated, payload, task_id=task_id)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def _next_entry_id(self, task_id: str) -> str:
        seq = self._entry_seq.get(task_id, 0) + 1
        self._entry_seq[task_id] = seq
        return f"{task_id}:entry:{seq}"

    def _stamp_recorded_at(self) -> Result[int]:
        if self._journal is not None:
            stamps = self._journal.stamp_durable()
            if is_refusal(stamps):
                return stamps
            return Ok(stamps.value.recorded_at)
        wall = self._clock.wall_now()
        if is_refusal(wall):
            return wall
        return Ok(wall.value.value_ns)

    def _announce(
        self,
        ledger: TaskLedger,
        entry: Mapping[str, object],
        *,
        task_id: str,
    ) -> Result[AnnouncementOutcome | None]:
        _ = ledger
        if self._journal is None:
            return Ok(None)
        addressed = content_address(dict(entry))
        if is_refusal(addressed):
            return addressed
        declared = self._journal.declare_store(TASK_LEDGER_STORE_NAME)
        if is_refusal(declared):
            return declared
        announced = self._journal.announce_evidence_append(
            TASK_LEDGER_STORE_NAME,
            addressed.value,
            extra_payload={"task_id": task_id},
        )
        if is_refusal(announced):
            return announced
        return Ok(announced.value)

    def _ledger_updated_event(
        self,
        request: WireEnvelope,
        *,
        task_id: str,
        entry: Mapping[str, object],
        attempt_no: int,
    ) -> Result[WireEnvelope]:
        return WireEnvelope.try_create(
            v=request.v or _WIRE_PROTOCOL,
            type=WireEvent.LEDGER_UPDATED.value,
            id=f"ledger-updated:{task_id}:{entry.get('id', request.id)}",
            producer_id="qma-daemon",
            scope_path=[segment.to_dict() for segment in request.scope_path],
            payload={
                "store": TASK_LEDGER_STORE_NAME,
                "task_id": task_id,
                "attempt_no": attempt_no,
                "entry": dict(entry),
                "survives_worker": True,
            },
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _refuse_wrong_lease(kind: LeaseKind) -> TypedRefusal:
        return policy_rejection(
            "lease",
            "Task Ledger append rights follow dispatch_lease, distinct from "
            "environment_lease and quant_ledger_lease (CT-51; FR-Q57)",
            given=kind.value,
            required=LeaseKind.DISPATCH_LEASE.value,
        )
