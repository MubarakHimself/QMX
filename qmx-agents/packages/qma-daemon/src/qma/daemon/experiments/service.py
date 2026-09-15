"""Register content-addressed ExperimentSpec records and CT-07 lineage (FR-Q54).

Equivalent specs collapse on inherited ``fp1``. Successors are new records.
Lineage is append-only CT-07 ``branches-from`` edges over those fingerprints.
The Experiment Ledger is resolved at registration; its author is the Agent
holding the registering Task's ``dispatch_lease``. When bound to the sole
sqlite writer, those records are product truth and survive a daemon restart.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.ports.experiments import (
    COORDINATED_CONTINUITY_KIND,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    ExperimentSpec,
    admit_coordinated_continuity,
    admit_experiment_evidence_body,
)
from qma.daemon.experiments.sqlite import ExperimentSqliteStore
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.ledgers.experiment import (
    ExperimentLedger,
    ExperimentLedgerStore,
)
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
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

    def __init__(
        self,
        *,
        writer: WriterId | None = None,
        ledgers: ExperimentLedgerStore | None = None,
        sqlite: SingleSqliteWriter | None = None,
        journal: AuthoritativeJournal | None = None,
    ) -> None:
        if writer is None:
            minted = WriterId.try_create("qma-daemon", "authoring", "experiment-lineage", "boot-1")
            if is_refusal(minted):
                msg = "experiment lineage writer id must construct"
                raise RuntimeError(msg)
            writer = minted.value
        self._writer = writer
        self._edges = EdgeLog(writer)
        self._specs: dict[str, ExperimentSpec] = {}
        self._ledger_store = ledgers if ledgers is not None else ExperimentLedgerStore()
        self._leases: dict[str, DispatchLease] = {}
        self._lineage: dict[str, LineageEdge] = {}
        self._edge_rows: list[LineageEdge] = []
        self._durable: ExperimentSqliteStore | None = None
        self._journal = journal
        if sqlite is not None:
            attached = self.bind_durable(sqlite=sqlite, journal=journal)
            if is_refusal(attached):
                msg = "experiment sqlite restore failed"
                raise RuntimeError(msg)

    @property
    def edge_log(self) -> EdgeLog:
        return self._edges

    @property
    def ledgers(self) -> ExperimentLedgerStore:
        return self._ledger_store

    @property
    def product_truth(self) -> str:
        """Sqlite is product truth when bound; in-memory maps are not."""
        return "sqlite" if self._durable is not None else "memory"

    def bind_durable(
        self,
        *,
        sqlite: SingleSqliteWriter,
        journal: AuthoritativeJournal | None = None,
    ) -> Result[int]:
        """Attach the sole sqlite writer and restore specs, ledgers, and edges."""
        self._durable = ExperimentSqliteStore(sqlite)
        if journal is not None:
            self._journal = journal
        self._durable.ensure_schema()
        return self.reload()

    def drop_memory_cache(self) -> None:
        """Drop in-memory maps. Sqlite remains product truth."""
        self._specs.clear()
        self._leases.clear()
        self._lineage.clear()
        self._edge_rows.clear()

    def reload(self) -> Result[int]:
        """Replace in-memory maps from sqlite. No-op when sqlite is unbound."""
        store = self._durable
        if store is None:
            return Ok(0)
        loaded = store.load_all()
        if is_refusal(loaded):
            return loaded
        self._specs = {}
        self._leases = {}
        self._lineage = {}
        self._edge_rows = []
        for snapshot in loaded.value:
            self._specs[snapshot.spec.spec_fp1] = snapshot.spec
            self._leases[snapshot.spec.spec_fp1] = snapshot.lease
            self._ledger_store.install_restored(
                snapshot.ledger,
                snapshot.lease,
                entry_seq=snapshot.entry_seq,
            )
            if snapshot.lineage_edge is not None:
                self._lineage[snapshot.spec.spec_fp1] = snapshot.lineage_edge
                self._edge_rows.append(snapshot.lineage_edge)
        return Ok(len(loaded.value))

    def admit_continuity(self, kind: object) -> Result[str]:
        """Coordinated continuity is ExperimentSpec fp1; Project/Workspace refuse."""
        return admit_coordinated_continuity(kind)

    def register_project(self, *_args: object, **_kwargs: object) -> Result[str]:
        """Refused — Project is not a continuity object (DEC-0284)."""
        return admit_coordinated_continuity("project")

    def register_workspace(self, *_args: object, **_kwargs: object) -> Result[str]:
        """Refused — Workspace is not a continuity object (DEC-0284)."""
        return admit_coordinated_continuity("workspace")

    def copy_qmb_jsonl(self, payload: object = None) -> Result[None]:
        """Refused — QMA stores _refs and never copies QMB JSONL."""
        return policy_rejection(
            "qmb_jsonl",
            "QMA stores _refs only — it does not copy or merge JSONL or CT-32 "
            "(FR-W10; NFR-W04; DEC-0276)",
            payload=repr(payload),
        )

    def merge_ct32(self, payload: object = None) -> Result[None]:
        """Refused — QMA stores _refs and never copies CT-32."""
        return policy_rejection(
            "ct32",
            "QMA stores _refs only — it does not copy or merge JSONL or CT-32 "
            "(FR-W10; NFR-W04; DEC-0276)",
            payload=repr(payload),
        )

    def write_edges_from_qmb(self, *_args: object, **_kwargs: object) -> Result[None]:
        """Refused — QMB does not write ExperimentSpec CT-07 edges."""
        return policy_rejection(
            "qmb_lineage",
            "QMB does not write ExperimentSpec edges; CT-07 branches-from "
            "successor edges persist through the daemon journal / sqlite writer "
            "(FR-W10; DEC-0276; DEC-0308)",
        )

    def register(
        self,
        spec: ExperimentSpec,
        *,
        dispatch_lease: DispatchLease,
        model_deployment_ref: object,
        continuity_kind: object = COORDINATED_CONTINUITY_KIND,
    ) -> Result[RegisteredExperiment]:
        """Register a spec. Identical ``fp1`` collapses to the existing record."""
        continuity = admit_coordinated_continuity(continuity_kind)
        if is_refusal(continuity):
            return continuity
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
            existing_ledger = self._ledger_store.get(spec.spec_fp1)
            if existing_ledger is None:
                return invalid_input(
                    "experiment_ledger_ref",
                    "an ExperimentSpec with no resolvable Experiment Ledger is a "
                    "registration defect (CT-47; DEC-0308; FR-Q54)",
                    spec_fp1=spec.spec_fp1,
                )
            return Ok(
                RegisteredExperiment(
                    spec=existing,
                    ledger=existing_ledger,
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
        ledger = self._ledger_store.open_for_experiment(
            experiment_id=stored.spec_fp1,
            owner=dispatch_lease.owner,
            registering_lease=dispatch_lease,
            ledger_ref=ledger_ref,
        )
        self._specs[stored.spec_fp1] = stored
        self._leases[stored.spec_fp1] = dispatch_lease
        persisted = self._persist_registration(stored, dispatch_lease, ledger)
        if is_refusal(persisted):
            return persisted
        announced = self._journal_event(
            "experiment.registered",
            {
                "spec_fp1": stored.spec_fp1,
                "experiment_ledger_ref": ledger_ref,
                "continuity": COORDINATED_CONTINUITY_KIND,
            },
        )
        if is_refusal(announced):
            return announced
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
        source: object = "qma-daemon",
    ) -> Result[RegisteredExperiment]:
        """Mint a new spec, append a CT-07 edge, and leave the predecessor untouched."""
        if isinstance(source, str) and source.strip().casefold() in {"qmb", "qmb-cli", "qmb_cli"}:
            return policy_rejection(
                "qmb_lineage",
                "QMB does not write ExperimentSpec edges; CT-07 branches-from "
                "successor edges persist through the daemon journal / sqlite writer "
                "(FR-W10; DEC-0276; DEC-0308)",
                source=source,
            )
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
        self._edge_rows.append(edge)
        persisted = self._persist_edge(edge)
        if is_refusal(persisted):
            return persisted
        announced = self._journal_event(
            "experiment.branched",
            {
                "spec_fp1": record.spec.spec_fp1,
                "predecessor_fp1": predecessor.spec_fp1,
                "edge_type": EXPERIMENT_LINEAGE_EDGE_TYPE,
                "edge_fingerprint": edge.edge_fingerprint.value,
            },
        )
        if is_refusal(announced):
            return announced
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
        admitted = admit_experiment_evidence_body(body)
        if is_refusal(admitted):
            return admitted
        appended = self._ledger_store.append_evidence(
            spec_fp1=spec_fp1,
            dispatch_lease=dispatch_lease,
            model_deployment_ref=model_deployment_ref,
            body=admitted.value,
        )
        if is_refusal(appended):
            return appended
        persisted = self._persist_ledger(appended.value)
        if is_refusal(persisted):
            return persisted
        return appended

    def resolve(self, spec_fp1: object) -> Result[RegisteredExperiment]:
        """Resolve a registered spec. Identity content is never rewritten."""
        if not isinstance(spec_fp1, str) or spec_fp1.strip() == "":
            return invalid_input("spec_fp1", "resolve requires an ExperimentSpec fp1")
        key = spec_fp1.strip()
        spec = self._specs.get(key)
        ledger = self._ledger_store.get(key)
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
        if self._edge_rows:
            return tuple(
                edge
                for edge in self._edge_rows
                if spec_fp1 in {edge.from_ref.value, edge.to_ref.value}
            )
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

    def _persist_registration(
        self,
        spec: ExperimentSpec,
        lease: DispatchLease,
        ledger: ExperimentLedger,
    ) -> Result[None]:
        store = self._durable
        if store is None:
            return Ok(None)
        store.put_spec(spec, lease)
        store.put_ledger(ledger)
        return Ok(None)

    def _persist_ledger(self, ledger: ExperimentLedger) -> Result[None]:
        store = self._durable
        if store is None:
            return Ok(None)
        store.put_ledger(ledger)
        for entry in ledger.entries:
            store.put_entry(entry)
        return Ok(None)

    def _persist_edge(self, edge: LineageEdge) -> Result[None]:
        store = self._durable
        if store is None:
            return Ok(None)
        store.put_edge(edge)
        return Ok(None)

    def _journal_event(
        self,
        event: str,
        payload: Mapping[str, object],
    ) -> Result[None]:
        if self._journal is None:
            return Ok(None)
        appended = self._journal.append_event(event, payload=payload)
        if is_refusal(appended):
            return appended
        return Ok(None)
