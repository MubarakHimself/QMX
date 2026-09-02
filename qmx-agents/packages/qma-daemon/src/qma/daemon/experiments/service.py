"""Register content-addressed ExperimentSpec records and CT-07 lineage (FR-Q54).

Equivalent specs collapse on inherited ``fp1``. Successors are new records.
Lineage is append-only CT-07 ``branches-from`` edges over those fingerprints.
The Experiment Ledger is resolved at registration; its author is the Agent
holding the registering Task's ``dispatch_lease``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.ports.experiments import (
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    ExperimentSpec,
)
from qma.daemon.ledgers.experiment import ExperimentLedger, ExperimentLedgerEntry
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.registry import EdgeLog, LineageEdge

__all__ = ["ExperimentSpecService", "RegisteredExperiment"]


def _ledger_ref_for(spec_fp1: str) -> str:
    return f"experiment-ledger:{spec_fp1}"


@dataclass(frozen=True, slots=True)
class RegisteredExperiment:
    """Registered ExperimentSpec plus its ledger and optional lineage edge."""

    spec: ExperimentSpec
    ledger: ExperimentLedger
    dispatch_lease: DispatchLease
    lineage_edge: LineageEdge | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "spec": dict(self.spec.to_payload()),
            "ledger": dict(self.ledger.to_payload()),
            "dispatch_lease": dict(self.dispatch_lease.to_payload()),
        }
        if self.lineage_edge is not None:
            payload["lineage_edge"] = {
                "edge_type": self.lineage_edge.edge_type.value,
                "from_ref": self.lineage_edge.from_ref.value,
                "to_ref": self.lineage_edge.to_ref.value,
                "edge_fingerprint": self.lineage_edge.edge_fingerprint.value,
            }
        return MappingProxyType(payload)


class ExperimentSpecService:
    """Daemon registration, ledger append, and CT-07 lineage for ExperimentSpec."""

    def __init__(self, *, writer: WriterId | None = None) -> None:
        if writer is None:
            minted = WriterId.try_create("qma-daemon", "authoring", "experiment-lineage", "boot-1")
            if is_refusal(minted):
                msg = "experiment lineage writer id must construct"
                raise RuntimeError(msg)
            writer = minted.value
        self._writer = writer
        self._edges = EdgeLog(writer)
        self._specs: dict[str, ExperimentSpec] = {}
        self._ledgers: dict[str, ExperimentLedger] = {}
        self._leases: dict[str, DispatchLease] = {}
        self._lineage: dict[str, LineageEdge] = {}

    @property
    def edge_log(self) -> EdgeLog:
        return self._edges

    def register(
        self,
        spec: ExperimentSpec,
        *,
        dispatch_lease: DispatchLease,
        model_deployment_ref: object,
    ) -> Result[RegisteredExperiment]:
        """Register a spec. Identical ``fp1`` collapses to the existing record."""
        if not isinstance(model_deployment_ref, str) or model_deployment_ref.strip() == "":
            return invalid_input(
                "model_deployment_ref",
                "Experiment Ledger entries carry the model deployment used",
            )
        if not dispatch_lease.holder_agent_id.strip():
            return invalid_input(
                "dispatch_lease",
                "Experiment registration requires the Agent holding dispatch_lease",
            )
        existing = self._specs.get(spec.spec_fp1)
        if existing is not None:
            return Ok(
                RegisteredExperiment(
                    spec=existing,
                    ledger=self._ledgers[spec.spec_fp1],
                    dispatch_lease=self._leases[spec.spec_fp1],
                    lineage_edge=self._lineage.get(spec.spec_fp1),
                )
            )
        ledger_ref = _ledger_ref_for(spec.spec_fp1)
        stored = spec.with_ledger_ref(ledger_ref)
        if stored.spec_fp1 != spec.spec_fp1:
            return policy_rejection(
                "spec_fp1",
                "Experiment Ledger attachment must not change spec identity",
            )
        ledger = ExperimentLedger(
            experiment_id=stored.spec_fp1,
            owner=dispatch_lease.owner,
            registering_task_id=dispatch_lease.task_id,
            author_agent_id=dispatch_lease.holder_agent_id,
            ledger_ref=ledger_ref,
        )
        self._specs[stored.spec_fp1] = stored
        self._ledgers[stored.spec_fp1] = ledger
        self._leases[stored.spec_fp1] = dispatch_lease
        return Ok(
            RegisteredExperiment(
                spec=stored,
                ledger=ledger,
                dispatch_lease=dispatch_lease,
            )
        )

    def create_successor(
        self,
        *,
        predecessor_fp1: object,
        change: object,
        dispatch_lease: DispatchLease,
        model_deployment_ref: object,
        resolved_config_ref: object = None,
        code_ref: object = None,
        data_ref: object = None,
        environment_ref: object = None,
        seed: object = None,
        model_and_harness_version: object = None,
        cost_assumptions: object = None,
        mechanisms: object = None,
        extra: Mapping[str, object] | None = None,
    ) -> Result[RegisteredExperiment]:
        """Mint a new spec, append a CT-07 edge, and leave the predecessor untouched."""
        if not isinstance(predecessor_fp1, str) or predecessor_fp1.strip() == "":
            return invalid_input("predecessor_fp1", "successor requires a predecessor fp1")
        predecessor = self._specs.get(predecessor_fp1.strip())
        if predecessor is None:
            return invalid_input(
                "predecessor_fp1",
                "unknown predecessor ExperimentSpec",
                predecessor_fp1=predecessor_fp1,
            )
        snapshot = dict(predecessor.to_payload())
        created = predecessor.with_change(
            change=change,
            resolved_config_ref=resolved_config_ref,
            code_ref=code_ref,
            data_ref=data_ref,
            environment_ref=environment_ref,
            seed=seed,
            model_and_harness_version=model_and_harness_version,
            cost_assumptions=cost_assumptions,
            mechanisms=mechanisms,
            extra=extra,
        )
        if is_refusal(created):
            return created
        registered = self.register(
            created.value,
            dispatch_lease=dispatch_lease,
            model_deployment_ref=model_deployment_ref,
        )
        if is_refusal(registered):
            return registered
        record = registered.value
        if dict(self._specs[predecessor.spec_fp1].to_payload()) != snapshot:
            return policy_rejection(
                "predecessor",
                "lineage never mutates the predecessor ExperimentSpec in place "
                "(CT-07; CT-47; FR-Q54)",
            )
        appended = self._edges.append(
            edge_type=EXPERIMENT_LINEAGE_EDGE_TYPE,
            from_ref=record.spec.spec_fp1,
            to_ref=predecessor.spec_fp1,
        )
        if is_refusal(appended):
            return appended
        edge = appended.value.edge
        self._lineage[record.spec.spec_fp1] = edge
        return Ok(
            RegisteredExperiment(
                spec=record.spec,
                ledger=record.ledger,
                dispatch_lease=record.dispatch_lease,
                lineage_edge=edge,
            )
        )

    def append_evidence(
        self,
        *,
        spec_fp1: object,
        dispatch_lease: DispatchLease,
        model_deployment_ref: object,
        body: Mapping[str, object],
    ) -> Result[ExperimentLedger]:
        """Append evidence. Author is the registering Task's dispatch_lease holder."""
        if not isinstance(spec_fp1, str) or spec_fp1.strip() == "":
            return invalid_input("spec_fp1", "ledger append requires an ExperimentSpec fp1")
        if not isinstance(model_deployment_ref, str) or model_deployment_ref.strip() == "":
            return invalid_input(
                "model_deployment_ref",
                "Experiment Ledger entries carry the model deployment used",
            )
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
                "two Tasks registering against one Experiment never produce two "
                "simultaneous authors; only the registering Task's dispatch_lease "
                "holder may append (CT-47; DEC-0308; FR-Q54)",
                registering_task_id=ledger.registering_task_id,
                given_task_id=dispatch_lease.task_id,
            )
        if dispatch_lease.holder_agent_id != ledger.author_agent_id:
            return policy_rejection(
                "authored_by",
                "the Agent holding the registering Task's dispatch_lease is the "
                "Experiment Ledger author (CT-47; DEC-0308; FR-Q54)",
                author_agent_id=ledger.author_agent_id,
                given_agent_id=dispatch_lease.holder_agent_id,
            )
        entry = ExperimentLedgerEntry(
            authored_by=dispatch_lease.holder_agent_id,
            owner=ledger.owner.value,
            model_deployment_ref=model_deployment_ref.strip(),
            spec_fp1=key,
            body=body,
        )
        updated = ledger.append(entry)
        self._ledgers[key] = updated
        return Ok(updated)

    def resolve(self, spec_fp1: object) -> Result[RegisteredExperiment]:
        """Resolve a registered spec. Identity content is never rewritten."""
        if not isinstance(spec_fp1, str) or spec_fp1.strip() == "":
            return invalid_input("spec_fp1", "resolve requires an ExperimentSpec fp1")
        key = spec_fp1.strip()
        spec = self._specs.get(key)
        ledger = self._ledgers.get(key)
        lease = self._leases.get(key)
        if spec is None or ledger is None or lease is None:
            return invalid_input("spec_fp1", "unknown ExperimentSpec", spec_fp1=key)
        if spec.experiment_ledger_ref is None:
            return invalid_input(
                "experiment_ledger_ref",
                "an ExperimentSpec with no resolvable Experiment Ledger is a "
                "registration defect (CT-47; DEC-0308; FR-Q54)",
            )
        return Ok(
            RegisteredExperiment(
                spec=spec,
                ledger=ledger,
                dispatch_lease=lease,
                lineage_edge=self._lineage.get(key),
            )
        )

    def resolve_ledger(self, spec_fp1: object) -> Result[ExperimentLedger]:
        """Resolve the Experiment Ledger linked from a registered spec."""
        resolved = self.resolve(spec_fp1)
        if is_refusal(resolved):
            return resolved
        return Ok(resolved.value.ledger)

    def lineage_edges(self, spec_fp1: object) -> tuple[LineageEdge, ...]:
        """CT-07 edges whose ``from_ref`` or ``to_ref`` is this spec."""
        if not isinstance(spec_fp1, str):
            return ()
        outgoing = self._edges.edges_from(spec_fp1)
        incoming = self._edges.edges_to(spec_fp1)
        return (*outgoing, *incoming)

    def mutate_in_place(self, spec_fp1: object, **_fields: object) -> Result[ExperimentSpec]:
        """Every in-place edit is refused. A change is a new content-addressed spec."""
        _ = spec_fp1
        return policy_rejection(
            "spec",
            "ExperimentSpec records are immutable; a change mints a successor "
            "with a CT-07 lineage edge and never mutates either record "
            "(CT-07; CT-47; FR-Q54)",
        )
