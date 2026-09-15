"""Sqlite product truth for ExperimentSpec, Experiment Ledger, and CT-07 edges.

In-memory maps are a cache. A daemon restart reloads these tables through the
sole sqlite writer. QMB JSONL and CT-32 stay behind ``_ref`` keys.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qma.core.ontology import ActorId
from qma.core.ports.experiments import (
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    ExperimentSpec,
    parse_experiment_spec,
)
from qma.daemon.ledgers.experiment import ExperimentLedger, ExperimentLedgerEntry
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.data.store.refusals import invalid_input, storage_failure
from qmf.registry import LineageEdge

__all__ = [
    "EXPERIMENT_LEDGER_ENTRY_TABLE",
    "EXPERIMENT_LEDGER_TABLE",
    "EXPERIMENT_LINEAGE_EDGE_TABLE",
    "EXPERIMENT_SPEC_TABLE",
    "EXPERIMENT_SQLITE_TABLES",
    "ExperimentSqliteSnapshot",
    "ExperimentSqliteStore",
]

EXPERIMENT_SPEC_TABLE: Final[str] = "experiment_spec"
EXPERIMENT_LEDGER_TABLE: Final[str] = "experiment_ledger"
EXPERIMENT_LEDGER_ENTRY_TABLE: Final[str] = "experiment_ledger_entry"
EXPERIMENT_LINEAGE_EDGE_TABLE: Final[str] = "experiment_lineage_edge"
EXPERIMENT_SQLITE_TABLES: Final[frozenset[str]] = frozenset(
    {
        EXPERIMENT_SPEC_TABLE,
        EXPERIMENT_LEDGER_TABLE,
        EXPERIMENT_LEDGER_ENTRY_TABLE,
        EXPERIMENT_LINEAGE_EDGE_TABLE,
    }
)

_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS experiment_spec (
    spec_fp1 TEXT PRIMARY KEY NOT NULL,
    payload TEXT NOT NULL,
    ledger_ref TEXT NOT NULL,
    lease_payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_ledger (
    experiment_id TEXT PRIMARY KEY NOT NULL,
    owner TEXT NOT NULL,
    registering_task_id TEXT NOT NULL,
    author_agent_id TEXT NOT NULL,
    ledger_ref TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_ledger_entry (
    id TEXT PRIMARY KEY NOT NULL,
    experiment_id TEXT NOT NULL,
    recorded_at INTEGER NOT NULL,
    authored_by TEXT NOT NULL,
    model_deployment_ref TEXT NOT NULL,
    spec_fp1 TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_lineage_edge (
    edge_fingerprint TEXT PRIMARY KEY NOT NULL,
    from_ref TEXT NOT NULL,
    to_ref TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS experiment_ledger_entry_by_experiment
    ON experiment_ledger_entry (experiment_id, recorded_at);
CREATE INDEX IF NOT EXISTS experiment_lineage_edge_from
    ON experiment_lineage_edge (from_ref);
CREATE INDEX IF NOT EXISTS experiment_lineage_edge_to
    ON experiment_lineage_edge (to_ref);
"""


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def _load_object(raw: object, *, field: str) -> Result[dict[str, object]]:
    if not isinstance(raw, str) or raw.strip() == "":
        return invalid_input(field, "sqlite row payload is a JSON object")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return storage_failure(
            f"experiment sqlite payload is not JSON: {exc}",
            context={"field": field},
        )
    if not isinstance(parsed, dict):
        return invalid_input(field, "sqlite row payload is a JSON object")
    return Ok(cast("dict[str, object]", parsed))


def _parse_lease(payload: Mapping[str, object]) -> Result[DispatchLease]:
    task_id = payload.get("task_id")
    holder = payload.get("holder_agent_id")
    mission_id = payload.get("mission_id")
    owner_raw = payload.get("owner")
    if not isinstance(task_id, str) or task_id.strip() == "":
        return invalid_input("dispatch_lease", "restored lease requires task_id")
    if not isinstance(holder, str) or holder.strip() == "":
        return invalid_input("dispatch_lease", "restored lease requires holder_agent_id")
    if not isinstance(mission_id, str) or mission_id.strip() == "":
        return invalid_input("dispatch_lease", "restored lease requires mission_id")
    owner = ActorId.try_create(owner_raw)
    if is_refusal(owner):
        return owner
    return Ok(
        DispatchLease(
            task_id=task_id,
            holder_agent_id=holder,
            mission_id=mission_id,
            owner=owner.value,
        )
    )


def _parse_edge(payload: Mapping[str, object]) -> Result[LineageEdge]:
    writer_raw = payload.get("writer")
    if not isinstance(writer_raw, dict):
        return invalid_input("writer", "restored CT-07 edge carries its original writer")
    writer_body = cast("dict[str, object]", writer_raw)
    writer = WriterId.try_create(
        writer_body.get("machine"),
        writer_body.get("role"),
        writer_body.get("stream"),
        writer_body.get("boot_epoch_id"),
    )
    if is_refusal(writer):
        return writer
    built = LineageEdge.try_create(
        payload.get("edge_type", EXPERIMENT_LINEAGE_EDGE_TYPE),
        payload.get("from_ref"),
        payload.get("to_ref"),
        writer.value,
        payload.get("contract_format_version", 1),
    )
    if is_refusal(built):
        return built
    stored_fp = payload.get("edge_fingerprint")
    if isinstance(stored_fp, str) and stored_fp != built.value.edge_fingerprint.value:
        return invalid_input(
            "edge_fingerprint",
            "restored CT-07 edge fingerprint must match derived identity",
            stored=stored_fp,
            derived=built.value.edge_fingerprint.value,
        )
    return built


def _entry_seq(experiment_id: str, entries: tuple[ExperimentLedgerEntry, ...]) -> int:
    prefix = f"{experiment_id}:entry:"
    highest = 0
    for entry in entries:
        if not entry.id.startswith(prefix):
            continue
        tail = entry.id[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return highest


@dataclass(frozen=True, slots=True)
class ExperimentSqliteSnapshot:
    """One restored experiment: spec, lease, ledger, optional successor edge."""

    spec: ExperimentSpec
    lease: DispatchLease
    ledger: ExperimentLedger
    entry_seq: int
    lineage_edge: LineageEdge | None


class ExperimentSqliteStore:
    """Sole-writer sqlite rows for coordinated ExperimentSpec identity."""

    def __init__(self, sqlite: SingleSqliteWriter) -> None:
        self._sqlite = sqlite

    def ensure_schema(self) -> None:
        """Create experiment tables on the sole writable connection."""

        def _ddl(conn: sqlite3.Connection) -> None:
            conn.executescript(_SCHEMA_SQL)

        self._sqlite.run(_ddl)

    def put_spec(self, spec: ExperimentSpec, lease: DispatchLease) -> None:
        ledger_ref = spec.experiment_ledger_ref
        if ledger_ref is None:
            ledger_ref = f"experiment-ledger:{spec.spec_fp1}"
        self._sqlite.execute(
            "INSERT OR REPLACE INTO experiment_spec "
            "(spec_fp1, payload, ledger_ref, lease_payload) VALUES (?, ?, ?, ?)",
            (spec.spec_fp1, _dump(spec.to_payload()), ledger_ref, _dump(lease.to_payload())),
        )

    def put_ledger(self, ledger: ExperimentLedger) -> None:
        self._sqlite.execute(
            "INSERT OR REPLACE INTO experiment_ledger "
            "(experiment_id, owner, registering_task_id, author_agent_id, ledger_ref) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                ledger.experiment_id,
                ledger.owner.value,
                ledger.registering_task_id,
                ledger.author_agent_id,
                ledger.ledger_ref,
            ),
        )

    def put_entry(self, entry: ExperimentLedgerEntry) -> None:
        self._sqlite.execute(
            "INSERT OR REPLACE INTO experiment_ledger_entry "
            "(id, experiment_id, recorded_at, authored_by, model_deployment_ref, "
            "spec_fp1, body) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.spec_fp1,
                entry.recorded_at,
                entry.authored_by,
                entry.model_deployment_ref,
                entry.spec_fp1,
                _dump(entry.body),
            ),
        )

    def put_edge(self, edge: LineageEdge) -> None:
        payload = dict(edge.fp1_identity())
        payload["edge_fingerprint"] = edge.edge_fingerprint.value
        self._sqlite.execute(
            "INSERT OR REPLACE INTO experiment_lineage_edge "
            "(edge_fingerprint, from_ref, to_ref, edge_type, payload) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                edge.edge_fingerprint.value,
                edge.from_ref.value,
                edge.to_ref.value,
                edge.edge_type.value,
                _dump(payload),
            ),
        )

    def load_all(self) -> Result[tuple[ExperimentSqliteSnapshot, ...]]:
        """Reload product truth. In-memory maps are not consulted."""
        spec_rows = self._sqlite.execute(
            "SELECT spec_fp1, payload, ledger_ref, lease_payload FROM experiment_spec "
            "ORDER BY spec_fp1"
        )
        ledger_rows = self._sqlite.execute(
            "SELECT experiment_id, owner, registering_task_id, author_agent_id, "
            "ledger_ref FROM experiment_ledger"
        )
        entry_rows = self._sqlite.execute(
            "SELECT id, experiment_id, recorded_at, authored_by, model_deployment_ref, "
            "spec_fp1, body FROM experiment_ledger_entry ORDER BY recorded_at, id"
        )
        edge_rows = self._sqlite.execute("SELECT from_ref, payload FROM experiment_lineage_edge")

        ledgers: dict[str, tuple[str, str, str, str]] = {}
        for row in ledger_rows:
            experiment_id = str(row[0])
            ledgers[experiment_id] = (str(row[1]), str(row[2]), str(row[3]), str(row[4]))

        entries_by_id: dict[str, list[ExperimentLedgerEntry]] = {}
        for row in entry_rows:
            body = _load_object(row[6], field="experiment_ledger_entry.body")
            if is_refusal(body):
                return body
            experiment_id = str(row[1])
            entry = ExperimentLedgerEntry(
                authored_by=str(row[3]),
                owner="",
                model_deployment_ref=str(row[4]),
                spec_fp1=str(row[5]),
                body=body.value,
                id=str(row[0]),
                recorded_at=int(str(row[2])),
            )
            entries_by_id.setdefault(experiment_id, []).append(entry)

        edges_by_from: dict[str, LineageEdge] = {}
        for row in edge_rows:
            payload = _load_object(row[1], field="experiment_lineage_edge.payload")
            if is_refusal(payload):
                return payload
            edge = _parse_edge(payload.value)
            if is_refusal(edge):
                return edge
            edges_by_from[str(row[0])] = edge.value

        snapshots: list[ExperimentSqliteSnapshot] = []
        for row in spec_rows:
            spec_payload = _load_object(row[1], field="experiment_spec.payload")
            if is_refusal(spec_payload):
                return spec_payload
            spec = parse_experiment_spec(**spec_payload.value)
            if is_refusal(spec):
                return spec
            lease_payload = _load_object(row[3], field="experiment_spec.lease_payload")
            if is_refusal(lease_payload):
                return lease_payload
            lease = _parse_lease(lease_payload.value)
            if is_refusal(lease):
                return lease
            header = ledgers.get(spec.value.spec_fp1)
            if header is None:
                return invalid_input(
                    "experiment_ledger_ref",
                    "an ExperimentSpec with no resolvable Experiment Ledger is a "
                    "registration defect (CT-47; DEC-0308; FR-Q54)",
                    spec_fp1=spec.value.spec_fp1,
                )
            owner = ActorId.try_create(header[0])
            if is_refusal(owner):
                return owner
            restored_entries = tuple(entries_by_id.get(spec.value.spec_fp1, ()))
            owned_entries = tuple(
                ExperimentLedgerEntry(
                    authored_by=entry.authored_by,
                    owner=owner.value.value,
                    model_deployment_ref=entry.model_deployment_ref,
                    spec_fp1=entry.spec_fp1,
                    body=entry.body,
                    id=entry.id,
                    recorded_at=entry.recorded_at,
                )
                for entry in restored_entries
            )
            ledger = ExperimentLedger(
                experiment_id=spec.value.spec_fp1,
                owner=owner.value,
                registering_task_id=header[1],
                author_agent_id=header[2],
                ledger_ref=header[3],
                entries=owned_entries,
            )
            snapshots.append(
                ExperimentSqliteSnapshot(
                    spec=spec.value,
                    lease=lease.value,
                    ledger=ledger,
                    entry_seq=_entry_seq(spec.value.spec_fp1, owned_entries),
                    lineage_edge=edges_by_from.get(spec.value.spec_fp1),
                )
            )
        return Ok(tuple(snapshots))
