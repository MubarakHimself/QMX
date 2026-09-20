"""Named ``task_graph_state`` projection — durable edges in daemon sqlite.

Story 57.1 / FR-WF-45. The closed-list projection already exists (QMA AD-6);
this module materializes ``edges: {from, to, mapping}`` so successors can be
walked after restart. Occupancy is existing ``environment_lease`` plus
Workbench AD-8 door law folded into this projection — not a separate table.
QMB does not write daemon occupancy. RoutineScheduler / Mission Compiler
remain the procedure runtime; a second scheduler is refused. No sixth COMP.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import ActorId
from qma.core.ports.qmb import (
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    qmb_opens_daemon_sqlite,
)
from qma.core.vocabulary.enums import (
    EdgeMapping,
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)
from qma.daemon.envs.registry import EnvironmentLease
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.stores import StoreClass
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.daemon.taskgraph.outbox import (
    DEFAULT_PARTITION_ID,
    OUTBOX_SCHEMA_SQL,
    TASK_GRAPH_ELIGIBILITY_TABLE,
    TASK_GRAPH_OUTBOX_TABLE,
    TASK_GRAPH_RECEIVER_TABLE,
    CompletionCrash,
    OutboxAcceptanceState,
    OutboxEffectState,
    OutboxTransportState,
    PredecessorCompletion,
    ReceiverAcceptance,
    SuccessorEligibility,
    TaskGraphOutboxRow,
    ack_outbox_dispatch,
    apply_successor_eligibility,
    build_outbox_row,
    load_eligibility_rows,
    load_outbox_rows,
    load_receiver_rows,
    maybe_crash,
    newly_ready_successors,
    next_predecessor_revision,
    refuse_merge_remote_worker_outbox,
    replayable_outbox,
    write_eligibility_rows,
    write_outbox_rows,
    write_receiver_row,
)
from qma.daemon.taskgraph.records import (
    NODE_SUCCESSOR_KEYS,
    TaskGraph,
    TaskGraphEdge,
    TaskGraphNode,
    TaskLedger,
    TaskRecord,
)
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection, storage_failure

__all__ = [
    "DURABLE_EDGES_EXISTED_AT_INSPECT_SHA",
    "OCCUPANCY_TABLE",
    "OCCUPANCY_TABLE_MINTED",
    "PROCEDURE_RUNTIME",
    "QMB_WRITES_DAEMON_OCCUPANCY",
    "SECOND_SCHEDULER_MINTED",
    "TASK_GRAPH_STATE_EDGE_TABLE",
    "TASK_GRAPH_STATE_EXISTED_AT_INSPECT_SHA",
    "TASK_GRAPH_STATE_FOLD_ID",
    "TASK_GRAPH_STATE_INSPECT_SHAS",
    "TASK_GRAPH_STATE_OCCUPANCY_LAW",
    "TASK_GRAPH_STATE_SIXTH_COMP_MINTED",
    "TASK_GRAPH_STATE_SQLITE_TABLES",
    "TASK_GRAPH_STATE_STORE",
    "TASK_GRAPH_STATE_STORE_CLASS",
    "TASK_GRAPH_STATE_TABLE",
    "TaskGraphStateService",
    "TaskGraphStateSnapshot",
    "TaskGraphStateSqliteStore",
    "claim_durable_edges_at_inspect_sha",
    "empty_occupancy",
    "parse_task_graph_edge",
    "refuse_merge_remote_worker_outbox",
    "refuse_qmb_occupancy_write",
    "refuse_second_scheduler",
]


TASK_GRAPH_STATE_STORE: Final[str] = "task_graph_state"
TASK_GRAPH_STATE_FOLD_ID: Final[str] = "task_state"
TASK_GRAPH_STATE_TABLE: Final[str] = "task_graph_state"
TASK_GRAPH_STATE_EDGE_TABLE: Final[str] = "task_graph_state_edge"
TASK_GRAPH_STATE_STORE_CLASS: Final[str] = StoreClass.JOURNAL_DERIVED_PROJECTION.value
TASK_GRAPH_STATE_OCCUPANCY_LAW: Final[str] = "environment_lease+workbench_ad8"
TASK_GRAPH_STATE_INSPECT_SHAS: Final[tuple[str, ...]] = ("270e992",)
TASK_GRAPH_STATE_EXISTED_AT_INSPECT_SHA: Final[bool] = False
DURABLE_EDGES_EXISTED_AT_INSPECT_SHA: Final[bool] = False
TASK_GRAPH_STATE_SIXTH_COMP_MINTED: Final[bool] = False
OCCUPANCY_TABLE_MINTED: Final[bool] = False
OCCUPANCY_TABLE: Final[None] = None
QMB_WRITES_DAEMON_OCCUPANCY: Final[bool] = False
SECOND_SCHEDULER_MINTED: Final[bool] = False
PROCEDURE_RUNTIME: Final[tuple[str, ...]] = ("RoutineScheduler", "MissionCompiler")
TASK_GRAPH_STATE_SQLITE_TABLES: Final[frozenset[str]] = frozenset(
    {
        TASK_GRAPH_STATE_TABLE,
        TASK_GRAPH_STATE_EDGE_TABLE,
        TASK_GRAPH_OUTBOX_TABLE,
        TASK_GRAPH_ELIGIBILITY_TABLE,
        TASK_GRAPH_RECEIVER_TABLE,
    }
)
_MATERIALIZED_EVENT: Final[str] = "task.graph_materialized"
_PREDECESSOR_COMPLETED_EVENT: Final[str] = "task.predecessor_completed"
_OCCUPANCY_EVENT: Final[str] = "task.occupancy_recorded"
_OCCUPANCY_TABLE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "occupancy",
        "task_graph_occupancy",
        "task_graph_state_occupancy",
        "daemon_occupancy",
    }
)

_SCHEMA_SQL: Final[str] = (
    """
CREATE TABLE IF NOT EXISTS task_graph_state (
    graph_id TEXT PRIMARY KEY NOT NULL,
    mission_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    occupancy TEXT NOT NULL,
    journal_seq INTEGER NOT NULL,
    recorded_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS task_graph_state_edge (
    graph_id TEXT NOT NULL,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    mapping TEXT NOT NULL,
    PRIMARY KEY (graph_id, from_node, to_node)
);
CREATE INDEX IF NOT EXISTS task_graph_state_edge_from
    ON task_graph_state_edge (graph_id, from_node);
"""
    + OUTBOX_SCHEMA_SQL
)


def empty_occupancy() -> dict[str, object]:
    """Occupancy folded into ``task_graph_state`` — never a separate table."""
    return {
        "law": TASK_GRAPH_STATE_OCCUPANCY_LAW,
        "separate_table": False,
        "qmb_writes": False,
        "slots": {},
    }


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def _as_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _object_seq(value: object) -> tuple[object, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(cast("Sequence[object]", value))
    return ()


def refuse_second_scheduler(*, given: object = None) -> TypedRefusal:
    """A second scheduler is refused; AD-7 procedure runtime stands (FR-WF-45)."""
    context: dict[str, object] = {
        "field": "scheduler",
        "reason": "a second scheduler is refused; RoutineScheduler / Mission "
        "Compiler remain the procedure runtime (AD-7; FR-WF-45)",
        "minted": SECOND_SCHEDULER_MINTED,
        "runtime": list(PROCEDURE_RUNTIME),
        "sixth_comp": TASK_GRAPH_STATE_SIXTH_COMP_MINTED,
    }
    if given is not None:
        context["given"] = repr(given)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_qmb_occupancy_write(**extra: object) -> TypedRefusal:
    """QMB does not write daemon occupancy (FR-WF-51; Story 36.5)."""
    context: dict[str, object] = {
        "field": extra.pop("field", "occupancy"),
        "reason": "QMB does not write daemon occupancy; occupancy is "
        "environment_lease plus Workbench AD-8 door law folded into "
        "task_graph_state (FR-WF-51)",
        "qmb_writes": False,
        "qmb_opens_daemon_sqlite": qmb_opens_daemon_sqlite(),
        "separate_table": False,
        "store": TASK_GRAPH_STATE_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def claim_durable_edges_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming durable edges existed at 270e992 fails the story (DEC-0450)."""
    if existed is True or existed == "true":
        return policy_rejection(
            "task_graph_state",
            "durable Task Graph edges did not exist after restart at inspect "
            "SHA 270e992; the in-memory store dropped edges (DEC-0450; GAP-0095)",
            existed_at_inspect_sha=False,
            inspect_shas=list(TASK_GRAPH_STATE_INSPECT_SHAS),
        )
    if existed is not False:
        return invalid_input(
            "existed_at_inspect_sha",
            "claim must be the boolean false — class existence is not this story",
            given=repr(existed),
        )
    return Ok(False)


def parse_task_graph_edge(value: object) -> Result[TaskGraphEdge]:
    """Parse a persisted ``{from, to, mapping}`` edge."""
    if not isinstance(value, Mapping):
        return _invalid("edge", "persisted edge is a mapping {from, to, mapping}")
    body = cast("Mapping[str, object]", value)
    src = body.get("from", body.get("from_node"))
    dst = body.get("to", body.get("to_node"))
    mapping_raw = body.get("mapping")
    if not isinstance(src, str) or not src:
        return _invalid("edge.from", "persisted edge requires from")
    if not isinstance(dst, str) or not dst:
        return _invalid("edge.to", "persisted edge requires to")
    if not isinstance(mapping_raw, str):
        return _invalid("edge.mapping", "persisted edge requires mapping")
    try:
        mapping = EdgeMapping(mapping_raw)
    except ValueError:
        return _invalid(
            "edge.mapping",
            "edge mapping must be one of one|zip|broadcast|keyed-join|cartesian",
            given=mapping_raw,
        )
    return Ok(TaskGraphEdge(from_node=src, to_node=dst, mapping=mapping))


def _parse_node(value: object) -> Result[TaskGraphNode]:
    if not isinstance(value, Mapping):
        return _invalid("node", "persisted node is a mapping")
    body = cast("Mapping[str, object]", value)
    stolen = sorted(key for key in body if key in NODE_SUCCESSOR_KEYS)
    if stolen:
        return policy_rejection(
            "node",
            "Task Graph nodes do not carry successor lists (FR-WF-45)",
            fields=stolen,
        )
    node_id = body.get("id")
    kind_raw = body.get("kind")
    state_raw = body.get("state", TaskMissionState.PENDING.value)
    config_raw = body.get("config", {})
    if not isinstance(node_id, str) or not node_id:
        return _invalid("node.id", "persisted node requires id")
    if not isinstance(kind_raw, str):
        return _invalid("node.kind", "persisted node requires kind")
    if isinstance(config_raw, Mapping):
        config = dict(cast("Mapping[str, object]", config_raw))
    else:
        return _invalid("node.config", "persisted node config is a mapping")
    stolen_config = sorted(key for key in config if key in NODE_SUCCESSOR_KEYS)
    if stolen_config:
        return policy_rejection(
            "node",
            "Task Graph nodes do not carry successor lists (FR-WF-45)",
            node_id=node_id,
            fields=stolen_config,
        )
    try:
        kind = NodeKind(kind_raw)
        state = TaskMissionState(str(state_raw))
    except ValueError:
        return _invalid("node", "persisted node kind/state is closed vocabulary")
    return Ok(TaskGraphNode(id=node_id, kind=kind, state=state, config=config))


def _parse_ledger(task_id: str, value: object) -> Result[TaskLedger]:
    if value is None:
        return Ok(TaskLedger(task_id=task_id))
    if not isinstance(value, Mapping):
        return _invalid("ledger", "persisted ledger is a mapping")
    body = cast("Mapping[str, object]", value)
    entries_raw = body.get("entries", ())
    attempt_raw = body.get("attempt_no", 0)
    entries = tuple(
        dict(cast("Mapping[str, object]", item))
        for item in _object_seq(entries_raw)
        if isinstance(item, Mapping)
    )
    attempt = 0
    if isinstance(attempt_raw, int) and not isinstance(attempt_raw, bool):
        attempt = attempt_raw
    return Ok(TaskLedger(task_id=task_id, entries=entries, attempt_no=attempt))


def _parse_task(value: object) -> Result[TaskRecord]:
    if not isinstance(value, Mapping):
        return _invalid("task", "persisted task is a mapping")
    body = cast("Mapping[str, object]", value)
    task_id = body.get("id")
    mission_id = body.get("mission_id")
    intent = body.get("intent")
    if not isinstance(task_id, str) or not task_id:
        return _invalid("task.id", "persisted task requires id")
    if not isinstance(mission_id, str) or not mission_id:
        return _invalid("task.mission_id", "persisted task requires mission_id")
    if not isinstance(intent, str):
        return _invalid("task.intent", "persisted task requires intent")
    owner = ActorId.try_create(body.get("owner"))
    if is_refusal(owner):
        return owner
    inputs_raw = body.get("inputs", {})
    inputs: dict[str, object] = {}
    if isinstance(inputs_raw, Mapping):
        inputs = dict(cast("Mapping[str, object]", inputs_raw))
    refs_raw = body.get("refs", ())
    refs = tuple(str(item) for item in _object_seq(refs_raw))
    ac_raw = body.get("acceptance_criteria", ())
    acceptance = tuple(str(item) for item in _object_seq(ac_raw))
    try:
        state = TaskMissionState(str(body.get("state", TaskMissionState.PENDING.value)))
    except ValueError:
        return _invalid("task.state", "persisted task state is closed vocabulary")
    node_id_raw = body.get("node_id")
    node_id = node_id_raw if isinstance(node_id_raw, str) else None
    node_kind = None
    kind_raw = body.get("node_kind")
    if isinstance(kind_raw, str):
        try:
            node_kind = NodeKind(kind_raw)
        except ValueError:
            return _invalid("task.node_kind", "persisted node_kind is closed vocabulary")
    agent_role_raw = body.get("agent_role")
    worker_raw = body.get("worker_template_ref")
    ledger = _parse_ledger(task_id, body.get("ledger"))
    if is_refusal(ledger):
        return ledger
    iteration = body.get("iteration", 0)
    retry_index = body.get("retry_index", 0)
    attempt_of_raw = body.get("attempt_of")
    return Ok(
        TaskRecord(
            id=task_id,
            mission_id=mission_id,
            owner=owner.value,
            intent=intent,
            inputs=inputs,
            refs=refs,
            acceptance_criteria=acceptance,
            state=state,
            node_id=node_id,
            node_kind=node_kind,
            agent_role=agent_role_raw if isinstance(agent_role_raw, str) else None,
            worker_template_ref=worker_raw if isinstance(worker_raw, str) else None,
            iteration=_as_int(iteration),
            retry_index=_as_int(retry_index),
            attempt_of=attempt_of_raw if isinstance(attempt_of_raw, str) else None,
            ledger=ledger.value,
        )
    )


def parse_task_graph(
    value: object,
    *,
    edges: Sequence[TaskGraphEdge] | None = None,
) -> Result[TaskGraph]:
    """Rehydrate a Task Graph; ``edges`` table is the successor walk."""
    if not isinstance(value, Mapping):
        return _invalid("task_graph", "persisted task_graph_state payload is a mapping")
    body = cast("Mapping[str, object]", value)
    graph_id = body.get("id")
    mission_id = body.get("mission_id")
    if not isinstance(graph_id, str) or not graph_id:
        return _invalid("id", "persisted task_graph_state requires graph id")
    if not isinstance(mission_id, str) or not mission_id:
        return _invalid("mission_id", "persisted task_graph_state requires mission_id")
    nodes_raw = body.get("nodes", ())
    tasks_raw = body.get("tasks", ())
    nodes: list[TaskGraphNode] = []
    for item in _object_seq(nodes_raw):
        parsed = _parse_node(item)
        if is_refusal(parsed):
            return parsed
        nodes.append(parsed.value)
    tasks: list[TaskRecord] = []
    for item in _object_seq(tasks_raw):
        parsed_task = _parse_task(item)
        if is_refusal(parsed_task):
            return parsed_task
        tasks.append(parsed_task.value)
    resolved_edges: list[TaskGraphEdge] = []
    if edges is not None:
        resolved_edges.extend(edges)
    else:
        for item in _object_seq(body.get("edges", ())):
            parsed_edge = parse_task_graph_edge(item)
            if is_refusal(parsed_edge):
                return parsed_edge
            resolved_edges.append(parsed_edge.value)
    try:
        state = TaskMissionState(str(body.get("state", TaskMissionState.PENDING.value)))
    except ValueError:
        return _invalid("state", "persisted task_graph_state is closed vocabulary")
    template_raw = body.get("graph_template_ref")
    return Ok(
        TaskGraph(
            id=graph_id,
            mission_id=mission_id,
            nodes=tuple(nodes),
            tasks=tuple(tasks),
            edges=tuple(resolved_edges),
            artifact_kind=GraphArtifactKind.TASK_GRAPH,
            graph_template_ref=template_raw if isinstance(template_raw, str) else None,
            state=state,
        )
    )


def _parse_occupancy(value: object) -> Result[dict[str, object]]:
    if value is None:
        return Ok(empty_occupancy())
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            return storage_failure(
                f"task_graph_state occupancy is not JSON: {exc}",
                context={"field": "occupancy"},
            )
        value = parsed
    if not isinstance(value, Mapping):
        return _invalid("occupancy", "occupancy folded into task_graph_state is a mapping")
    body = dict(cast("Mapping[str, object]", value))
    body.setdefault("law", TASK_GRAPH_STATE_OCCUPANCY_LAW)
    body["separate_table"] = False
    body["qmb_writes"] = False
    slots = body.get("slots", {})
    if not isinstance(slots, Mapping):
        return _invalid("occupancy.slots", "occupancy slots are a mapping keyed by task id")
    body["slots"] = dict(cast("Mapping[str, object]", slots))
    return Ok(body)


@dataclass(frozen=True, slots=True)
class TaskGraphStateSnapshot:
    """One restored Task Graph plus occupancy folded into the projection."""

    graph: TaskGraph
    occupancy: Mapping[str, object]
    journal_seq: int
    recorded_at: int


def _write_graph_rows(
    conn: sqlite3.Connection,
    graph: TaskGraph,
    *,
    occupancy_json: str,
    payload: str,
    journal_seq: int,
    recorded_at: int,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO task_graph_state "
        "(graph_id, mission_id, payload, occupancy, journal_seq, recorded_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            graph.id,
            graph.mission_id,
            payload,
            occupancy_json,
            journal_seq,
            recorded_at,
        ),
    )
    conn.execute(
        "DELETE FROM task_graph_state_edge WHERE graph_id = ?",
        (graph.id,),
    )
    conn.executemany(
        "INSERT INTO task_graph_state_edge "
        "(graph_id, from_node, to_node, mapping) VALUES (?, ?, ?, ?)",
        tuple((graph.id, edge.from_node, edge.to_node, edge.mapping.value) for edge in graph.edges),
    )


class TaskGraphStateSqliteStore:
    """Sqlite fold for the named ``task_graph_state`` projection (NFR-WF-04)."""

    def __init__(self, sqlite: SingleSqliteWriter) -> None:
        self._sqlite = sqlite
        self._ensured = False
        self._crash_after: str | None = None

    def ensure_schema(self) -> None:
        if self._ensured:
            return

        def _ddl(conn: sqlite3.Connection) -> None:
            conn.executescript(_SCHEMA_SQL)

        self._sqlite.run(_ddl)
        self._ensured = True

    def table_names(self) -> frozenset[str]:
        self.ensure_schema()
        rows = self._sqlite.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return frozenset(str(row[0]) for row in rows)

    def occupancy_table_present(self) -> bool:
        return bool(self.table_names() & _OCCUPANCY_TABLE_NAMES)

    def put(
        self,
        graph: TaskGraph,
        *,
        occupancy: Mapping[str, object],
        journal_seq: int,
        recorded_at: int,
    ) -> None:
        self.ensure_schema()
        occupancy_json = _dump(occupancy)
        payload = _dump(graph.to_payload())

        def _write(conn: sqlite3.Connection) -> None:
            _write_graph_rows(
                conn,
                graph,
                occupancy_json=occupancy_json,
                payload=payload,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )

        self._sqlite.run(_write)

    def arm_completion_crash(self, after: str) -> None:
        """Test seam: raise inside the one sqlite completion transaction."""
        self._crash_after = after

    def put_completion(
        self,
        graph: TaskGraph,
        *,
        occupancy: Mapping[str, object],
        journal_seq: int,
        recorded_at: int,
        eligibility: Sequence[SuccessorEligibility],
        outbox: Sequence[TaskGraphOutboxRow],
    ) -> None:
        """One transaction: A terminal, B eligibility, outbox rows (FR-WF-46)."""
        self.ensure_schema()
        occupancy_json = _dump(occupancy)
        payload = _dump(graph.to_payload())
        crash_after = self._crash_after

        def _write(conn: sqlite3.Connection) -> None:
            _write_graph_rows(
                conn,
                graph,
                occupancy_json=occupancy_json,
                payload=payload,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
            maybe_crash(crash_after, "terminal")
            write_eligibility_rows(conn, eligibility)
            maybe_crash(crash_after, "eligibility")
            write_outbox_rows(conn, outbox)
            maybe_crash(crash_after, "outbox")

        try:
            self._sqlite.run(_write)
        finally:
            self._crash_after = None

    def load_edges(self, graph_id: str) -> Result[tuple[TaskGraphEdge, ...]]:
        self.ensure_schema()
        rows = self._sqlite.execute(
            "SELECT from_node, to_node, mapping FROM task_graph_state_edge "
            "WHERE graph_id = ? ORDER BY from_node, to_node",
            (graph_id,),
        )
        edges: list[TaskGraphEdge] = []
        for row in rows:
            parsed = parse_task_graph_edge({"from": row[0], "to": row[1], "mapping": row[2]})
            if is_refusal(parsed):
                return parsed
            edges.append(parsed.value)
        return Ok(tuple(edges))

    def get(self, graph_id: str) -> Result[TaskGraphStateSnapshot | None]:
        self.ensure_schema()
        rows = self._sqlite.execute(
            "SELECT payload, occupancy, journal_seq, recorded_at FROM task_graph_state "
            "WHERE graph_id = ?",
            (graph_id,),
        )
        if not rows:
            return Ok(None)
        raw_payload, raw_occupancy, journal_seq, recorded_at = rows[0]
        if not isinstance(raw_payload, str):
            return storage_failure(
                "task_graph_state sqlite payload is not JSON text",
                context={"field": "task_graph_state"},
            )
        try:
            parsed_payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            return storage_failure(
                f"task_graph_state sqlite payload is not JSON: {exc}",
                context={"field": "task_graph_state"},
            )
        if not isinstance(parsed_payload, dict):
            return _invalid("task_graph_state", "sqlite payload is a JSON object")
        edges = self.load_edges(graph_id)
        if is_refusal(edges):
            return edges
        graph = parse_task_graph(
            cast("dict[str, object]", parsed_payload),
            edges=edges.value,
        )
        if is_refusal(graph):
            return graph
        occupancy = _parse_occupancy(raw_occupancy)
        if is_refusal(occupancy):
            return occupancy
        seq = _as_int(journal_seq)
        recorded = _as_int(recorded_at)
        return Ok(
            TaskGraphStateSnapshot(
                graph=graph.value,
                occupancy=MappingProxyType(occupancy.value),
                journal_seq=seq,
                recorded_at=recorded,
            )
        )

    def load_all(self) -> Result[tuple[TaskGraphStateSnapshot, ...]]:
        self.ensure_schema()
        rows = self._sqlite.execute("SELECT graph_id FROM task_graph_state ORDER BY graph_id")
        snapshots: list[TaskGraphStateSnapshot] = []
        for row in rows:
            graph_id = row[0]
            if not isinstance(graph_id, str):
                return _invalid("graph_id", "task_graph_state graph_id is text")
            loaded = self.get(graph_id)
            if is_refusal(loaded):
                return loaded
            if loaded.value is not None:
                snapshots.append(loaded.value)
        return Ok(tuple(snapshots))


@dataclass
class TaskGraphStateService:
    """Persist Task Graph edges and the AD-26 successor outbox (Stories 57.1–57.2)."""

    journal: AuthoritativeJournal | None = None
    sqlite: SingleSqliteWriter | None = None
    _rows: dict[str, TaskGraph] = field(default_factory=dict[str, TaskGraph], init=False)
    _occupancy: dict[str, dict[str, object]] = field(
        default_factory=dict[str, dict[str, object]], init=False
    )
    _outbox: dict[tuple[str, str, int, str], TaskGraphOutboxRow] = field(
        default_factory=dict[tuple[str, str, int, str], TaskGraphOutboxRow],
        init=False,
    )
    _eligibility: dict[tuple[str, str, int, str], SuccessorEligibility] = field(
        default_factory=dict[tuple[str, str, int, str], SuccessorEligibility],
        init=False,
    )
    _receiver: dict[str, ReceiverAcceptance] = field(
        default_factory=dict[str, ReceiverAcceptance], init=False
    )
    _sqlite_store: TaskGraphStateSqliteStore | None = field(default=None, init=False)
    _restored: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.sqlite is not None:
            self._sqlite_store = TaskGraphStateSqliteStore(self.sqlite)
            self._sqlite_store.ensure_schema()

    @property
    def store(self) -> str:
        return TASK_GRAPH_STATE_STORE

    @property
    def fold_id(self) -> str:
        return TASK_GRAPH_STATE_FOLD_ID

    @property
    def product_truth(self) -> str:
        return "sqlite" if self._sqlite_store is not None else "memory"

    @property
    def occupancy_table_minted(self) -> bool:
        return OCCUPANCY_TABLE_MINTED

    @property
    def second_scheduler_minted(self) -> bool:
        return SECOND_SCHEDULER_MINTED

    @property
    def sixth_comp_minted(self) -> bool:
        return TASK_GRAPH_STATE_SIXTH_COMP_MINTED

    @property
    def existed_at_inspect_sha(self) -> bool:
        return DURABLE_EDGES_EXISTED_AT_INSPECT_SHA

    def bind_durable(
        self,
        *,
        sqlite: SingleSqliteWriter,
        journal: AuthoritativeJournal | None = None,
    ) -> Result[int]:
        """Attach the sole sqlite writer and restore graphs plus edges."""
        self.sqlite = sqlite
        self._sqlite_store = TaskGraphStateSqliteStore(sqlite)
        if journal is not None:
            self.journal = journal
        self._sqlite_store.ensure_schema()
        return self.reload()

    def drop_memory_cache(self) -> None:
        self._rows.clear()
        self._occupancy.clear()
        self._outbox.clear()
        self._eligibility.clear()
        self._receiver.clear()
        self._restored = False

    def reload(self) -> Result[int]:
        store = self._sqlite_store
        if store is None:
            return Ok(0)
        loaded = store.load_all()
        if is_refusal(loaded):
            return loaded
        self._rows = {}
        self._occupancy = {}
        for snapshot in loaded.value:
            self._rows[snapshot.graph.id] = snapshot.graph
            self._occupancy[snapshot.graph.id] = dict(snapshot.occupancy)
        restored = self._reload_outbox()
        if is_refusal(restored):
            return restored
        self._restored = True
        return Ok(len(loaded.value))

    def _reload_outbox(self) -> Result[None]:
        if self.sqlite is None or self._sqlite_store is None:
            return Ok(None)
        self._sqlite_store.ensure_schema()

        def _load(
            conn: sqlite3.Connection,
        ) -> Result[
            tuple[
                tuple[TaskGraphOutboxRow, ...],
                tuple[SuccessorEligibility, ...],
                tuple[ReceiverAcceptance, ...],
            ]
        ]:
            outbox = load_outbox_rows(conn)
            if is_refusal(outbox):
                return outbox
            eligibility = load_eligibility_rows(conn)
            if is_refusal(eligibility):
                return eligibility
            receiver = load_receiver_rows(conn)
            if is_refusal(receiver):
                return receiver
            return Ok((outbox.value, eligibility.value, receiver.value))

        loaded = self.sqlite.run(_load)
        if is_refusal(loaded):
            return loaded
        outbox_rows, eligibility_rows, receiver_rows = loaded.value
        self._outbox = {row.unique_key(): row for row in outbox_rows}
        self._eligibility = {row.unique_key(): row for row in eligibility_rows}
        self._receiver = {row.logical_invocation_id: row for row in receiver_rows}
        return Ok(None)

    def occupancy_table_present(self) -> bool:
        if self._sqlite_store is None:
            return False
        return self._sqlite_store.occupancy_table_present()

    def sqlite_table_names(self) -> frozenset[str]:
        if self._sqlite_store is None:
            return frozenset()
        return self._sqlite_store.table_names() & TASK_GRAPH_STATE_SQLITE_TABLES

    def _ensure_declared(self) -> Result[None]:
        journal = self.journal
        if journal is None:
            return Ok(None)
        declared = journal.declare_store(TASK_GRAPH_STATE_STORE)
        if is_refusal(declared):
            return declared
        folded = journal.register_fold(TASK_GRAPH_STATE_FOLD_ID)
        if is_refusal(folded):
            return folded
        return Ok(None)

    def occupancy_for(self, graph_id: str) -> Mapping[str, object]:
        return MappingProxyType(dict(self._occupancy.get(graph_id, empty_occupancy())))

    def persist(
        self,
        graph: TaskGraph,
        *,
        occupancy: Mapping[str, object] | None = None,
        scope_path: object = (),
    ) -> Result[TaskGraph]:
        """Write the graph and its edges into daemon sqlite."""
        stolen_nodes = [
            node.id
            for node in graph.nodes
            if any(key in NODE_SUCCESSOR_KEYS for key in node.config)
        ]
        if stolen_nodes:
            return policy_rejection(
                "node",
                "Task Graph nodes do not carry successor lists (FR-WF-45)",
                node_ids=stolen_nodes,
            )
        declared = self._ensure_declared()
        if is_refusal(declared):
            return declared
        occupancy_body = (
            dict(occupancy)
            if occupancy is not None
            else dict(self._occupancy.get(graph.id, empty_occupancy()))
        )
        occupancy_body["law"] = TASK_GRAPH_STATE_OCCUPANCY_LAW
        occupancy_body["separate_table"] = False
        occupancy_body["qmb_writes"] = False
        occupancy_body.setdefault("slots", {})
        journal_seq = 0
        recorded_at = 0
        if self.journal is not None:
            journal_payload: dict[str, object] = {
                "graph_id": graph.id,
                "mission_id": graph.mission_id,
                "state": graph.state.value,
                "edges": [dict(edge.to_payload()) for edge in graph.edges],
                "occupancy": occupancy_body,
            }
            if graph.graph_template_ref is not None:
                journal_payload["graph_template_ref"] = graph.graph_template_ref
            appended = self.journal.append_event(
                _MATERIALIZED_EVENT,
                scope_path=scope_path,
                payload=journal_payload,
            )
            if is_refusal(appended):
                return appended
            journal_seq = appended.value.record.journal_seq
            recorded_at = appended.value.record.recorded_at
        if self._sqlite_store is not None:
            self._sqlite_store.put(
                graph,
                occupancy=occupancy_body,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
        self._rows[graph.id] = graph
        self._occupancy[graph.id] = occupancy_body
        return Ok(graph)

    def arm_completion_crash(self, after: str) -> Result[None]:
        """Arm an in-transaction crash so tests can prove rollback (FR-WF-46)."""
        if self._sqlite_store is None:
            return policy_rejection(
                "outbox",
                "completion-crash injection requires daemon sqlite",
            )
        self._sqlite_store.arm_completion_crash(after)
        return Ok(None)

    def _occupancy_body(
        self,
        graph: TaskGraph,
        occupancy: Mapping[str, object] | None,
    ) -> dict[str, object]:
        occupancy_body = (
            dict(occupancy)
            if occupancy is not None
            else dict(self._occupancy.get(graph.id, empty_occupancy()))
        )
        occupancy_body["law"] = TASK_GRAPH_STATE_OCCUPANCY_LAW
        occupancy_body["separate_table"] = False
        occupancy_body["qmb_writes"] = False
        occupancy_body.setdefault("slots", {})
        return occupancy_body

    def complete_predecessor(
        self,
        graph: TaskGraph,
        predecessor: TaskRecord,
        *,
        partition_id: str = DEFAULT_PARTITION_ID,
        occupancy: Mapping[str, object] | None = None,
        scope_path: object = (),
    ) -> Result[PredecessorCompletion]:
        """One sqlite transaction: A terminal, B ready, outbox row (FR-WF-46)."""
        if not partition_id:
            return _invalid("partition_id", "outbox partition_id is required")
        declared = self._ensure_declared()
        if is_refusal(declared):
            return declared
        ready = newly_ready_successors(graph, predecessor)
        updated = apply_successor_eligibility(graph, predecessor=predecessor, ready=ready)
        revision = next_predecessor_revision(
            (*self._eligibility.values(), *self._outbox.values()),
            graph_run_id=graph.id,
            predecessor_node_id=predecessor.node_id or predecessor.id,
        )
        eligibility_rows: list[SuccessorEligibility] = []
        outbox_rows: list[TaskGraphOutboxRow] = []
        for successor in ready:
            if successor.node_id is None or predecessor.node_id is None:
                return _invalid(
                    "node_id",
                    "eligible successors require node ids on both ends",
                )
            eligibility_rows.append(
                SuccessorEligibility(
                    graph_run_id=graph.id,
                    successor_node_id=successor.node_id,
                    predecessor_node_id=predecessor.node_id,
                    predecessor_revision=revision,
                    partition_id=partition_id,
                )
            )
            built = build_outbox_row(
                graph=graph,
                predecessor=predecessor,
                successor=successor,
                predecessor_revision=revision,
                partition_id=partition_id,
            )
            if is_refusal(built):
                return built
            outbox_rows.append(built.value)
        occupancy_body = self._occupancy_body(updated, occupancy)
        journal_seq = 0
        recorded_at = 0
        if self.journal is not None:
            journal_payload: dict[str, object] = {
                "graph_id": updated.id,
                "predecessor_task_id": predecessor.id,
                "predecessor_state": predecessor.state.value,
                "predecessor_revision": revision,
                "ready_successor_ids": [task.id for task in ready],
                "outbox_keys": [list(row.unique_key()) for row in outbox_rows],
            }
            appended = self.journal.append_event(
                _PREDECESSOR_COMPLETED_EVENT,
                scope_path=scope_path,
                payload=journal_payload,
            )
            if is_refusal(appended):
                return appended
            journal_seq = appended.value.record.journal_seq
            recorded_at = appended.value.record.recorded_at
        if self._sqlite_store is not None:
            try:
                self._sqlite_store.put_completion(
                    updated,
                    occupancy=occupancy_body,
                    journal_seq=journal_seq,
                    recorded_at=recorded_at,
                    eligibility=eligibility_rows,
                    outbox=outbox_rows,
                )
            except CompletionCrash:
                return storage_failure(
                    "injected crash inside A-terminal/B-ready/outbox transaction",
                    context={
                        "field": "outbox",
                        "graph_id": graph.id,
                        "rolled_back": True,
                    },
                )
            reloaded = self._reload_outbox()
            if is_refusal(reloaded):
                return reloaded
        else:
            for row in eligibility_rows:
                self._eligibility[row.unique_key()] = row
            for row in outbox_rows:
                self._outbox[row.unique_key()] = row
        ready_updated = tuple(
            task for task in updated.tasks if task.id in {item.id for item in ready}
        )
        self._rows[updated.id] = updated
        self._occupancy[updated.id] = occupancy_body
        return Ok(
            PredecessorCompletion(
                graph=updated,
                predecessor=predecessor,
                predecessor_revision=revision,
                ready_successors=ready_updated,
                eligibility=tuple(eligibility_rows),
                outbox=tuple(outbox_rows),
            )
        )

    def outbox_rows(self, graph_run_id: str | None = None) -> tuple[TaskGraphOutboxRow, ...]:
        rows = tuple(self._outbox.values())
        if graph_run_id is None:
            return rows
        return tuple(row for row in rows if row.graph_run_id == graph_run_id)

    def eligibility_rows(self, graph_run_id: str | None = None) -> tuple[SuccessorEligibility, ...]:
        rows = tuple(self._eligibility.values())
        if graph_run_id is None:
            return rows
        return tuple(row for row in rows if row.graph_run_id == graph_run_id)

    def replayable_rows(self, graph_run_id: str | None = None) -> tuple[TaskGraphOutboxRow, ...]:
        return replayable_outbox(self.outbox_rows(graph_run_id))

    def ack_dispatch(
        self,
        *,
        graph_run_id: str | None = None,
        successor_node_id: str | None = None,
        logical_invocation_id: str | None = None,
    ) -> Result[tuple[TaskGraphOutboxRow, ...]]:
        """Ack transport dispatch. Does not record acceptance or effect."""
        if logical_invocation_id is None and (graph_run_id is None or successor_node_id is None):
            return _invalid(
                "outbox",
                "dispatch ack requires logical_invocation_id or graph_run_id+successor_node_id",
            )
        if self.sqlite is not None and self._sqlite_store is not None:
            self._sqlite_store.ensure_schema()

            def _ack(conn: sqlite3.Connection) -> int:
                return ack_outbox_dispatch(
                    conn,
                    logical_invocation_id=logical_invocation_id,
                    graph_run_id=graph_run_id,
                    successor_node_id=successor_node_id,
                )

            self.sqlite.run(_ack)
            reloaded = self._reload_outbox()
            if is_refusal(reloaded):
                return reloaded
        else:
            updated: dict[tuple[str, str, int, str], TaskGraphOutboxRow] = {}
            for key, row in self._outbox.items():
                match_logical = (
                    logical_invocation_id is None
                    or row.logical_invocation_id == logical_invocation_id
                )
                match_successor = successor_node_id is None or (
                    row.graph_run_id == graph_run_id and row.successor_node_id == successor_node_id
                )
                if (
                    match_logical
                    and match_successor
                    and row.transport_state is OutboxTransportState.PENDING
                ):
                    updated[key] = row.with_transport(OutboxTransportState.DISPATCHED)
            self._outbox.update(updated)
        if logical_invocation_id is not None:
            return Ok(
                tuple(
                    row
                    for row in self._outbox.values()
                    if row.logical_invocation_id == logical_invocation_id
                )
            )
        if graph_run_id is not None and successor_node_id is not None:
            return Ok(
                tuple(
                    row
                    for row in self._outbox.values()
                    if row.graph_run_id == graph_run_id
                    and row.successor_node_id == successor_node_id
                )
            )
        return Ok(self.replayable_rows(graph_run_id))

    def accept_logical(
        self,
        logical_invocation_id: str,
        *,
        result: Mapping[str, object] | None = None,
    ) -> Result[ReceiverAcceptance]:
        """Exactly-once logical acceptance under the receiver ledger (FR-WF-48)."""
        if not logical_invocation_id:
            return _invalid("logical_invocation_id", "receiver dedupe requires an id")
        prior = self._receiver.get(logical_invocation_id)
        if prior is not None:
            return Ok(
                ReceiverAcceptance(
                    logical_invocation_id=prior.logical_invocation_id,
                    receiver_acceptance_id=prior.receiver_acceptance_id,
                    result=dict(prior.result),
                    replayed=True,
                )
            )
        payload = dict(result) if result is not None else {"accepted": True}
        acceptance_id = f"recv:{logical_invocation_id}"
        accepted = ReceiverAcceptance(
            logical_invocation_id=logical_invocation_id,
            receiver_acceptance_id=acceptance_id,
            result=payload,
        )
        if self.sqlite is not None and self._sqlite_store is not None:
            self._sqlite_store.ensure_schema()

            def _accept(conn: sqlite3.Connection) -> None:
                write_receiver_row(conn, accepted)
                conn.execute(
                    "UPDATE task_graph_outbox SET acceptance_state = ?, "
                    "receiver_acceptance_id = ? WHERE logical_invocation_id = ?",
                    (
                        OutboxAcceptanceState.ACCEPTED.value,
                        acceptance_id,
                        logical_invocation_id,
                    ),
                )

            self.sqlite.run(_accept)
            reloaded = self._reload_outbox()
            if is_refusal(reloaded):
                return reloaded
            stored = self._receiver.get(logical_invocation_id)
            if stored is not None:
                return Ok(stored)
        self._receiver[logical_invocation_id] = accepted
        for key, row in list(self._outbox.items()):
            if row.logical_invocation_id == logical_invocation_id:
                self._outbox[key] = row.with_acceptance(receiver_acceptance_id=acceptance_id)
        return Ok(accepted)

    def mark_effected(self, logical_invocation_id: str) -> Result[TaskGraphOutboxRow]:
        """Record effect completion. The outbox still does not prove exactly-once."""
        if not logical_invocation_id:
            return _invalid("logical_invocation_id", "effect recording requires an id")
        if self.sqlite is not None and self._sqlite_store is not None:
            self._sqlite_store.ensure_schema()

            def _effect(conn: sqlite3.Connection) -> None:
                conn.execute(
                    "UPDATE task_graph_outbox SET effect_state = ? WHERE logical_invocation_id = ?",
                    (OutboxEffectState.EFFECTED.value, logical_invocation_id),
                )

            self.sqlite.run(_effect)
            reloaded = self._reload_outbox()
            if is_refusal(reloaded):
                return reloaded
        else:
            for key, row in list(self._outbox.items()):
                if row.logical_invocation_id == logical_invocation_id:
                    self._outbox[key] = row.with_effect()
        matched = tuple(
            row
            for row in self._outbox.values()
            if row.logical_invocation_id == logical_invocation_id
        )
        if not matched:
            return _invalid(
                "logical_invocation_id",
                "no outbox row for effect recording",
                given=logical_invocation_id,
            )
        return Ok(matched[0])

    def occupy_run_step(
        self,
        graph: TaskGraph,
        lease: EnvironmentLease,
        *,
        door: str = QMB_OCCUPANCY_RUN,
        scope_path: object = (),
    ) -> Result[TaskGraph]:
        """Fold ``environment_lease`` + AD-8 door law into ``task_graph_state``."""
        if door == QMB_OCCUPANCY_QUERY:
            slot: dict[str, object] = {
                "door": QMB_OCCUPANCY_QUERY,
                "consumes_environment": False,
            }
        else:
            if door != QMB_OCCUPANCY_RUN:
                return _invalid(
                    "occupancy",
                    "Workbench AD-8 door occupancy is run or query",
                    given=door,
                )
            slot = {
                "door": QMB_OCCUPANCY_RUN,
                "environment_lease": dict(lease.to_payload()),
                "consumes_environment": True,
            }
        occupancy = dict(self._occupancy.get(graph.id, empty_occupancy()))
        slots_raw = occupancy.get("slots", {})
        slots: dict[str, object] = {}
        if isinstance(slots_raw, Mapping):
            slots = dict(cast("Mapping[str, object]", slots_raw))
        slots[lease.task_id] = slot
        occupancy["slots"] = slots
        occupancy["law"] = TASK_GRAPH_STATE_OCCUPANCY_LAW
        occupancy["separate_table"] = False
        occupancy["qmb_writes"] = False
        if self.journal is not None:
            occupancy_payload: dict[str, object] = {
                "graph_id": graph.id,
                "task_id": lease.task_id,
                "door": slot["door"],
                "consumes_environment": slot["consumes_environment"],
            }
            lease_payload = slot.get("environment_lease")
            if isinstance(lease_payload, Mapping):
                occupancy_payload["environment_lease"] = dict(
                    cast("Mapping[str, object]", lease_payload)
                )
            appended = self.journal.append_event(
                _OCCUPANCY_EVENT,
                scope_path=scope_path,
                payload=occupancy_payload,
            )
            if is_refusal(appended):
                return appended
        return self.persist(graph, occupancy=occupancy, scope_path=scope_path)

    def write_qmb_occupancy(self, *_args: object, **kwargs: object) -> Result[None]:
        """Refused — QMB never writes daemon occupancy."""
        return refuse_qmb_occupancy_write(**kwargs)

    def mint_second_scheduler(self, given: object = None) -> Result[None]:
        """Refused — RoutineScheduler / Mission Compiler remain the runtime."""
        return refuse_second_scheduler(given=given)

    def get(self, graph_id: str) -> Result[TaskGraph]:
        cached = self._rows.get(graph_id)
        if cached is not None:
            return Ok(cached)
        if self._sqlite_store is not None:
            loaded = self._sqlite_store.get(graph_id)
            if is_refusal(loaded):
                return loaded
            if loaded.value is not None:
                self._rows[graph_id] = loaded.value.graph
                self._occupancy[graph_id] = dict(loaded.value.occupancy)
                return Ok(loaded.value.graph)
        return _invalid(
            "graph_id",
            "task_graph_state has no materialized graph",
            given=graph_id,
        )

    def snapshot(self, graph_id: str) -> Result[TaskGraphStateSnapshot]:
        cached = self._rows.get(graph_id)
        if cached is not None:
            occupancy = self._occupancy.get(graph_id, empty_occupancy())
            return Ok(
                TaskGraphStateSnapshot(
                    graph=cached,
                    occupancy=MappingProxyType(dict(occupancy)),
                    journal_seq=0,
                    recorded_at=0,
                )
            )
        if self._sqlite_store is None:
            return _invalid(
                "graph_id",
                "task_graph_state has no materialized graph",
                given=graph_id,
            )
        loaded = self._sqlite_store.get(graph_id)
        if is_refusal(loaded):
            return loaded
        if loaded.value is None:
            return _invalid(
                "graph_id",
                "task_graph_state has no materialized graph",
                given=graph_id,
            )
        return Ok(loaded.value)
