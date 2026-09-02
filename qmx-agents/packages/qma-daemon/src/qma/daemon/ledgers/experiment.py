"""Experiment Ledger — one scientist notebook per Experiment (AD-9; FR-Q54).

Owned by the Quant that registered the Experiment. Appended only by the Agent
holding the registering Task's ``dispatch_lease``. Entries are frozen; a
correction is a new entry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.ontology import ActorId

__all__ = ["ExperimentLedger", "ExperimentLedgerEntry"]


@dataclass(frozen=True, slots=True)
class ExperimentLedgerEntry:
    """One append-only Experiment Ledger row (CT-47; DEC-0308)."""

    authored_by: str
    owner: str
    model_deployment_ref: str
    spec_fp1: str
    body: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", MappingProxyType(dict(self.body)))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "authored_by": self.authored_by,
                "owner": self.owner,
                "model_deployment_ref": self.model_deployment_ref,
                "spec_fp1": self.spec_fp1,
                "body": dict(self.body),
            }
        )


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
                "ledger_ref": self.ledger_ref,
                "entries": [dict(entry.to_payload()) for entry in self.entries],
            }
        )
