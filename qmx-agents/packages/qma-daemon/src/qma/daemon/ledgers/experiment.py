"""Experiment Ledger — one scientist notebook per Experiment (AD-9; FR-Q54, FR-Q59).

Owned by the Experiment (one ledger per Experiment). Appended only by the Agent
holding the registering Task's ``dispatch_lease``. Entries are frozen; a
correction is a new entry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.content import content_address
from qma.core.ontology import ActorId
from qma.core.plugins.hooks import HookResult
from qma.core.ports.ledgers import named_lease_kind
from qma.core.vocabulary.enums import LeaseKind
from qma.daemon.hooks.ledger_gate import (
    LedgerQuarantineStream,
    evaluate_before_ledger_append,
)
from qma.daemon.journal.authoritative import AnnouncementOutcome, AuthoritativeJournal
from qma.daemon.ledgers.announcements import (
    LedgerAppendAnnouncement,
    agent_ref_from_authored_by,
)
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "EXPERIMENT_LEDGER_STORE_NAME",
    "ExperimentLedger",
    "ExperimentLedgerEntry",
    "ExperimentLedgerStore",
]

EXPERIMENT_LEDGER_STORE_NAME: Final[str] = "experiment_ledger"
_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(
        boot_epoch_id="experiment-ledger",
        wall_instants=walls,
        monotonic_ns=monos,
    )


@dataclass(frozen=True, slots=True)
class ExperimentLedgerEntry:
    """One append-only Experiment Ledger row (CT-47; DEC-0308)."""

    authored_by: str
    owner: str
    model_deployment_ref: str
    spec_fp1: str
    body: Mapping[str, object]
    id: str = ""
    recorded_at: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", MappingProxyType(dict(self.body)))

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "authored_by": self.authored_by,
            "owner": self.owner,
            "model_deployment_ref": self.model_deployment_ref,
            "spec_fp1": self.spec_fp1,
            "body": dict(self.body),
        }
        if self.id:
            payload["id"] = self.id
        if self.recorded_at:
            payload["recorded_at"] = self.recorded_at
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class ExperimentLedger:
    """Append-only notebook keyed by ExperimentSpec ``fp1``."""

    experiment_id: str
    owner: ActorId
    registering_task_id: str
    author_agent_id: str
    ledger_ref: str
    entries: tuple[ExperimentLedgerEntry, ...] = ()

    def append(self, entry: ExperimentLedgerEntry) -> ExperimentLedger:
        """Return a new ledger with ``entry`` appended. Never mutates in place."""
        return ExperimentLedger(
            experiment_id=self.experiment_id,
            owner=self.owner,
            registering_task_id=self.registering_task_id,
            author_agent_id=self.author_agent_id,
            ledger_ref=self.ledger_ref,
            entries=(*self.entries, entry),
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "experiment_id": self.experiment_id,
                "owner": self.owner.value,
                "registering_task_id": self.registering_task_id,
                "author_agent_id": self.author_agent_id,
                "store": EXPERIMENT_LEDGER_STORE_NAME,
                "ledger_ref": self.ledger_ref,
                "entries": [dict(entry.to_payload()) for entry in self.entries],
            }
        )


@dataclass
class ExperimentLedgerStore:
    """Independent Experiment Ledger store — one ledger per Experiment."""

    _ledgers: dict[str, ExperimentLedger] = field(default_factory=dict[str, ExperimentLedger])
    _leases: dict[str, DispatchLease] = field(default_factory=dict[str, DispatchLease])
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

    def announcements(self) -> tuple[LedgerAppendAnnouncement, ...]:
        return tuple(self._announcements)

    def get(self, experiment_id: str) -> ExperimentLedger | None:
        return self._ledgers.get(experiment_id)

    def lease_for(self, experiment_id: str) -> DispatchLease | None:
        return self._leases.get(experiment_id)

    def open_for_experiment(
        self,
        *,
        experiment_id: str,
        owner: ActorId,
        registering_lease: DispatchLease,
        ledger_ref: str | None = None,
    ) -> ExperimentLedger:
        """Open the one Experiment-owned ledger; never a second authoring Task."""
        existing = self._ledgers.get(experiment_id)
        if existing is not None:
            return existing
        ref = ledger_ref if ledger_ref is not None else f"experiment-ledger:{experiment_id}"
        ledger = ExperimentLedger(
            experiment_id=experiment_id,
            owner=owner,
            registering_task_id=registering_lease.task_id,
            author_agent_id=registering_lease.holder_agent_id,
            ledger_ref=ref,
        )
        self._ledgers[experiment_id] = ledger
        self._leases[experiment_id] = registering_lease
        return ledger

    def append_evidence(
        self,
        *,
        spec_fp1: object,
        dispatch_lease: DispatchLease,
        model_deployment_ref: object,
        body: Mapping[str, object],
        timed_out: bool = False,
        attempted_result: HookResult | None = None,
    ) -> Result[ExperimentLedger]:
        """Append evidence. Author is the registering Task's dispatch_lease holder."""
        if not isinstance(spec_fp1, str) or spec_fp1.strip() == "":
            return invalid_input("spec_fp1", "ledger append requires an ExperimentSpec fp1")
        if not isinstance(model_deployment_ref, str) or model_deployment_ref.strip() == "":
            return invalid_input(
                "model_deployment_ref",
                "Experiment Ledger entries carry the model deployment used",
            )
        kind = named_lease_kind(dispatch_lease)
        if is_refusal(kind):
            return kind
        if kind.value is not LeaseKind.DISPATCH_LEASE:
            return self._refuse_wrong_lease(kind.value)
        key = spec_fp1.strip()
        ledger = self._ledgers.get(key)
        if ledger is None:
            return invalid_input(
                "experiment_ledger_ref",
                "an ExperimentSpec with no resolvable Experiment Ledger is a "
                "registration defect (CT-47; DEC-0308; FR-Q54)",
                spec_fp1=key,
            )
        if dispatch_lease.task_id != ledger.registering_task_id:
            return policy_rejection(
                "dispatch_lease",
                "the Experiment owns one Experiment Ledger; only the Agent holding "
                "the registering Task's dispatch_lease may author an append "
                "(CT-51; FR-Q59)",
                registering_task_id=ledger.registering_task_id,
                given_task_id=dispatch_lease.task_id,
            )
        if dispatch_lease.holder_agent_id != ledger.author_agent_id:
            return policy_rejection(
                "authored_by",
                "the Agent holding the registering Task's dispatch_lease is the "
                "Experiment Ledger author (CT-47; DEC-0308; FR-Q59)",
                author_agent_id=ledger.author_agent_id,
                given_agent_id=dispatch_lease.holder_agent_id,
            )
        recorded_at = self._stamp_recorded_at()
        if is_refusal(recorded_at):
            return recorded_at
        entry_id = self._next_entry_id(key)
        inbound: dict[str, object] = {
            "id": entry_id,
            "kind": "evidence",
            "authored_by": {
                "agent": dispatch_lease.holder_agent_id,
                "quant": ledger.owner.value,
            },
            "recorded_at": recorded_at.value,
            "model_deployment_ref": model_deployment_ref.strip(),
            "spec_fp1": key,
            "body": dict(body),
        }
        gated = evaluate_before_ledger_append(
            inbound,
            lease_holder=ledger.author_agent_id,
            timed_out=timed_out,
            attempted_result=attempted_result,
            quarantine=self._quarantine,
            schema_valid=True,
            outside_lease_reason="outside_dispatch_lease",
        )
        if gated.disposition == "quarantine":
            return policy_rejection(
                "dispatch_lease",
                "before_ledger_append refused an Experiment Ledger append not "
                "authored by the registering Task's dispatch_lease holder; the "
                "entry is quarantined and not discarded (CT-51; FR-Q59)",
                gate_reason=gated.result.reason,
                discarded=False,
            )
        record = ExperimentLedgerEntry(
            authored_by=dispatch_lease.holder_agent_id,
            owner=ledger.owner.value,
            model_deployment_ref=model_deployment_ref.strip(),
            spec_fp1=key,
            body=body,
            id=entry_id,
            recorded_at=recorded_at.value,
        )
        updated = ledger.append(record)
        self._ledgers[key] = updated
        announced = self._announce(updated, inbound, ledger=updated)
        if is_refusal(announced):
            return announced
        return Ok(updated)

    def _next_entry_id(self, experiment_id: str) -> str:
        seq = self._entry_seq.get(experiment_id, 0) + 1
        self._entry_seq[experiment_id] = seq
        return f"{experiment_id}:entry:{seq}"

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
        _updated: ExperimentLedger,
        entry: Mapping[str, object],
        *,
        ledger: ExperimentLedger,
    ) -> Result[AnnouncementOutcome | None]:
        recorded_raw = entry.get("recorded_at")
        recorded_at = recorded_raw if isinstance(recorded_raw, int) else 0
        agent = agent_ref_from_authored_by(entry.get("authored_by"))
        extra_payload: dict[str, object] = {
            "experiment": ledger.experiment_id,
            "quant": ledger.owner.value,
            "task": ledger.registering_task_id,
        }
        if agent is not None:
            extra_payload["agent"] = agent
        if self._journal is None:
            self._announce_seq += 1
            self._announcements.append(
                LedgerAppendAnnouncement(
                    journal_seq=self._announce_seq,
                    store=EXPERIMENT_LEDGER_STORE_NAME,
                    recorded_at=recorded_at,
                    entry=entry,
                    quant=ledger.owner.value,
                    agent=agent,
                    task=ledger.registering_task_id,
                    experiment=ledger.experiment_id,
                )
            )
            return Ok(None)
        addressed = content_address(dict(entry))
        if is_refusal(addressed):
            return addressed
        declared = self._journal.declare_store(EXPERIMENT_LEDGER_STORE_NAME)
        if is_refusal(declared):
            return declared
        announced = self._journal.announce_evidence_append(
            EXPERIMENT_LEDGER_STORE_NAME,
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
                store=EXPERIMENT_LEDGER_STORE_NAME,
                recorded_at=recorded_at,
                entry=entry,
                quant=ledger.owner.value,
                agent=agent,
                task=ledger.registering_task_id,
                experiment=ledger.experiment_id,
            )
        )
        return Ok(announced.value)

    @staticmethod
    def _refuse_wrong_lease(kind: LeaseKind) -> TypedRefusal:
        return policy_rejection(
            "lease",
            "Experiment Ledger append rights follow the registering Task's "
            "dispatch_lease, distinct from environment_lease and "
            "quant_ledger_lease (CT-51; FR-Q59)",
            given=kind.value,
            required=LeaseKind.DISPATCH_LEASE.value,
        )
