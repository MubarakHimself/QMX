"""Quant Ledger store under ``quant_ledger_lease`` (AD-9; FR-Q59).

Opened only while the Quant carries its desk's lead flag. The daemon grants
the ``quant_ledger_lease`` to at most one Agent of that Quant at a time.
A lead-flag move retains the existing ledger and does not open one for the
successor.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.content import content_address
from qma.core.ontology import ActorId, Agent, DeskSlug, Quant
from qma.core.plugins.hooks import HookResult
from qma.core.ports.ledgers import (
    QuantLedgerEntry,
    QuantLedgerLease,
    named_lease_kind,
    parse_quant_ledger_entry,
)
from qma.core.vocabulary.enums import LeaseKind, QuantLedgerEntryKind
from qma.daemon.hooks.ledger_gate import (
    LedgerQuarantineStream,
    evaluate_before_ledger_append,
)
from qma.daemon.journal.authoritative import AnnouncementOutcome, AuthoritativeJournal
from qma.daemon.ledgers.announcements import (
    LedgerAppendAnnouncement,
    agent_ref_from_authored_by,
)
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "QUANT_LEDGER_DECLARED_KINDS",
    "QUANT_LEDGER_STORE_NAME",
    "LeadFlagMove",
    "QuantLedger",
    "QuantLedgerStore",
]


QUANT_LEDGER_STORE_NAME: Final[str] = "quant_ledger"
QUANT_LEDGER_DECLARED_KINDS: Final[frozenset[str]] = frozenset(
    member.value for member in QuantLedgerEntryKind
)
_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(
        boot_epoch_id="quant-ledger",
        wall_instants=walls,
        monotonic_ns=monos,
    )


def _quant_with_lead(quant: Quant, *, lead: bool) -> Quant:
    return Quant(
        actor_id=quant.actor_id,
        desk=quant.desk,
        quant_slug=quant.quant_slug,
        role=quant.role,
        name=quant.name,
        lead=lead,
        retired=quant.retired,
    )


def _ledger_ref_for(quant: Quant) -> str:
    return f"quant-ledger:{quant.actor_id.value}"


@dataclass(frozen=True, slots=True)
class QuantLedger:
    """Desk-lead Quant's own work ledger with the declared entry schema."""

    owner: Quant
    ledger_ref: str
    entries: tuple[Mapping[str, object], ...] = ()

    @property
    def desk(self) -> DeskSlug:
        return self.owner.desk

    def append(self, entry: Mapping[str, object]) -> QuantLedger:
        return QuantLedger(
            owner=self.owner,
            ledger_ref=self.ledger_ref,
            entries=(*self.entries, dict(entry)),
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "store": QUANT_LEDGER_STORE_NAME,
                "owner": self.owner.actor_id.value,
                "desk": self.owner.desk.value,
                "quant_slug": self.owner.quant_slug,
                "ledger_ref": self.ledger_ref,
                "declared_kinds": sorted(QUANT_LEDGER_DECLARED_KINDS),
                "entries": [dict(item) for item in self.entries],
            }
        )


@dataclass(frozen=True, slots=True)
class LeadFlagMove:
    """Outcome of moving a desk lead flag — existing ledger is retained."""

    previous: Quant
    successor: Quant
    retained_ledger: QuantLedger | None
    successor_ledger_opened: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "previous": {
                "actor_id": self.previous.actor_id.value,
                "lead": self.previous.lead,
            },
            "successor": {
                "actor_id": self.successor.actor_id.value,
                "lead": self.successor.lead,
            },
            "successor_ledger_opened": self.successor_ledger_opened,
        }
        if self.retained_ledger is not None:
            payload["retained_ledger_ref"] = self.retained_ledger.ledger_ref
        return MappingProxyType(payload)


@dataclass
class QuantLedgerStore:
    """Independent Quant Ledger store — one ledger per Quant that has been lead."""

    _ledgers: dict[str, QuantLedger] = field(default_factory=dict[str, QuantLedger])
    _leases: dict[str, QuantLedgerLease] = field(default_factory=dict[str, QuantLedgerLease])
    _quants: dict[str, Quant] = field(default_factory=dict[str, Quant])
    _clock: Clock = field(default_factory=_default_clock)
    _journal: AuthoritativeJournal | None = None
    _entry_seq: dict[str, int] = field(default_factory=dict[str, int])
    _quarantine: LedgerQuarantineStream = field(default_factory=LedgerQuarantineStream)
    _announcements: list[LedgerAppendAnnouncement] = field(
        default_factory=list[LedgerAppendAnnouncement]
    )
    _announce_seq: int = 0

    def __post_init__(self) -> None:
        if self._journal is not None:
            self._quarantine.bind_projection(self._journal.stores)

    @property
    def quarantine(self) -> LedgerQuarantineStream:
        return self._quarantine

    def quants(self) -> tuple[Quant, ...]:
        return tuple(self._quants.values())

    def announcements(self) -> tuple[LedgerAppendAnnouncement, ...]:
        return tuple(self._announcements)

    def _owner_key(self, owner: Quant | ActorId | str) -> str:
        if isinstance(owner, Quant):
            return owner.actor_id.value
        if isinstance(owner, ActorId):
            return owner.value
        return owner

    def get(self, owner: Quant | ActorId | str) -> QuantLedger | None:
        return self._ledgers.get(self._owner_key(owner))

    def lease_for(self, owner: Quant | ActorId | str) -> QuantLedgerLease | None:
        return self._leases.get(self._owner_key(owner))

    def open_for_quant(self, quant: Quant) -> Result[QuantLedger]:
        """Create the Quant Ledger only while the Quant carries the lead flag."""
        key = quant.actor_id.value
        self._quants[key] = quant
        existing = self._ledgers.get(key)
        if existing is not None:
            updated = QuantLedger(
                owner=quant,
                ledger_ref=existing.ledger_ref,
                entries=existing.entries,
            )
            self._ledgers[key] = updated
            return Ok(updated)
        if not quant.lead:
            return policy_rejection(
                "lead_flag",
                "no Quant Ledger opens without the desk lead flag; a Quant that "
                "has never held the lead flag has none (AD-9; DEC-0349; FR-Q59)",
                actor_id=key,
            )
        ledger = QuantLedger(owner=quant, ledger_ref=_ledger_ref_for(quant))
        self._ledgers[key] = ledger
        return Ok(ledger)

    def grant(
        self,
        lease: QuantLedgerLease,
        *,
        agent: Agent | None = None,
    ) -> Result[QuantLedgerLease]:
        """Grant ``quant_ledger_lease`` to at most one Agent of this Quant."""
        kind = named_lease_kind(lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.QUANT_LEDGER_LEASE:
            return self._refuse_wrong_lease(kind.value)
        key = lease.owner.value
        if key not in self._ledgers:
            return policy_rejection(
                "quant_ledger",
                "Quant Ledger append rights require an opened Quant Ledger (AD-9; FR-Q59)",
                owner=key,
            )
        if agent is not None:
            if agent.owner != lease.owner:
                return policy_rejection(
                    "quant_ledger_lease",
                    "quant_ledger_lease is granted only to an Agent of the owning "
                    "Quant (AD-9; FR-Q59)",
                    owner=key,
                    agent_owner=agent.owner.value,
                )
            if agent.id != lease.holder_agent_id:
                return invalid_input(
                    "holder_agent_id",
                    "quant_ledger_lease holder must match the Agent id",
                    holder_agent_id=lease.holder_agent_id,
                    agent_id=agent.id,
                )
        # Exclusive: at most one Agent of this Quant holds the lease at a time.
        self._leases[key] = lease
        return Ok(lease)

    def append(
        self,
        entry: Mapping[str, object],
        *,
        lease: object,
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
    ) -> Result[QuantLedger]:
        """Persist one Quant Ledger entry through ``before_ledger_append``."""
        kind = named_lease_kind(lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.QUANT_LEDGER_LEASE:
            return self._refuse_wrong_lease(kind.value)
        if not isinstance(lease, QuantLedgerLease):
            return invalid_input(
                "quant_ledger_lease",
                "Quant Ledger append requires a quant_ledger_lease (AD-9; FR-Q59)",
            )
        key = lease.owner.value
        ledger = self._ledgers.get(key)
        if ledger is None:
            return policy_rejection(
                "quant_ledger",
                "Quant Ledger append requires an opened Quant Ledger (AD-9; FR-Q59)",
                owner=key,
            )
        held = self._leases.get(key)
        if held is None:
            self._leases[key] = lease
            held = lease
        if held.holder_agent_id != lease.holder_agent_id:
            return policy_rejection(
                "quant_ledger_lease",
                "only one Agent of that Quant holding the quant_ledger_lease may "
                "append through before_ledger_append at a time (AD-9; FR-Q59)",
                holder_agent_id=held.holder_agent_id,
                given=lease.holder_agent_id,
            )
        inbound = dict(entry)
        if "recorded_at" not in inbound:
            stamped = self._stamp_recorded_at()
            if is_refusal(stamped):
                return stamped
            inbound["recorded_at"] = stamped.value
        if "id" not in inbound:
            inbound["id"] = self._next_entry_id(key)
        parsed = parse_quant_ledger_entry(inbound)
        gated = evaluate_before_ledger_append(
            inbound,
            lease_holder=held.holder_agent_id,
            timed_out=timed_out,
            attempted_result=attempted_result,
            quarantine=self._quarantine,
            schema_valid=not is_refusal(parsed),
            outside_lease_reason="outside_quant_ledger_lease",
        )
        if gated.disposition == "quarantine":
            field = (
                "entry"
                if gated.quarantine is not None and gated.quarantine.denial_source == "schema"
                else "quant_ledger_lease"
            )
            return policy_rejection(
                field,
                "before_ledger_append refused a schema-invalid Quant Ledger entry "
                "or one not authored by the quant_ledger_lease holder; the entry "
                "is quarantined and not discarded (AD-9; FR-Q59)",
                gate_reason=gated.result.reason,
                discarded=False,
            )
        if is_refusal(parsed):
            self._quarantine.write(gated.entry, reason="schema_invalid", denial_source="schema")
            return parsed
        record: QuantLedgerEntry = parsed.value
        if record.authored_by.agent_ref != held.holder_agent_id:
            return policy_rejection(
                "quant_ledger_lease",
                "an Agent appends the Quant Ledger only while holding that Quant's "
                "quant_ledger_lease (AD-9; FR-Q59)",
                holder_agent_id=held.holder_agent_id,
                authored_by=record.authored_by.agent_ref,
            )
        if record.authored_by.quant is not None and record.authored_by.quant != lease.owner:
            return policy_rejection(
                "authored_by",
                "authored_by carries the owning Quant ActorId (AD-9; FR-Q59)",
                owner=lease.owner.value,
                given=record.authored_by.quant.value,
            )
        payload = dict(record.to_payload())
        annotations = gated.entry.get("annotations")
        if isinstance(annotations, list):
            payload["annotations"] = [str(item) for item in cast("list[object]", annotations)]
        if gated.entry.get("hook_timeout"):
            payload["hook_timeout"] = True
        updated = ledger.append(payload)
        self._ledgers[key] = updated
        announced = self._announce(updated, payload, quant=ledger.owner)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def move_lead_flag(self, *, current: Quant, successor: Quant) -> Result[LeadFlagMove]:
        """Move a desk's lead flag; retain the existing Quant Ledger."""
        if current.desk != successor.desk:
            return policy_rejection(
                "lead_flag",
                "a desk's lead flag moves between Quants of that desk (AD-9; FR-Q59)",
                current_desk=current.desk.value,
                successor_desk=successor.desk.value,
            )
        if current.actor_id == successor.actor_id:
            return policy_rejection(
                "lead_flag",
                "lead flag movement names a distinct successor Quant (AD-9; FR-Q59)",
            )
        live = self._quants.get(current.actor_id.value, current)
        if not live.lead and not current.lead:
            return policy_rejection(
                "lead_flag",
                "lead flag movement starts from the Quant that currently carries it (AD-9; FR-Q59)",
                actor_id=current.actor_id.value,
            )
        previous = _quant_with_lead(current, lead=False)
        next_lead = _quant_with_lead(successor, lead=True)
        self._quants[previous.actor_id.value] = previous
        self._quants[next_lead.actor_id.value] = next_lead
        retained = self._ledgers.get(previous.actor_id.value)
        if retained is not None:
            self._ledgers[previous.actor_id.value] = QuantLedger(
                owner=previous,
                ledger_ref=retained.ledger_ref,
                entries=retained.entries,
            )
            retained = self._ledgers[previous.actor_id.value]
        # Successor does not receive a replacement ledger merely because the flag moved.
        return Ok(
            LeadFlagMove(
                previous=previous,
                successor=next_lead,
                retained_ledger=retained,
            )
        )

    def _next_entry_id(self, owner_key: str) -> str:
        seq = self._entry_seq.get(owner_key, 0) + 1
        self._entry_seq[owner_key] = seq
        return f"{owner_key}:entry:{seq}"

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
        ledger: QuantLedger,
        entry: Mapping[str, object],
        *,
        quant: Quant,
    ) -> Result[AnnouncementOutcome | None]:
        _ = ledger
        recorded_raw = entry.get("recorded_at")
        recorded_at = recorded_raw if isinstance(recorded_raw, int) else 0
        extra = {
            "quant": quant.actor_id.value,
            "desk": quant.desk.value,
            "agent": agent_ref_from_authored_by(entry.get("authored_by")),
        }
        extra_payload = {key: value for key, value in extra.items() if value is not None}
        if self._journal is None:
            self._announce_seq += 1
            self._announcements.append(
                LedgerAppendAnnouncement(
                    journal_seq=self._announce_seq,
                    store=QUANT_LEDGER_STORE_NAME,
                    recorded_at=recorded_at,
                    entry=entry,
                    desk=quant.desk.value,
                    quant=quant.actor_id.value,
                    agent=agent_ref_from_authored_by(entry.get("authored_by")),
                )
            )
            return Ok(None)
        addressed = content_address(dict(entry))
        if is_refusal(addressed):
            return addressed
        declared = self._journal.declare_store(QUANT_LEDGER_STORE_NAME)
        if is_refusal(declared):
            return declared
        announced = self._journal.announce_evidence_append(
            QUANT_LEDGER_STORE_NAME,
            addressed.value,
            extra_payload=extra_payload,
        )
        if is_refusal(announced):
            return announced
        seq = announced.value.journal_seq
        if seq is None:
            self._announce_seq += 1
            seq = self._announce_seq
        else:
            self._announce_seq = max(self._announce_seq, seq)
        self._announcements.append(
            LedgerAppendAnnouncement(
                journal_seq=seq,
                store=QUANT_LEDGER_STORE_NAME,
                recorded_at=recorded_at,
                entry=entry,
                desk=quant.desk.value,
                quant=quant.actor_id.value,
                agent=agent_ref_from_authored_by(entry.get("authored_by")),
            )
        )
        return Ok(announced.value)

    @staticmethod
    def _refuse_wrong_lease(kind: LeaseKind) -> TypedRefusal:
        return policy_rejection(
            "lease",
            "Quant Ledger append rights follow quant_ledger_lease, distinct from "
            "dispatch_lease and environment_lease (AD-9; FR-Q59)",
            given=kind.value,
            required=LeaseKind.QUANT_LEDGER_LEASE.value,
        )
