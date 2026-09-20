"""AD-26 Task Graph successor outbox — distinct from Story 41.4 RemoteOutbox.

Completing predecessor A and making successor B ready is one daemon-sqlite
transaction: persist A terminal, persist successor eligibility at a revision,
and write one outbox row per newly ready successor (FR-WF-46; SCN-0021).
Unique key is ``(graph_run_id, successor_node_id, predecessor_revision,
partition_id)``. Dispatch, acceptance, and effect stay distinct; the outbox
alone does not prove exactly-once effect. Receiver dedupe is on
``logical_invocation_id``.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.vocabulary.enums import TaskMissionState
from qma.daemon.taskgraph.records import TaskGraph, TaskRecord
from qmf.core import Ok, Result, fingerprint, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input

__all__ = [
    "DEFAULT_PARTITION_ID",
    "OUTBOXES_MERGED",
    "OUTBOX_PROVES_EXACTLY_ONCE_EFFECT",
    "OUTBOX_SCHEMA_SQL",
    "OUTBOX_UNIQUE_KEY_FIELDS",
    "REMOTE_WORKER_OUTBOX_NOUN",
    "TASK_GRAPH_ELIGIBILITY_TABLE",
    "TASK_GRAPH_OUTBOX_NOUN",
    "TASK_GRAPH_OUTBOX_TABLE",
    "TASK_GRAPH_RECEIVER_TABLE",
    "CompletionCrash",
    "OutboxAcceptanceState",
    "OutboxEffectState",
    "OutboxTransportState",
    "PredecessorCompletion",
    "ReceiverAcceptance",
    "SuccessorEligibility",
    "TaskGraphOutboxRow",
    "ack_outbox_dispatch",
    "apply_successor_eligibility",
    "build_outbox_row",
    "derive_logical_invocation_id",
    "derive_outbox_id",
    "envelope_hash_for",
    "load_eligibility_rows",
    "load_outbox_rows",
    "load_receiver_rows",
    "load_replayable_outbox_rows",
    "newly_ready_successors",
    "next_predecessor_revision",
    "parse_outbox_row",
    "refuse_merge_remote_worker_outbox",
    "replayable_outbox",
    "successor_target",
    "write_eligibility_rows",
    "write_outbox_rows",
    "write_receiver_row",
]


TASK_GRAPH_OUTBOX_NOUN: Final[str] = "task_graph_outbox"
REMOTE_WORKER_OUTBOX_NOUN: Final[str] = "remote_worker_outbox"
OUTBOXES_MERGED: Final[bool] = False
OUTBOX_PROVES_EXACTLY_ONCE_EFFECT: Final[bool] = False
DEFAULT_PARTITION_ID: Final[str] = "default"
TASK_GRAPH_OUTBOX_TABLE: Final[str] = "task_graph_outbox"
TASK_GRAPH_ELIGIBILITY_TABLE: Final[str] = "task_graph_successor_eligibility"
TASK_GRAPH_RECEIVER_TABLE: Final[str] = "task_graph_outbox_receiver"
OUTBOX_UNIQUE_KEY_FIELDS: Final[tuple[str, ...]] = (
    "graph_run_id",
    "successor_node_id",
    "predecessor_revision",
    "partition_id",
)
OUTBOX_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS task_graph_successor_eligibility (
    graph_run_id TEXT NOT NULL,
    successor_node_id TEXT NOT NULL,
    predecessor_node_id TEXT NOT NULL,
    predecessor_revision INTEGER NOT NULL,
    partition_id TEXT NOT NULL,
    PRIMARY KEY (
        graph_run_id, successor_node_id, predecessor_revision, partition_id
    )
);
CREATE TABLE IF NOT EXISTS task_graph_outbox (
    graph_run_id TEXT NOT NULL,
    successor_node_id TEXT NOT NULL,
    predecessor_revision INTEGER NOT NULL,
    partition_id TEXT NOT NULL,
    outbox_id TEXT NOT NULL,
    predecessor_node_id TEXT NOT NULL,
    logical_invocation_id TEXT NOT NULL,
    target TEXT NOT NULL,
    envelope_hash TEXT NOT NULL,
    transport_state TEXT NOT NULL,
    acceptance_state TEXT,
    effect_state TEXT,
    receiver_acceptance_id TEXT,
    PRIMARY KEY (
        graph_run_id, successor_node_id, predecessor_revision, partition_id
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS task_graph_outbox_logical
    ON task_graph_outbox (logical_invocation_id);
CREATE TABLE IF NOT EXISTS task_graph_outbox_receiver (
    logical_invocation_id TEXT PRIMARY KEY NOT NULL,
    receiver_acceptance_id TEXT NOT NULL,
    result_payload TEXT NOT NULL
);
"""

_CrashAfter = Literal["terminal", "eligibility", "outbox"]


class CompletionCrash(RuntimeError):
    """Raised inside the sqlite transaction to prove rollback (test seam)."""


class OutboxTransportState(StrEnum):
    """Closed transport states — dispatched is not accepted (FR-WF-47)."""

    PENDING = "pending"
    DISPATCHED = "dispatched"


class OutboxAcceptanceState(StrEnum):
    """Receiver-durable acceptance. Null means not accepted."""

    ACCEPTED = "accepted"


class OutboxEffectState(StrEnum):
    """Logical effect completion. Null means not effected."""

    EFFECTED = "effected"


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def refuse_merge_remote_worker_outbox(*, given: object = None) -> TypedRefusal:
    """Story 41.4 remote-worker outbox stays a different noun (FR-WF-46)."""
    context: dict[str, object] = {
        "field": "outbox",
        "reason": "Story 41.4 remote-worker outbox remains a different noun "
        "from the Task Graph successor outbox (FR-WF-46; AD-26)",
        "task_graph_outbox": TASK_GRAPH_OUTBOX_NOUN,
        "remote_worker_outbox": REMOTE_WORKER_OUTBOX_NOUN,
        "merged": OUTBOXES_MERGED,
        "outbox_proves_exactly_once_effect": OUTBOX_PROVES_EXACTLY_ONCE_EFFECT,
    }
    if given is not None:
        context["given"] = repr(given)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def derive_logical_invocation_id(
    *,
    graph_run_id: str,
    successor_node_id: str,
    predecessor_revision: int,
    partition_id: str,
) -> str:
    """Stable invocation identity for receiver dedupe (FR-WF-48)."""
    return f"inv:{graph_run_id}:{successor_node_id}:{predecessor_revision}:{partition_id}"


def derive_outbox_id(
    *,
    graph_run_id: str,
    successor_node_id: str,
    predecessor_revision: int,
    partition_id: str,
) -> str:
    return f"obx:{graph_run_id}:{successor_node_id}:{predecessor_revision}:{partition_id}"


def successor_target(
    task: TaskRecord,
    *,
    config_revision: int,
) -> dict[str, object]:
    """Complete dispatch target persisted on the outbox row (RC-07)."""
    op_raw = task.inputs.get("op_id")
    op_id = (
        op_raw
        if isinstance(op_raw, str) and op_raw
        else (
            f"taskgraph.node:{task.node_id}"
            if task.node_id is not None
            else f"taskgraph.task:{task.id}"
        )
    )
    version_raw = task.inputs.get("op_version", 1)
    op_version = (
        version_raw if isinstance(version_raw, int) and not isinstance(version_raw, bool) else 1
    )
    instance_raw = task.inputs.get("instance_id")
    instance_id = (
        instance_raw if isinstance(instance_raw, str) and instance_raw else f"inst:{task.id}"
    )
    return {
        "op_id": op_id,
        "op_version": op_version,
        "instance_id": instance_id,
        "config_revision": config_revision,
    }


def envelope_hash_for(
    *,
    logical_invocation_id: str,
    target: Mapping[str, object],
) -> Result[str]:
    hashed = fingerprint(
        {
            "logical_invocation_id": logical_invocation_id,
            "target": dict(target),
        }
    )
    if is_refusal(hashed):
        return hashed
    return Ok(hashed.value.value)


def newly_ready_successors(
    graph: TaskGraph,
    predecessor: TaskRecord,
) -> tuple[TaskRecord, ...]:
    """Successors that become eligible only once every predecessor is DONE."""
    if predecessor.state is not TaskMissionState.DONE or predecessor.node_id is None:
        return ()
    ready: list[TaskRecord] = []
    for successor_id in graph.successor_ids(predecessor.node_id):
        successor = graph.task_for_node(successor_id)
        if successor is None or successor.state is not TaskMissionState.PENDING:
            continue
        preds = graph.predecessor_ids(successor_id)
        if not preds:
            continue
        all_done = True
        for pred_id in preds:
            pred_task = graph.task_for_node(pred_id)
            if pred_task is None or pred_task.state is not TaskMissionState.DONE:
                all_done = False
                break
        if all_done:
            ready.append(successor)
    return tuple(ready)


def apply_successor_eligibility(
    graph: TaskGraph,
    *,
    predecessor: TaskRecord,
    ready: Sequence[TaskRecord],
) -> TaskGraph:
    """Persist A terminal and B ready on the in-memory graph snapshot."""
    ready_ids = {task.id for task in ready}
    tasks = tuple(
        task.with_state(TaskMissionState.READY) if task.id in ready_ids else task
        for task in graph.replace_task(predecessor).tasks
    )
    node_states: dict[str, TaskMissionState] = {}
    if predecessor.node_id is not None:
        node_states[predecessor.node_id] = predecessor.state
    for task in ready:
        if task.node_id is not None:
            node_states[task.node_id] = TaskMissionState.READY
    nodes = tuple(
        node.with_state(node_states[node.id]) if node.id in node_states else node
        for node in graph.nodes
    )
    return graph.replace_tasks(tasks).replace_nodes(nodes)


@dataclass(frozen=True, slots=True)
class SuccessorEligibility:
    """Successor eligibility recorded at a predecessor revision (FR-WF-46)."""

    graph_run_id: str
    successor_node_id: str
    predecessor_node_id: str
    predecessor_revision: int
    partition_id: str = DEFAULT_PARTITION_ID

    def unique_key(self) -> tuple[str, str, int, str]:
        return (
            self.graph_run_id,
            self.successor_node_id,
            self.predecessor_revision,
            self.partition_id,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "graph_run_id": self.graph_run_id,
                "successor_node_id": self.successor_node_id,
                "predecessor_node_id": self.predecessor_node_id,
                "predecessor_revision": self.predecessor_revision,
                "partition_id": self.partition_id,
            }
        )


@dataclass(frozen=True, slots=True)
class TaskGraphOutboxRow:
    """One successor outbox row. Transport ≠ acceptance ≠ effect (FR-WF-47)."""

    graph_run_id: str
    successor_node_id: str
    predecessor_revision: int
    partition_id: str
    outbox_id: str
    predecessor_node_id: str
    logical_invocation_id: str
    target: Mapping[str, object]
    envelope_hash: str
    transport_state: OutboxTransportState = OutboxTransportState.PENDING
    acceptance_state: OutboxAcceptanceState | None = None
    effect_state: OutboxEffectState | None = None
    receiver_acceptance_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target", MappingProxyType(dict(self.target)))

    def unique_key(self) -> tuple[str, str, int, str]:
        return (
            self.graph_run_id,
            self.successor_node_id,
            self.predecessor_revision,
            self.partition_id,
        )

    @property
    def replayable(self) -> bool:
        if self.transport_state is OutboxTransportState.PENDING:
            return True
        return (
            self.transport_state is OutboxTransportState.DISPATCHED
            and self.acceptance_state is None
        )

    def with_transport(self, state: OutboxTransportState) -> TaskGraphOutboxRow:
        return self._copy(transport_state=state)

    def with_acceptance(
        self,
        *,
        receiver_acceptance_id: str,
    ) -> TaskGraphOutboxRow:
        return self._copy(
            acceptance_state=OutboxAcceptanceState.ACCEPTED,
            receiver_acceptance_id=receiver_acceptance_id,
        )

    def with_effect(self) -> TaskGraphOutboxRow:
        return self._copy(effect_state=OutboxEffectState.EFFECTED)

    def _copy(
        self,
        *,
        transport_state: OutboxTransportState | None = None,
        acceptance_state: OutboxAcceptanceState | None = None,
        effect_state: OutboxEffectState | None = None,
        receiver_acceptance_id: str | None = None,
    ) -> TaskGraphOutboxRow:
        return TaskGraphOutboxRow(
            graph_run_id=self.graph_run_id,
            successor_node_id=self.successor_node_id,
            predecessor_revision=self.predecessor_revision,
            partition_id=self.partition_id,
            outbox_id=self.outbox_id,
            predecessor_node_id=self.predecessor_node_id,
            logical_invocation_id=self.logical_invocation_id,
            target=dict(self.target),
            envelope_hash=self.envelope_hash,
            transport_state=self.transport_state if transport_state is None else transport_state,
            acceptance_state=(
                self.acceptance_state if acceptance_state is None else acceptance_state
            ),
            effect_state=self.effect_state if effect_state is None else effect_state,
            receiver_acceptance_id=(
                self.receiver_acceptance_id
                if receiver_acceptance_id is None
                else receiver_acceptance_id
            ),
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "outbox_id": self.outbox_id,
                "graph_run_id": self.graph_run_id,
                "successor_node_id": self.successor_node_id,
                "predecessor_node_id": self.predecessor_node_id,
                "predecessor_revision": self.predecessor_revision,
                "partition_id": self.partition_id,
                "logical_invocation_id": self.logical_invocation_id,
                "target": dict(self.target),
                "envelope_hash": self.envelope_hash,
                "transport_state": self.transport_state.value,
                "acceptance_state": (
                    None if self.acceptance_state is None else self.acceptance_state.value
                ),
                "effect_state": None if self.effect_state is None else self.effect_state.value,
                "receiver_acceptance_id": self.receiver_acceptance_id,
                "outbox_proves_exactly_once_effect": OUTBOX_PROVES_EXACTLY_ONCE_EFFECT,
                "noun": TASK_GRAPH_OUTBOX_NOUN,
            }
        )


@dataclass(frozen=True, slots=True)
class ReceiverAcceptance:
    """Exactly-once logical acceptance under the receiver ledger (FR-WF-48)."""

    logical_invocation_id: str
    receiver_acceptance_id: str
    result: Mapping[str, object]
    replayed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", MappingProxyType(dict(self.result)))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "logical_invocation_id": self.logical_invocation_id,
                "receiver_acceptance_id": self.receiver_acceptance_id,
                "result": dict(self.result),
                "replayed": self.replayed,
            }
        )


@dataclass(frozen=True, slots=True)
class PredecessorCompletion:
    """Result of the one-transaction A-terminal / B-ready / outbox publish."""

    graph: TaskGraph
    predecessor: TaskRecord
    predecessor_revision: int
    ready_successors: tuple[TaskRecord, ...]
    eligibility: tuple[SuccessorEligibility, ...]
    outbox: tuple[TaskGraphOutboxRow, ...]


def build_outbox_row(
    *,
    graph: TaskGraph,
    predecessor: TaskRecord,
    successor: TaskRecord,
    predecessor_revision: int,
    partition_id: str = DEFAULT_PARTITION_ID,
) -> Result[TaskGraphOutboxRow]:
    if predecessor.node_id is None or successor.node_id is None:
        return _invalid(
            "node_id",
            "outbox rows require predecessor and successor node ids",
        )
    if not partition_id:
        return _invalid("partition_id", "outbox partition_id is required")
    target = successor_target(successor, config_revision=predecessor_revision)
    logical_id = derive_logical_invocation_id(
        graph_run_id=graph.id,
        successor_node_id=successor.node_id,
        predecessor_revision=predecessor_revision,
        partition_id=partition_id,
    )
    hashed = envelope_hash_for(logical_invocation_id=logical_id, target=target)
    if is_refusal(hashed):
        return hashed
    return Ok(
        TaskGraphOutboxRow(
            graph_run_id=graph.id,
            successor_node_id=successor.node_id,
            predecessor_revision=predecessor_revision,
            partition_id=partition_id,
            outbox_id=derive_outbox_id(
                graph_run_id=graph.id,
                successor_node_id=successor.node_id,
                predecessor_revision=predecessor_revision,
                partition_id=partition_id,
            ),
            predecessor_node_id=predecessor.node_id,
            logical_invocation_id=logical_id,
            target=target,
            envelope_hash=hashed.value,
        )
    )


def replayable_outbox(rows: Sequence[TaskGraphOutboxRow]) -> tuple[TaskGraphOutboxRow, ...]:
    """Unacked or dispatched-not-accepted rows (at-least-once dispatch)."""
    return tuple(row for row in rows if row.replayable)


def next_predecessor_revision(
    existing: Sequence[SuccessorEligibility | TaskGraphOutboxRow],
    *,
    graph_run_id: str,
    predecessor_node_id: str,
) -> int:
    current = 0
    for row in existing:
        if row.graph_run_id != graph_run_id:
            continue
        if row.predecessor_node_id != predecessor_node_id:
            continue
        current = max(current, row.predecessor_revision)
    return current + 1


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    return None


def parse_outbox_row(value: object) -> Result[TaskGraphOutboxRow]:
    if not isinstance(value, Mapping):
        return _invalid("outbox", "outbox row is a mapping")
    body = cast("Mapping[str, object]", value)
    graph_run_id = body.get("graph_run_id")
    successor_node_id = body.get("successor_node_id")
    predecessor_node_id = body.get("predecessor_node_id")
    partition_id = body.get("partition_id", DEFAULT_PARTITION_ID)
    revision_raw = body.get("predecessor_revision")
    if not isinstance(graph_run_id, str) or not graph_run_id:
        return _invalid("graph_run_id", "outbox requires graph_run_id")
    if not isinstance(successor_node_id, str) or not successor_node_id:
        return _invalid("successor_node_id", "outbox requires successor_node_id")
    if not isinstance(predecessor_node_id, str) or not predecessor_node_id:
        return _invalid("predecessor_node_id", "outbox requires predecessor_node_id")
    if not isinstance(partition_id, str) or not partition_id:
        return _invalid("partition_id", "outbox requires partition_id")
    if not isinstance(revision_raw, int) or isinstance(revision_raw, bool):
        return _invalid("predecessor_revision", "predecessor_revision is an int")
    target_raw = body.get("target")
    if isinstance(target_raw, str):
        try:
            loaded = json.loads(target_raw)
        except json.JSONDecodeError:
            return _invalid("target", "outbox target is JSON")
        target_raw = loaded
    if not isinstance(target_raw, Mapping):
        return _invalid("target", "outbox persists a complete target object")
    target = dict(cast("Mapping[str, object]", target_raw))
    for required in ("op_id", "op_version", "instance_id", "config_revision"):
        if required not in target:
            return _invalid("target", "outbox target is incomplete", missing=required)
    transport_raw = body.get("transport_state", OutboxTransportState.PENDING.value)
    try:
        transport = OutboxTransportState(str(transport_raw))
    except ValueError:
        return _invalid("transport_state", "transport_state is pending|dispatched")
    acceptance_raw = _as_optional_str(body.get("acceptance_state"))
    acceptance: OutboxAcceptanceState | None = None
    if acceptance_raw is not None:
        try:
            acceptance = OutboxAcceptanceState(acceptance_raw)
        except ValueError:
            return _invalid("acceptance_state", "acceptance_state is accepted or null")
    effect_raw = _as_optional_str(body.get("effect_state"))
    effect: OutboxEffectState | None = None
    if effect_raw is not None:
        try:
            effect = OutboxEffectState(effect_raw)
        except ValueError:
            return _invalid("effect_state", "effect_state is effected or null")
    logical_id = body.get("logical_invocation_id")
    if not isinstance(logical_id, str) or not logical_id:
        return _invalid("logical_invocation_id", "outbox requires logical_invocation_id")
    envelope_hash = body.get("envelope_hash")
    if not isinstance(envelope_hash, str) or not envelope_hash:
        return _invalid("envelope_hash", "outbox requires envelope_hash")
    outbox_id_raw = body.get("outbox_id")
    outbox_id = (
        outbox_id_raw
        if isinstance(outbox_id_raw, str) and outbox_id_raw
        else derive_outbox_id(
            graph_run_id=graph_run_id,
            successor_node_id=successor_node_id,
            predecessor_revision=revision_raw,
            partition_id=partition_id,
        )
    )
    return Ok(
        TaskGraphOutboxRow(
            graph_run_id=graph_run_id,
            successor_node_id=successor_node_id,
            predecessor_revision=revision_raw,
            partition_id=partition_id,
            outbox_id=outbox_id,
            predecessor_node_id=predecessor_node_id,
            logical_invocation_id=logical_id,
            target=target,
            envelope_hash=envelope_hash,
            transport_state=transport,
            acceptance_state=acceptance,
            effect_state=effect,
            receiver_acceptance_id=_as_optional_str(body.get("receiver_acceptance_id")),
        )
    )


def write_outbox_rows(conn: sqlite3.Connection, rows: Sequence[TaskGraphOutboxRow]) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO task_graph_outbox ("
        "graph_run_id, successor_node_id, predecessor_revision, partition_id, "
        "outbox_id, predecessor_node_id, logical_invocation_id, target, "
        "envelope_hash, transport_state, acceptance_state, effect_state, "
        "receiver_acceptance_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(
            (
                row.graph_run_id,
                row.successor_node_id,
                row.predecessor_revision,
                row.partition_id,
                row.outbox_id,
                row.predecessor_node_id,
                row.logical_invocation_id,
                _dump(row.target),
                row.envelope_hash,
                row.transport_state.value,
                None if row.acceptance_state is None else row.acceptance_state.value,
                None if row.effect_state is None else row.effect_state.value,
                row.receiver_acceptance_id,
            )
            for row in rows
        ),
    )


def write_eligibility_rows(
    conn: sqlite3.Connection,
    rows: Sequence[SuccessorEligibility],
) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO task_graph_successor_eligibility ("
        "graph_run_id, successor_node_id, predecessor_node_id, "
        "predecessor_revision, partition_id) VALUES (?, ?, ?, ?, ?)",
        tuple(
            (
                row.graph_run_id,
                row.successor_node_id,
                row.predecessor_node_id,
                row.predecessor_revision,
                row.partition_id,
            )
            for row in rows
        ),
    )


def write_receiver_row(conn: sqlite3.Connection, accepted: ReceiverAcceptance) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO task_graph_outbox_receiver ("
        "logical_invocation_id, receiver_acceptance_id, result_payload) "
        "VALUES (?, ?, ?)",
        (accepted.logical_invocation_id, accepted.receiver_acceptance_id, _dump(accepted.result)),
    )


def _load_outbox_query(
    conn: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...],
) -> Result[tuple[TaskGraphOutboxRow, ...]]:
    rows = conn.execute(sql, parameters).fetchall()
    parsed: list[TaskGraphOutboxRow] = []
    for raw in rows:
        item = parse_outbox_row(
            {
                "graph_run_id": raw[0],
                "successor_node_id": raw[1],
                "predecessor_revision": raw[2],
                "partition_id": raw[3],
                "outbox_id": raw[4],
                "predecessor_node_id": raw[5],
                "logical_invocation_id": raw[6],
                "target": raw[7],
                "envelope_hash": raw[8],
                "transport_state": raw[9],
                "acceptance_state": raw[10],
                "effect_state": raw[11],
                "receiver_acceptance_id": raw[12],
            }
        )
        if is_refusal(item):
            return item
        parsed.append(item.value)
    return Ok(tuple(parsed))


_OUTBOX_SELECT: Final[str] = (
    "SELECT graph_run_id, successor_node_id, predecessor_revision, partition_id, "
    "outbox_id, predecessor_node_id, logical_invocation_id, target, envelope_hash, "
    "transport_state, acceptance_state, effect_state, receiver_acceptance_id "
    "FROM task_graph_outbox"
)


def load_outbox_rows(
    conn: sqlite3.Connection,
    *,
    graph_run_id: str | None = None,
) -> Result[tuple[TaskGraphOutboxRow, ...]]:
    if graph_run_id is None:
        return _load_outbox_query(conn, _OUTBOX_SELECT + " ORDER BY outbox_id", ())
    return _load_outbox_query(
        conn,
        _OUTBOX_SELECT + " WHERE graph_run_id = ? ORDER BY outbox_id",
        (graph_run_id,),
    )


def load_replayable_outbox_rows(
    conn: sqlite3.Connection,
    *,
    graph_run_id: str | None = None,
) -> Result[tuple[TaskGraphOutboxRow, ...]]:
    clause = (
        " WHERE (transport_state = 'pending' OR "
        "(transport_state = 'dispatched' AND acceptance_state IS NULL))"
    )
    parameters: tuple[object, ...] = ()
    if graph_run_id is not None:
        clause += " AND graph_run_id = ?"
        parameters = (graph_run_id,)
    return _load_outbox_query(conn, _OUTBOX_SELECT + clause + " ORDER BY outbox_id", parameters)


def load_eligibility_rows(
    conn: sqlite3.Connection,
    *,
    graph_run_id: str | None = None,
) -> Result[tuple[SuccessorEligibility, ...]]:
    if graph_run_id is None:
        raw_rows = conn.execute(
            "SELECT graph_run_id, successor_node_id, predecessor_node_id, "
            "predecessor_revision, partition_id FROM task_graph_successor_eligibility "
            "ORDER BY graph_run_id, successor_node_id"
        ).fetchall()
    else:
        raw_rows = conn.execute(
            "SELECT graph_run_id, successor_node_id, predecessor_node_id, "
            "predecessor_revision, partition_id FROM task_graph_successor_eligibility "
            "WHERE graph_run_id = ? ORDER BY successor_node_id",
            (graph_run_id,),
        ).fetchall()
    rows: list[SuccessorEligibility] = []
    for raw in raw_rows:
        graph_id, successor_id, predecessor_id, revision, partition_id = raw
        if not isinstance(graph_id, str) or not isinstance(successor_id, str):
            return _invalid("eligibility", "eligibility ids are text")
        if not isinstance(predecessor_id, str) or not isinstance(partition_id, str):
            return _invalid("eligibility", "eligibility ids are text")
        if not isinstance(revision, int) or isinstance(revision, bool):
            return _invalid("predecessor_revision", "predecessor_revision is an int")
        rows.append(
            SuccessorEligibility(
                graph_run_id=graph_id,
                successor_node_id=successor_id,
                predecessor_node_id=predecessor_id,
                predecessor_revision=revision,
                partition_id=partition_id,
            )
        )
    return Ok(tuple(rows))


def load_receiver_rows(
    conn: sqlite3.Connection,
) -> Result[tuple[ReceiverAcceptance, ...]]:
    raw_rows = conn.execute(
        "SELECT logical_invocation_id, receiver_acceptance_id, result_payload "
        "FROM task_graph_outbox_receiver ORDER BY logical_invocation_id"
    ).fetchall()
    rows: list[ReceiverAcceptance] = []
    for raw in raw_rows:
        logical_id, acceptance_id, payload = raw
        if not isinstance(logical_id, str) or not isinstance(acceptance_id, str):
            return _invalid("receiver", "receiver ledger ids are text")
        if not isinstance(payload, str):
            return _invalid("receiver", "receiver result is JSON text")
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return _invalid("receiver", "receiver result is JSON")
        if not isinstance(loaded, dict):
            return _invalid("receiver", "receiver result is a JSON object")
        rows.append(
            ReceiverAcceptance(
                logical_invocation_id=logical_id,
                receiver_acceptance_id=acceptance_id,
                result=cast("dict[str, object]", loaded),
            )
        )
    return Ok(tuple(rows))


def ack_outbox_dispatch(
    conn: sqlite3.Connection,
    *,
    logical_invocation_id: str | None = None,
    graph_run_id: str | None = None,
    successor_node_id: str | None = None,
) -> int:
    """Mark matching pending rows dispatched. Does not record acceptance."""
    if logical_invocation_id is not None:
        cur = conn.execute(
            "UPDATE task_graph_outbox SET transport_state = ? "
            "WHERE logical_invocation_id = ? AND transport_state = ?",
            (
                OutboxTransportState.DISPATCHED.value,
                logical_invocation_id,
                OutboxTransportState.PENDING.value,
            ),
        )
        return int(cur.rowcount)
    if graph_run_id is not None and successor_node_id is not None:
        cur = conn.execute(
            "UPDATE task_graph_outbox SET transport_state = ? "
            "WHERE graph_run_id = ? AND successor_node_id = ? AND transport_state = ?",
            (
                OutboxTransportState.DISPATCHED.value,
                graph_run_id,
                successor_node_id,
                OutboxTransportState.PENDING.value,
            ),
        )
        return int(cur.rowcount)
    return 0


def maybe_crash(after: str | None, step: _CrashAfter) -> None:
    if after == step:
        raise CompletionCrash(f"injected crash after {step}")
