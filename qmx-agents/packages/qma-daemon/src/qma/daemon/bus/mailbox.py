"""Durable Quant Mailbox projection over journal ``message.*`` events (CT-48).

Each Quant owns one Mailbox in the daemon store — no external relay. Delivery is
at-least-once with idempotent msg-id dedup and a per-actor ack cursor. A handoff
becomes work only by writing a Task. A missing recipient resolves to
``dead_letter``. GAP-0071 and GAP-0079 stay Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.ontology import ActorId, Agent, Quant, Task
from qma.core.ontology.wake_policy import (
    QUANT_WRITE_COMMAND,
    WakePolicy,
    parse_wake_policy,
    refuse_model_wake_policy_write,
    source_may_write_wake_policy,
)
from qma.core.plugins.hooks import HookResult
from qma.core.ports.mailbox import (
    GAP_0071_LEAD_MAILBOX_CATCH_ALL,
    GAP_0079_EXTERNAL_TRANSPORT,
    Envelope,
    parse_envelope,
    refuse_external_agent_transport,
    refuse_lead_mailbox_catch_all,
)
from qma.core.vocabulary.enums import DeliveryState, HookResultDecision, HookVerb, MessageKind
from qma.daemon.hooks.registry import HookRegistry, event_names_for_verb
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.fold_contracts import v1_fold_contract
from qma.daemon.journal.variables import registry_key
from qma.daemon.ledgers.task import TaskLedgerStore
from qma.daemon.scheduler.wake import (
    WakeDecision,
    WakeExemption,
    civil_window_id,
    evaluate_delivery_wake,
    resolve_iana_zone,
    routine_fire_suppressed_by_quiet_hours,
    running_agent_paused_by_quiet_hours,
)
from qma.wire.principals import authorize_wire_command
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DELIVERY_RETENTION_KEYS",
    "GAP_0071_LEAD_MAILBOX_CATCH_ALL",
    "GAP_0079_EXTERNAL_TRANSPORT",
    "MAILBOX_FOLD_ID",
    "MAILBOX_SOURCE_STREAM",
    "MAILBOX_STORE_NAME",
    "NO_EXTERNAL_RELAY",
    "QUANT_WRITE_COMMAND",
    "DeliveryRecord",
    "Mailbox",
    "MailboxStore",
]


MAILBOX_STORE_NAME: Final[str] = "mailboxes_and_delivery_state"
MAILBOX_FOLD_ID: Final[str] = "mailbox_delivery_state"
MAILBOX_SOURCE_STREAM: Final[str] = "message.*"
NO_EXTERNAL_RELAY: Final[bool] = True

DELIVERY_RETENTION_KEYS: Final[tuple[str, ...]] = (
    registry_key("mailbox.delivery_retention_window"),
    registry_key("mailbox.delivery_trim_event_count"),
    registry_key("mailbox.delivery_trim_disk_bytes"),
)

_EXTERNAL_RELAY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "relay",
        "external_relay",
        "external_transport",
        "signing_protocol",
    }
)
_LEAD_CATCH_ALL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "catch_all_lead",
        "lead_mailbox",
        "lead_catch_all",
    }
)
_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)
_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000
_MESSAGE_SENT_EVENT: Final[str] = "message.sent"
_MESSAGE_DELIVERED_EVENT: Final[str] = "message.delivered"
_MESSAGE_ACKED_EVENT: Final[str] = "message.acked"
_MESSAGE_WOKE_EVENT: Final[str] = "message.woke"
_KEEP: Final[object] = object()
_TERMINAL_DELIVERY: Final[frozenset[DeliveryState]] = frozenset(
    {
        DeliveryState.DELIVERED,
        DeliveryState.WOKE,
        DeliveryState.DEFERRED,
        DeliveryState.DEAD_LETTER,
    }
)


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(
        boot_epoch_id="mailbox",
        wall_instants=walls,
        monotonic_ns=monos,
    )


def _truthy(value: object) -> bool:
    return value not in (None, False, 0, "", ())


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """One delivery-projection row over a mailbox Envelope."""

    envelope: Envelope
    state: DeliveryState
    journal_seq: int | None = None
    acked: bool = False
    answered: bool = False
    wake_at: int | None = None

    def with_state(
        self,
        state: DeliveryState,
        *,
        journal_seq: int | None = None,
        acked: bool | None = None,
        answered: bool | None = None,
        envelope: Envelope | None = None,
        wake_at: object = _KEEP,
    ) -> DeliveryRecord:
        resolved_wake = self.wake_at if wake_at is _KEEP else wake_at
        return DeliveryRecord(
            envelope=self.envelope if envelope is None else envelope,
            state=state,
            journal_seq=self.journal_seq if journal_seq is None else journal_seq,
            acked=self.acked if acked is None else acked,
            answered=self.answered if answered is None else answered,
            wake_at=(
                resolved_wake if isinstance(resolved_wake, int) or resolved_wake is None else None
            ),
        )

    @property
    def is_work(self) -> bool:
        """A message is never work; only a written Task is."""
        return False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "envelope": dict(self.envelope.to_payload()),
                "delivery_state": self.state.value,
                "journal_seq": self.journal_seq,
                "acked": self.acked,
                "answered": self.answered,
                "wake_at": self.wake_at,
                "is_work": False,
                "external_relay": False,
            }
        )


@dataclass(frozen=True, slots=True)
class Mailbox:
    """One Quant-owned durable Mailbox — a bounded delivery projection."""

    owner: ActorId
    records: tuple[DeliveryRecord, ...] = ()
    ack_cursor: str | None = None

    def append(self, record: DeliveryRecord) -> Mailbox:
        return Mailbox(
            owner=self.owner, records=(*self.records, record), ack_cursor=self.ack_cursor
        )

    def replace(self, record: DeliveryRecord) -> Mailbox:
        updated = tuple(
            record if existing.envelope.msg_id == record.envelope.msg_id else existing
            for existing in self.records
        )
        return Mailbox(owner=self.owner, records=updated, ack_cursor=self.ack_cursor)

    def with_ack_cursor(self, msg_id: str) -> Mailbox:
        return Mailbox(owner=self.owner, records=self.records, ack_cursor=msg_id)

    def without_records(self, drop: frozenset[str]) -> Mailbox:
        kept = tuple(item for item in self.records if item.envelope.msg_id not in drop)
        return Mailbox(owner=self.owner, records=kept, ack_cursor=self.ack_cursor)

    def record_for(self, msg_id: str) -> DeliveryRecord | None:
        for item in self.records:
            if item.envelope.msg_id == msg_id:
                return item
        return None

    def to_payload(self) -> Mapping[str, object]:
        fold = v1_fold_contract(MAILBOX_FOLD_ID)
        return MappingProxyType(
            {
                "store": MAILBOX_STORE_NAME,
                "fold_id": MAILBOX_FOLD_ID,
                "source_stream": MAILBOX_SOURCE_STREAM if fold is None else fold.source_stream,
                "owner": self.owner.value,
                "ack_cursor": self.ack_cursor,
                "external_relay": False,
                "retention": list(DELIVERY_RETENTION_KEYS),
                "entries": [dict(item.to_payload()) for item in self.records],
            }
        )


@dataclass
class MailboxStore:
    """Daemon-owned Mailbox projection — one durable inbox per Quant."""

    _mailboxes: dict[str, Mailbox] = field(default_factory=dict[str, Mailbox])
    _quants: dict[str, Quant] = field(default_factory=dict[str, Quant])
    _by_msg_id: dict[str, DeliveryRecord] = field(default_factory=dict[str, DeliveryRecord])
    _handoff_tasks: dict[str, Task] = field(default_factory=dict[str, Task])
    _clock: Clock = field(default_factory=_default_clock)
    _journal: AuthoritativeJournal | None = None
    _hooks: HookRegistry = field(default_factory=HookRegistry)
    _task_ledgers: TaskLedgerStore | None = None
    _journal_rows: int = 0
    _wake_counts: dict[str, dict[str, int]] = field(default_factory=dict[str, dict[str, int]])
    _running_agents: dict[str, set[str]] = field(default_factory=dict[str, set[str]])

    @property
    def store_name(self) -> str:
        return MAILBOX_STORE_NAME

    @property
    def external_relay(self) -> bool:
        return False

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    def mailbox_for(self, owner: Quant | ActorId | str) -> Mailbox | None:
        return self._mailboxes.get(self._owner_key(owner))

    def quant_for(self, owner: Quant | ActorId | str) -> Quant | None:
        return self._quants.get(self._owner_key(owner))

    def record_for(self, msg_id: str) -> DeliveryRecord | None:
        return self._by_msg_id.get(msg_id)

    def task_for_handoff(self, msg_id: str) -> Task | None:
        return self._handoff_tasks.get(msg_id)

    def handoff_is_work(self, msg_id: str) -> bool:
        return msg_id in self._handoff_tasks

    def journal_event_count(self) -> int:
        return self._journal_rows

    def open_for_quant(self, quant: Quant) -> Result[Mailbox]:
        """Create the one durable Mailbox for this Quant — no external relay."""
        key = quant.actor_id.value
        stored = self._quants.get(key)
        if stored is not None:
            if (
                quant.wake_policy is not None
                and stored.wake_policy is not None
                and quant.wake_policy != stored.wake_policy
            ):
                return refuse_model_wake_policy_write(source="mailbox.open_for_quant")
            if quant.wake_policy is not None and stored.wake_policy is None:
                return refuse_model_wake_policy_write(source="mailbox.open_for_quant")
            quant = quant.with_wake_policy(stored.wake_policy)
        self._quants[key] = quant
        existing = self._mailboxes.get(key)
        if existing is not None:
            return Ok(existing)
        mailbox = Mailbox(owner=quant.actor_id)
        self._mailboxes[key] = mailbox
        declared = self._declare_projection()
        if is_refusal(declared):
            return declared
        return Ok(mailbox)

    def open_for_agent(self, agent: Agent) -> Result[Mailbox]:
        """Agents and Subagents have no Mailbox and are never a ``to`` address."""
        return policy_rejection(
            "mailbox",
            "an Agent has no Mailbox and is never a to address (DEC-0306; CT-48; FR-Q60)",
            agent_id=agent.id,
        )

    def send(
        self,
        envelope: Mapping[str, object] | Envelope,
        *,
        external_relay: bool = False,
        catch_all_lead: bool = False,
    ) -> Result[DeliveryRecord]:
        """Accept one Envelope into the daemon Mailbox projection."""
        inbound = dict(envelope.to_payload() if isinstance(envelope, Envelope) else envelope)
        relay = self._refuse_external_relay(inbound, requested=external_relay)
        if is_refusal(relay):
            return relay
        lead = self._refuse_lead_catch_all(inbound, requested=catch_all_lead)
        if is_refusal(lead):
            return lead
        stamped = self._stamp_inbound(inbound)
        if is_refusal(stamped):
            return stamped
        parsed = parse_envelope(stamped.value)
        if is_refusal(parsed):
            return parsed
        envelope_record = parsed.value

        existing = self._by_msg_id.get(envelope_record.msg_id)
        if existing is not None:
            return Ok(existing)

        gated = self._before_message_send(envelope_record)
        if is_refusal(gated):
            return gated

        recipient = self._recipient_mailbox(envelope_record.to_actor)
        state = DeliveryState.DEAD_LETTER if recipient is None else DeliveryState.QUEUED
        journaled = self._journal_event(
            _MESSAGE_SENT_EVENT,
            envelope_record,
            state=state,
        )
        if is_refusal(journaled):
            return journaled
        seq = journaled.value
        record = DeliveryRecord(envelope=envelope_record, state=state, journal_seq=seq)
        self._index(record)
        if recipient is not None:
            self._mailboxes[recipient.owner.value] = recipient.append(record)
        self._after_message_send(envelope_record, record)
        return Ok(record)

    def write_wake_policy(
        self,
        owner: Quant | ActorId | str,
        policy: Mapping[str, object] | WakePolicy,
        *,
        principal_class: object,
        source: object = "operator",
    ) -> Result[Quant]:
        """Persist an operator-authored WakePolicy on the Quant record.

        Record-homed: never a ``variable.set``. No model authors, alters, or
        overrides the policy; a wake cap is not a write of the policy.
        """
        if not source_may_write_wake_policy(source):
            return refuse_model_wake_policy_write(source=source)
        authorized = authorize_wire_command(QUANT_WRITE_COMMAND, principal_class)
        if is_refusal(authorized):
            return authorized
        parsed = parse_wake_policy(policy)
        if is_refusal(parsed):
            return parsed
        authored = parsed.value
        if authored.quiet_hours is not None:
            zone = resolve_iana_zone(authored.quiet_hours.iana_zone)
            if is_refusal(zone):
                return zone
        key = self._owner_key(owner)
        quant = self._quants.get(key)
        if quant is None:
            return invalid_input("mailbox", "Quant has no Mailbox", given=key)
        updated = quant.with_wake_policy(authored)
        self._quants[key] = updated
        return Ok(updated)

    def deliver(self, msg_id: str) -> Result[DeliveryRecord]:
        """At-least-once delivery: idempotent on msg-id, never silent-drop.

        Evaluates the Quant ``WakePolicy`` at delivery time. Quiet hours
        suppress wakes only: the Envelope is still delivered and may be acked.
        """
        current = self._by_msg_id.get(msg_id)
        if current is None:
            return invalid_input("msg_id", "unknown mailbox Envelope", given=msg_id)
        if current.state in _TERMINAL_DELIVERY:
            return Ok(current)
        decision = self._evaluate_record(current)
        if is_refusal(decision):
            return decision
        verdict = decision.value
        journaled = self._journal_event(
            _MESSAGE_DELIVERED_EVENT,
            current.envelope,
            state=verdict.state,
        )
        if is_refusal(journaled):
            return journaled
        updated = current.with_state(
            verdict.state,
            journal_seq=journaled.value,
            wake_at=verdict.wake_at,
        )
        self._replace(updated)
        if verdict.wake:
            counted = self._count_wake(current.envelope.to_actor)
            if is_refusal(counted):
                return counted
        return Ok(updated)

    def fire_due_wakes(self, *, at: Instant | None = None) -> Result[tuple[DeliveryRecord, ...]]:
        """Fire deferred wakes whose ``wake_at`` has been reached."""
        when = self._evaluation_instant(at)
        if is_refusal(when):
            return when
        now = when.value
        fired: list[DeliveryRecord] = []
        for record in tuple(self._by_msg_id.values()):
            if record.state is not DeliveryState.DEFERRED:
                continue
            if record.wake_at is None or record.wake_at > now.value_ns:
                continue
            decision = self._evaluate_record(record, at=now)
            if is_refusal(decision):
                return decision
            verdict = decision.value
            event = _MESSAGE_WOKE_EVENT if verdict.wake else _MESSAGE_DELIVERED_EVENT
            journaled = self._journal_event(event, record.envelope, state=verdict.state)
            if is_refusal(journaled):
                return journaled
            updated = record.with_state(
                verdict.state,
                journal_seq=journaled.value,
                wake_at=verdict.wake_at,
            )
            self._replace(updated)
            if verdict.wake:
                counted = self._count_wake(record.envelope.to_actor, at=now)
                if is_refusal(counted):
                    return counted
            fired.append(updated)
        return Ok(tuple(fired))

    def mark_agent_running(self, owner: Quant | ActorId | str, agent_id: str) -> None:
        """Record that an Agent of this Quant is already running."""
        key = self._owner_key(owner)
        running = self._running_agents.setdefault(key, set())
        running.add(agent_id)

    def mark_agent_stopped(self, owner: Quant | ActorId | str, agent_id: str) -> None:
        """Clear a previously running Agent of this Quant."""
        key = self._owner_key(owner)
        running = self._running_agents.get(key)
        if running is not None:
            running.discard(agent_id)

    def pause_running_agent(
        self,
        owner: Quant | ActorId | str,
        *,
        at: Instant | None = None,
    ) -> Result[bool]:
        """Quiet hours never pause a run already under way (CT-48; FR-Q61)."""
        key = self._owner_key(owner)
        quant = self._quants.get(key)
        policy = None if quant is None else quant.wake_policy
        when = self._evaluation_instant(at)
        if is_refusal(when):
            return when
        paused = running_agent_paused_by_quiet_hours(policy, at=when.value)
        if is_refusal(paused):
            return paused
        return Ok(False)

    def evaluate_routine_fire(
        self,
        owner: Quant | ActorId | str,
        *,
        at: Instant | None = None,
    ) -> Result[bool]:
        """True when the Routine may fire. Quiet hours never suppress it."""
        key = self._owner_key(owner)
        quant = self._quants.get(key)
        policy = None if quant is None else quant.wake_policy
        when = self._evaluation_instant(at)
        if is_refusal(when):
            return when
        suppressed = routine_fire_suppressed_by_quiet_hours(policy, at=when.value)
        if is_refusal(suppressed):
            return suppressed
        return Ok(not suppressed.value)

    def ack(self, owner: Quant | ActorId | str, msg_id: str) -> Result[Mailbox]:
        """Advance the per-actor ack cursor. Idempotent on the same msg-id."""
        key = self._owner_key(owner)
        mailbox = self._mailboxes.get(key)
        if mailbox is None:
            return invalid_input("mailbox", "Quant has no Mailbox", given=key)
        record = mailbox.record_for(msg_id)
        if record is None:
            return invalid_input(
                "msg_id",
                "ack cursor names an Envelope in this actor's Mailbox (CT-48; FR-Q60)",
                given=msg_id,
            )
        if mailbox.ack_cursor == msg_id and record.acked:
            return Ok(mailbox)
        journaled = self._journal_event(
            _MESSAGE_ACKED_EVENT,
            record.envelope,
            state=record.state,
        )
        if is_refusal(journaled):
            return journaled
        acked = record.with_state(record.state, acked=True, journal_seq=journaled.value)
        self._replace(acked)
        updated = self._mailboxes[key].with_ack_cursor(msg_id)
        self._mailboxes[key] = updated
        return Ok(updated)

    def answer_approval(self, msg_id: str) -> Result[DeliveryRecord]:
        """Mark an ``approval_request`` answered so trim may later drop it."""
        current = self._by_msg_id.get(msg_id)
        if current is None:
            return invalid_input("msg_id", "unknown mailbox Envelope", given=msg_id)
        if current.envelope.kind is not MessageKind.APPROVAL_REQUEST:
            return policy_rejection(
                "kind",
                "approval_request is the single human-approval channel every gate "
                "raises (CT-48; DEC-0319; FR-Q60)",
                given=current.envelope.kind.value,
            )
        updated = current.with_state(current.state, answered=True)
        self._replace(updated)
        return Ok(updated)

    def realize_handoff_as_task(
        self,
        msg_id: str,
        *,
        task_id: str,
        mission_id: str | None = None,
    ) -> Result[Task]:
        """A handoff becomes work only by writing a Task (CT-48; FR-Q60)."""
        current = self._by_msg_id.get(msg_id)
        if current is None:
            return invalid_input("msg_id", "unknown mailbox Envelope", given=msg_id)
        if current.envelope.kind is not MessageKind.HANDOFF:
            return policy_rejection(
                "kind",
                "a message may request work but can never be the work; only a "
                "handoff realized by writing a Task becomes work (CT-48; DEC-0319; FR-Q60)",
                given=current.envelope.kind.value,
            )
        existing = self._handoff_tasks.get(msg_id)
        if existing is not None:
            return Ok(existing)
        if not task_id.strip():
            return invalid_input("task_id", "writing a Task requires a Task id")
        resolved_mission = mission_id or current.envelope.mission_ref
        if resolved_mission is None or resolved_mission.strip() == "":
            return invalid_input(
                "mission_id",
                "writing a Task from a handoff requires a Mission (CT-48; FR-Q60)",
            )
        task = Task(
            id=task_id.strip(),
            mission_id=resolved_mission.strip(),
            owner=current.envelope.to_actor,
        )
        self._handoff_tasks[msg_id] = task
        updated_envelope = current.envelope.with_task_ref(task.id)
        self._replace(current.with_state(current.state, envelope=updated_envelope))
        if self._task_ledgers is not None:
            self._task_ledgers.open_for_task(task.id, owner=task.owner)
        return Ok(task)

    def trim_delivery_projection(self) -> Mapping[str, object]:
        """Trim acked / dead_letter projection rows. Never deletes a journal record.

        Unacked Envelopes and unanswered ``approval_request`` rows stay. The trim
        window value is Deferred GAP-0089; this path cites the registry keys only.
        """
        drop: set[str] = set()
        for msg_id, record in self._by_msg_id.items():
            if record.state is DeliveryState.DEAD_LETTER:
                drop.add(msg_id)
                continue
            if record.state is DeliveryState.DEFERRED:
                continue
            if not record.acked:
                continue
            if record.envelope.kind is MessageKind.APPROVAL_REQUEST and not record.answered:
                continue
            drop.add(msg_id)
        frozen = frozenset(drop)
        for key, mailbox in list(self._mailboxes.items()):
            self._mailboxes[key] = mailbox.without_records(frozen)
        for msg_id in frozen:
            self._by_msg_id.pop(msg_id, None)
        return MappingProxyType(
            {
                "trimmed_projection_entries": len(frozen),
                "journal_records_deleted": False,
                "journal_event_count": self._journal_rows,
                "retention": list(DELIVERY_RETENTION_KEYS),
                "gap_0089": "deferred",
            }
        )

    def _evaluation_instant(self, at: Instant | None = None) -> Result[Instant]:
        if at is not None:
            return Ok(at)
        return self._clock.wall_now()

    def _is_approval_request_reply(self, envelope: Envelope) -> bool:
        if envelope.kind is not MessageKind.REPLY or envelope.reply_to_ref is None:
            return False
        parent = self._by_msg_id.get(envelope.reply_to_ref)
        if parent is None:
            return False
        return parent.envelope.kind is MessageKind.APPROVAL_REQUEST

    def _evaluate_record(
        self,
        record: DeliveryRecord,
        *,
        at: Instant | None = None,
    ) -> Result[WakeDecision]:
        quant = self._quants.get(record.envelope.to_actor.value)
        policy = None if quant is None else quant.wake_policy
        exemption: WakeExemption | None = None
        if self._is_approval_request_reply(record.envelope):
            exemption = "approval_request_reply"
        if policy is None:
            dummy = Instant(value_ns=0) if at is None else at
            return evaluate_delivery_wake(
                None,
                kind=record.envelope.kind,
                at=dummy,
                wakes_in_window=0,
                exemption=exemption,
            )
        when = self._evaluation_instant(at)
        if is_refusal(when):
            return when
        window = civil_window_id(policy, when.value)
        if is_refusal(window):
            return window
        wakes = self._wake_counts.get(record.envelope.to_actor.value, {}).get(window.value, 0)
        return evaluate_delivery_wake(
            policy,
            kind=record.envelope.kind,
            at=when.value,
            wakes_in_window=wakes,
            exemption=exemption,
        )

    def _count_wake(self, owner: ActorId, *, at: Instant | None = None) -> Result[None]:
        quant = self._quants.get(owner.value)
        policy = None if quant is None else quant.wake_policy
        when = self._evaluation_instant(at)
        if is_refusal(when):
            return when
        window = civil_window_id(policy, when.value)
        if is_refusal(window):
            return window
        per_owner = self._wake_counts.setdefault(owner.value, {})
        per_owner[window.value] = per_owner.get(window.value, 0) + 1
        return Ok(None)

    def _owner_key(self, owner: Quant | ActorId | str) -> str:
        if isinstance(owner, Quant):
            return owner.actor_id.value
        if isinstance(owner, ActorId):
            return owner.value
        return owner

    def _recipient_mailbox(self, actor: ActorId) -> Mailbox | None:
        quant = self._quants.get(actor.value)
        if quant is None or quant.retired:
            return None
        return self._mailboxes.get(actor.value)

    def _stamp_inbound(self, inbound: dict[str, object]) -> Result[Mapping[str, object]]:
        if "created_at" not in inbound:
            stamped = self._stamp_created_at()
            if is_refusal(stamped):
                return stamped
            inbound["created_at"] = stamped.value
        if "priority" not in inbound:
            inbound["priority"] = 0
        if "artifact_refs" not in inbound:
            inbound["artifact_refs"] = []
        return Ok(MappingProxyType(inbound))

    def _stamp_created_at(self) -> Result[int]:
        if self._journal is not None:
            stamps = self._journal.stamp_durable()
            if is_refusal(stamps):
                return stamps
            return Ok(stamps.value.recorded_at)
        wall = self._clock.wall_now()
        if is_refusal(wall):
            return wall
        return Ok(wall.value.value_ns)

    def _refuse_external_relay(
        self,
        inbound: Mapping[str, object],
        *,
        requested: bool,
    ) -> Result[None]:
        if requested:
            return refuse_external_agent_transport(requested=True)
        for key in _EXTERNAL_RELAY_KEYS:
            if key in inbound and _truthy(inbound.get(key)):
                return refuse_external_agent_transport(field=key)
        return Ok(None)

    def _refuse_lead_catch_all(
        self,
        inbound: Mapping[str, object],
        *,
        requested: bool,
    ) -> Result[None]:
        if requested:
            return refuse_lead_mailbox_catch_all(requested=True)
        for key in _LEAD_CATCH_ALL_KEYS:
            if key in inbound and _truthy(inbound.get(key)):
                return refuse_lead_mailbox_catch_all(field=key)
        return Ok(None)

    def _before_message_send(self, envelope: Envelope) -> Result[HookResult]:
        before, _after = event_names_for_verb(HookVerb.MESSAGE_SEND)
        result = self._hooks.dispatch(before, payload=dict(envelope.to_payload()))
        if is_refusal(result):
            return result
        gate = result.value
        if gate.decision in _BLOCKING_BEFORE:
            return policy_rejection(
                before,
                f"{before} resolved to {gate.decision.value}; send not accepted "
                "(CT-48; AD-10; FR-Q60)",
                given=gate.reason or gate.decision.value,
            )
        return Ok(gate)

    def _after_message_send(self, envelope: Envelope, record: DeliveryRecord) -> None:
        _before, after = event_names_for_verb(HookVerb.MESSAGE_SEND)
        payload = dict(envelope.to_payload())
        payload["delivery_state"] = record.state.value
        _ = self._hooks.dispatch(after, payload=payload)

    def _declare_projection(self) -> Result[None]:
        if self._journal is None:
            return Ok(None)
        declared = self._journal.declare_store(MAILBOX_STORE_NAME)
        if is_refusal(declared):
            return declared
        folded = self._journal.register_fold(MAILBOX_FOLD_ID)
        if is_refusal(folded):
            return folded
        return Ok(None)

    def _journal_event(
        self,
        event: str,
        envelope: Envelope,
        *,
        state: DeliveryState,
    ) -> Result[int | None]:
        if self._journal is None:
            self._journal_rows += 1
            return Ok(None)
        declared = self._declare_projection()
        if is_refusal(declared):
            return declared
        payload: dict[str, object] = {
            "envelope": dict(envelope.to_payload()),
            "delivery_state": state.value,
            "store": MAILBOX_STORE_NAME,
            "external_relay": False,
        }
        appended = self._journal.append_event(
            event,
            scope_path=self._scope_path(envelope.to_actor, envelope.from_actor),
            payload=payload,
        )
        if is_refusal(appended):
            return appended
        self._journal_rows += 1
        return Ok(appended.value.record.journal_seq)

    def _scope_path(
        self,
        to_actor: ActorId,
        from_actor: ActorId,
    ) -> list[dict[str, str]]:
        quant = self._quants.get(to_actor.value) or self._quants.get(from_actor.value)
        if quant is None:
            return []
        return [
            {"kind": "desk", "id": quant.desk.value},
            {"kind": "quant", "id": quant.quant_slug},
        ]

    def _index(self, record: DeliveryRecord) -> None:
        self._by_msg_id[record.envelope.msg_id] = record

    def _replace(self, record: DeliveryRecord) -> None:
        self._by_msg_id[record.envelope.msg_id] = record
        key = record.envelope.to_actor.value
        mailbox = self._mailboxes.get(key)
        if mailbox is not None and mailbox.record_for(record.envelope.msg_id) is not None:
            self._mailboxes[key] = mailbox.replace(record)
