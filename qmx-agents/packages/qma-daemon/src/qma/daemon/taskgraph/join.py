"""AD-26 join algebra — JoinState bound to revisions and a total order.

JoinState is a typed ``task_graph_state`` record (RC-08; FR-WF-52). It is not
guessed from JSON shape. ``first-wins`` total order is
``(event_time, receive_time, source_event_id)``. Late arrival after watermark
is ``late`` with evidence, not silently merged. Partial retry of failed
partitions uses the same ``definition_revision`` + ``join_revision`` and reuses
successful partition ``result_identity`` values.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.vocabulary.enums import EdgeMapping
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "FIRST_WINS_ORDER",
    "JOIN_GUESSED_FROM_JSON_SHAPE",
    "JOIN_LATE_EVENT_TABLE",
    "JOIN_PARTITION_TABLE",
    "JOIN_SCHEMA_SQL",
    "JOIN_STATE_FIELDS",
    "JOIN_STATE_TABLE",
    "LATE_DISPOSITION",
    "DuplicateKeyPolicy",
    "JoinArrival",
    "JoinLateEvent",
    "JoinPartition",
    "JoinPartitionStatus",
    "JoinRetryPlan",
    "JoinState",
    "JoinWatermark",
    "WatermarkKind",
    "apply_join_arrival",
    "apply_retry_result",
    "close_join_watermark",
    "derive_join_id",
    "first_wins_key",
    "load_join_states",
    "open_join",
    "parse_join_state",
    "plan_partial_retry",
    "refuse_guessed_join_from_json",
    "write_join_state",
]


JOIN_STATE_TABLE: Final[str] = "task_graph_join_state"
JOIN_PARTITION_TABLE: Final[str] = "task_graph_join_partition"
JOIN_LATE_EVENT_TABLE: Final[str] = "task_graph_join_late_event"
JOIN_GUESSED_FROM_JSON_SHAPE: Final[bool] = False
LATE_DISPOSITION: Final[str] = "late"
FIRST_WINS_ORDER: Final[tuple[str, str, str]] = (
    "event_time",
    "receive_time",
    "source_event_id",
)
JOIN_STATE_FIELDS: Final[tuple[str, ...]] = (
    "join_id",
    "graph_run_id",
    "node_id",
    "edge_id",
    "definition_revision",
    "join_revision",
    "mapping",
    "expected_cardinality",
    "duplicate_key_policy",
    "first_wins_order",
    "watermark",
    "partitions",
    "late_events",
)
JOIN_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS task_graph_join_state (
    join_id TEXT PRIMARY KEY NOT NULL,
    graph_run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    definition_revision INTEGER NOT NULL,
    join_revision INTEGER NOT NULL,
    mapping TEXT NOT NULL,
    expected_cardinality INTEGER NOT NULL,
    duplicate_key_policy TEXT NOT NULL,
    first_wins_order TEXT NOT NULL,
    watermark_kind TEXT NOT NULL,
    watermark_cause TEXT,
    watermark_closed_at TEXT
);
CREATE TABLE IF NOT EXISTS task_graph_join_partition (
    join_id TEXT NOT NULL,
    partition_id TEXT NOT NULL,
    status TEXT NOT NULL,
    logical_invocation_id TEXT,
    source_event_id TEXT NOT NULL,
    event_time TEXT NOT NULL,
    receive_time TEXT NOT NULL,
    result_identity TEXT,
    PRIMARY KEY (join_id, partition_id)
);
CREATE TABLE IF NOT EXISTS task_graph_join_late_event (
    join_id TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    partition_id TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    disposition TEXT NOT NULL,
    PRIMARY KEY (join_id, source_event_id, partition_id, detected_at)
);
"""


class DuplicateKeyPolicy(StrEnum):
    """Keyed-join unique-key policy (AD-26; RC-08)."""

    REFUSE = "refuse"
    FIRST_WINS = "first-wins"


class WatermarkKind(StrEnum):
    """Closed watermark kinds that end merge eligibility (AD-26; FR-WF-52)."""

    ALL_EXPECTED = "all-expected"
    TIMEOUT = "timeout"
    FAILED_AGGREGATION = "failed-aggregation"


class JoinPartitionStatus(StrEnum):
    """Durable partition outcome recorded on JoinState."""

    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


def _dump(payload: Mapping[str, object] | Sequence[object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"guessed_from_json_shape": JOIN_GUESSED_FROM_JSON_SHAPE}
    context.update(extra)
    return invalid_input(field, reason, **context)


def _closed_enum[EnumT: StrEnum](
    enum_type: type[EnumT],
    value: object,
    field: str,
    *,
    reason: str,
) -> Result[EnumT]:
    if type(value) is enum_type:
        return Ok(value)
    try:
        return Ok(enum_type(str(value)))
    except ValueError:
        return _invalid(field, reason, given=repr(value))


def refuse_guessed_join_from_json(*, given: object = None) -> TypedRefusal:
    """JoinState is a typed record — JSON shape does not mint one (FR-WF-52)."""
    context: dict[str, object] = {
        "field": "join_state",
        "reason": "JoinState binds revisions, mapping, duplicate_key_policy, "
        "first_wins_order, watermark, partitions, and late_events; it is not "
        "guessed from JSON shape (FR-WF-52; RC-08)",
        "guessed_from_json_shape": JOIN_GUESSED_FROM_JSON_SHAPE,
        "required_fields": list(JOIN_STATE_FIELDS),
        "first_wins_order": list(FIRST_WINS_ORDER),
    }
    if given is not None:
        context["given"] = repr(given)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def derive_join_id(*, graph_run_id: str, node_id: str, edge_id: str) -> str:
    return f"join:{graph_run_id}:{node_id}:{edge_id}"


def _parse_instant(value: str, *, field: str) -> Result[datetime]:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _invalid(field, "join timestamps are ISO-8601 instants", given=value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return Ok(parsed.astimezone(UTC))


def first_wins_key(
    *,
    event_time: str,
    receive_time: str,
    source_event_id: str,
) -> Result[tuple[datetime, datetime, str]]:
    """Total order ``(event_time, receive_time, source_event_id)`` (RC-08)."""
    event = _parse_instant(event_time, field="event_time")
    if is_refusal(event):
        return event
    received = _parse_instant(receive_time, field="receive_time")
    if is_refusal(received):
        return received
    if not source_event_id:
        return _invalid("source_event_id", "first-wins order requires source_event_id")
    return Ok((event.value, received.value, source_event_id))


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    return None


def _require_str(body: Mapping[str, object], field: str) -> Result[str]:
    value = body.get(field)
    if not isinstance(value, str) or not value:
        return _invalid(field, f"JoinState requires {field}")
    return Ok(value)


def _require_revision(body: Mapping[str, object], field: str) -> Result[int]:
    value = body.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return _invalid(field, f"{field} is a positive int bound on the join definition")
    return Ok(value)


@dataclass(frozen=True, slots=True)
class JoinWatermark:
    """Declared watermark with persisted cause/time (AD-26; FR-WF-52)."""

    kind: WatermarkKind
    cause: str | None = None
    closed_at: str | None = None

    @property
    def closed(self) -> bool:
        return self.closed_at is not None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind.value,
                "cause": self.cause,
                "closed_at": self.closed_at,
            }
        )


@dataclass(frozen=True, slots=True)
class JoinPartition:
    """One durable partition row bound to a source event (RC-08)."""

    partition_id: str
    source_event_id: str
    event_time: str
    receive_time: str
    status: JoinPartitionStatus = JoinPartitionStatus.DONE
    logical_invocation_id: str | None = None
    result_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.partition_id:
            msg = "JoinPartition.partition_id is required"
            raise ValueError(msg)
        if not self.source_event_id:
            msg = "JoinPartition.source_event_id is required"
            raise ValueError(msg)
        if not self.event_time or not self.receive_time:
            msg = "JoinPartition requires event_time and receive_time"
            raise ValueError(msg)

    def first_wins_key(self) -> Result[tuple[datetime, datetime, str]]:
        return first_wins_key(
            event_time=self.event_time,
            receive_time=self.receive_time,
            source_event_id=self.source_event_id,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "partition_id": self.partition_id,
                "status": self.status.value,
                "logical_invocation_id": self.logical_invocation_id,
                "source_event_id": self.source_event_id,
                "event_time": self.event_time,
                "receive_time": self.receive_time,
                "result_identity": self.result_identity,
            }
        )


@dataclass(frozen=True, slots=True)
class JoinLateEvent:
    """Arrival after watermark — evidence, never a silent merge (FR-WF-52)."""

    source_event_id: str
    partition_id: str
    detected_at: str
    disposition: str = LATE_DISPOSITION

    def __post_init__(self) -> None:
        if not self.source_event_id:
            msg = "JoinLateEvent.source_event_id is required"
            raise ValueError(msg)
        if not self.partition_id:
            msg = "JoinLateEvent.partition_id is required"
            raise ValueError(msg)
        if not self.detected_at:
            msg = "JoinLateEvent.detected_at is required"
            raise ValueError(msg)
        if self.disposition != LATE_DISPOSITION:
            msg = "late arrival disposition is late, never a silent merge"
            raise ValueError(msg)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_event_id": self.source_event_id,
                "partition_id": self.partition_id,
                "detected_at": self.detected_at,
                "disposition": self.disposition,
            }
        )


@dataclass(frozen=True, slots=True)
class JoinArrival:
    """One partition event offered to the join algebra."""

    partition_id: str
    source_event_id: str
    event_time: str
    receive_time: str
    status: JoinPartitionStatus = JoinPartitionStatus.DONE
    logical_invocation_id: str | None = None
    result_identity: str | None = None

    def as_partition(self) -> JoinPartition:
        return JoinPartition(
            partition_id=self.partition_id,
            source_event_id=self.source_event_id,
            event_time=self.event_time,
            receive_time=self.receive_time,
            status=self.status,
            logical_invocation_id=self.logical_invocation_id,
            result_identity=self.result_identity,
        )


@dataclass(frozen=True, slots=True)
class JoinState:
    """Durable join algebra bound to graph/run/node/edge/definition/join revisions."""

    join_id: str
    graph_run_id: str
    node_id: str
    edge_id: str
    definition_revision: int
    join_revision: int
    mapping: EdgeMapping
    expected_cardinality: int
    duplicate_key_policy: DuplicateKeyPolicy
    watermark: JoinWatermark
    first_wins_order: tuple[str, str, str] = FIRST_WINS_ORDER
    partitions: tuple[JoinPartition, ...] = ()
    late_events: tuple[JoinLateEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.join_id or not self.graph_run_id or not self.node_id or not self.edge_id:
            msg = "JoinState requires join_id, graph_run_id, node_id, and edge_id"
            raise ValueError(msg)
        if self.definition_revision < 1 or self.join_revision < 1:
            msg = "JoinState definition_revision and join_revision are positive ints"
            raise ValueError(msg)
        if self.expected_cardinality < 1:
            msg = "JoinState.expected_cardinality is a positive int"
            raise ValueError(msg)
        if tuple(self.first_wins_order) != FIRST_WINS_ORDER:
            msg = (
                "first-wins total order is (event_time, receive_time, source_event_id) "
                "(FR-WF-52; RC-08)"
            )
            raise ValueError(msg)
        object.__setattr__(self, "first_wins_order", FIRST_WINS_ORDER)
        ordered = tuple(sorted(self.partitions, key=lambda item: item.partition_id))
        object.__setattr__(self, "partitions", ordered)

    @property
    def definition_key(self) -> tuple[int, int]:
        return (self.definition_revision, self.join_revision)

    def partition(self, partition_id: str) -> JoinPartition | None:
        for item in self.partitions:
            if item.partition_id == partition_id:
                return item
        return None

    def with_partitions(self, partitions: Sequence[JoinPartition]) -> JoinState:
        return self._copy(partitions=tuple(partitions), late_events=self.late_events)

    def with_late(self, event: JoinLateEvent) -> JoinState:
        return self._copy(partitions=self.partitions, late_events=(*self.late_events, event))

    def with_watermark(self, watermark: JoinWatermark) -> JoinState:
        return self._copy(
            partitions=self.partitions,
            late_events=self.late_events,
            watermark=watermark,
        )

    def _copy(
        self,
        *,
        partitions: tuple[JoinPartition, ...],
        late_events: tuple[JoinLateEvent, ...],
        watermark: JoinWatermark | None = None,
    ) -> JoinState:
        return JoinState(
            join_id=self.join_id,
            graph_run_id=self.graph_run_id,
            node_id=self.node_id,
            edge_id=self.edge_id,
            definition_revision=self.definition_revision,
            join_revision=self.join_revision,
            mapping=self.mapping,
            expected_cardinality=self.expected_cardinality,
            duplicate_key_policy=self.duplicate_key_policy,
            first_wins_order=FIRST_WINS_ORDER,
            watermark=self.watermark if watermark is None else watermark,
            partitions=partitions,
            late_events=late_events,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "join_id": self.join_id,
                "graph_run_id": self.graph_run_id,
                "node_id": self.node_id,
                "edge_id": self.edge_id,
                "definition_revision": self.definition_revision,
                "join_revision": self.join_revision,
                "mapping": self.mapping.value,
                "expected_cardinality": self.expected_cardinality,
                "duplicate_key_policy": self.duplicate_key_policy.value,
                "first_wins_order": list(self.first_wins_order),
                "watermark": dict(self.watermark.to_payload()),
                "partitions": [dict(item.to_payload()) for item in self.partitions],
                "late_events": [dict(item.to_payload()) for item in self.late_events],
                "guessed_from_json_shape": JOIN_GUESSED_FROM_JSON_SHAPE,
            }
        )


@dataclass(frozen=True, slots=True)
class JoinRetryPlan:
    """Partial retry of failed partitions under the same join definition."""

    join: JoinState
    definition_revision: int
    join_revision: int
    reinvoke_partition_ids: tuple[str, ...]
    reused_result_identities: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reused_result_identities",
            MappingProxyType(dict(self.reused_result_identities)),
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "join_id": self.join.join_id,
                "definition_revision": self.definition_revision,
                "join_revision": self.join_revision,
                "reinvoke_partition_ids": list(self.reinvoke_partition_ids),
                "reused_result_identities": dict(self.reused_result_identities),
            }
        )


def _parse_watermark(value: object) -> Result[JoinWatermark]:
    if not isinstance(value, Mapping):
        return _invalid("watermark", "watermark is {kind, cause, closed_at}")
    body = cast("Mapping[str, object]", value)
    kind_raw = body.get("kind")
    if not isinstance(kind_raw, str):
        return _invalid(
            "watermark.kind", "watermark.kind is all-expected|timeout|failed-aggregation"
        )
    try:
        kind = WatermarkKind(kind_raw)
    except ValueError:
        return _invalid(
            "watermark.kind",
            "watermark.kind is all-expected|timeout|failed-aggregation",
            given=kind_raw,
        )
    cause = _as_optional_str(body.get("cause"))
    closed_at = _as_optional_str(body.get("closed_at"))
    return Ok(JoinWatermark(kind=kind, cause=cause, closed_at=closed_at))


def _parse_partition(value: object) -> Result[JoinPartition]:
    if not isinstance(value, Mapping):
        return _invalid("partitions", "partition rows are mappings, not inferred JSON")
    body = cast("Mapping[str, object]", value)
    partition_id = body.get("partition_id")
    source_event_id = body.get("source_event_id")
    event_time = body.get("event_time")
    receive_time = body.get("receive_time")
    if not isinstance(partition_id, str) or not partition_id:
        return _invalid("partition_id", "partition requires partition_id")
    if not isinstance(source_event_id, str) or not source_event_id:
        return _invalid("source_event_id", "partition requires source_event_id")
    if not isinstance(event_time, str) or not event_time:
        return _invalid("event_time", "partition requires event_time")
    if not isinstance(receive_time, str) or not receive_time:
        return _invalid("receive_time", "partition requires receive_time")
    status_raw = body.get("status", JoinPartitionStatus.DONE.value)
    try:
        status = JoinPartitionStatus(str(status_raw))
    except ValueError:
        return _invalid("status", "partition status is pending|done|failed")
    keyed = first_wins_key(
        event_time=event_time,
        receive_time=receive_time,
        source_event_id=source_event_id,
    )
    if is_refusal(keyed):
        return keyed
    return Ok(
        JoinPartition(
            partition_id=partition_id,
            source_event_id=source_event_id,
            event_time=event_time,
            receive_time=receive_time,
            status=status,
            logical_invocation_id=_as_optional_str(body.get("logical_invocation_id")),
            result_identity=_as_optional_str(body.get("result_identity")),
        )
    )


def _parse_late_event(value: object) -> Result[JoinLateEvent]:
    if not isinstance(value, Mapping):
        return _invalid("late_events", "late events are mappings with evidence")
    body = cast("Mapping[str, object]", value)
    source_event_id = body.get("source_event_id")
    partition_id = body.get("partition_id")
    detected_at = body.get("detected_at")
    disposition = body.get("disposition", LATE_DISPOSITION)
    if not isinstance(source_event_id, str) or not source_event_id:
        return _invalid("late_events.source_event_id", "late event requires source_event_id")
    if not isinstance(partition_id, str) or not partition_id:
        return _invalid("late_events.partition_id", "late event requires partition_id")
    if not isinstance(detected_at, str) or not detected_at:
        return _invalid("late_events.detected_at", "late event requires detected_at")
    if disposition != LATE_DISPOSITION:
        return _invalid(
            "late_events.disposition",
            "late arrival after watermark is late with evidence, not silently merged",
            given=repr(disposition),
        )
    return Ok(
        JoinLateEvent(
            source_event_id=source_event_id,
            partition_id=partition_id,
            detected_at=detected_at,
            disposition=LATE_DISPOSITION,
        )
    )


def _parse_first_wins_order(value: object) -> Result[tuple[str, str, str]]:
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return _invalid("first_wins_order", "first_wins_order is the bound total-order tuple")
        value = loaded
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return _invalid(
            "first_wins_order", "first_wins_order is (event_time, receive_time, source_event_id)"
        )
    items = tuple(str(item) for item in cast("Sequence[object]", value))
    if items != FIRST_WINS_ORDER:
        return _invalid(
            "first_wins_order",
            "first-wins total order is (event_time, receive_time, source_event_id)",
            given=list(items),
            required=list(FIRST_WINS_ORDER),
        )
    return Ok(FIRST_WINS_ORDER)


def parse_join_state(value: object) -> Result[JoinState]:
    """Parse a typed JoinState. JSON shape without bound fields is refused."""
    if not isinstance(value, Mapping):
        return refuse_guessed_join_from_json(given=value)
    body = cast("Mapping[str, object]", value)
    missing = [name for name in JOIN_STATE_FIELDS if name not in body]
    if missing:
        return refuse_guessed_join_from_json(given={"missing": missing})
    join_id = _require_str(body, "join_id")
    if is_refusal(join_id):
        return join_id
    graph_run_id = _require_str(body, "graph_run_id")
    if is_refusal(graph_run_id):
        return graph_run_id
    node_id = _require_str(body, "node_id")
    if is_refusal(node_id):
        return node_id
    edge_id = _require_str(body, "edge_id")
    if is_refusal(edge_id):
        return edge_id
    definition_revision = _require_revision(body, "definition_revision")
    if is_refusal(definition_revision):
        return definition_revision
    join_revision = _require_revision(body, "join_revision")
    if is_refusal(join_revision):
        return join_revision
    mapping_raw = body.get("mapping")
    if not isinstance(mapping_raw, str):
        return refuse_guessed_join_from_json(given={"mapping": mapping_raw})
    try:
        mapping = EdgeMapping(mapping_raw)
    except ValueError:
        return _invalid("mapping", "join mapping is an AD-5 EdgeMapping member", given=mapping_raw)
    cardinality_raw = body.get("expected_cardinality")
    if (
        not isinstance(cardinality_raw, int)
        or isinstance(cardinality_raw, bool)
        or cardinality_raw < 1
    ):
        return _invalid("expected_cardinality", "expected_cardinality is a positive int")
    policy_raw = body.get("duplicate_key_policy")
    if not isinstance(policy_raw, str):
        return refuse_guessed_join_from_json(given={"duplicate_key_policy": policy_raw})
    try:
        policy = DuplicateKeyPolicy(policy_raw)
    except ValueError:
        return _invalid("duplicate_key_policy", "duplicate_key_policy is refuse|first-wins")
    order = _parse_first_wins_order(body.get("first_wins_order"))
    if is_refusal(order):
        return order
    watermark = _parse_watermark(body.get("watermark"))
    if is_refusal(watermark):
        return watermark
    partitions_raw = body.get("partitions")
    if not isinstance(partitions_raw, Sequence) or isinstance(partitions_raw, (str, bytes)):
        return _invalid("partitions", "partitions is a list of typed partition rows")
    partitions: list[JoinPartition] = []
    for item in cast("Sequence[object]", partitions_raw):
        parsed = _parse_partition(item)
        if is_refusal(parsed):
            return parsed
        partitions.append(parsed.value)
    late_raw = body.get("late_events")
    if not isinstance(late_raw, Sequence) or isinstance(late_raw, (str, bytes)):
        return _invalid("late_events", "late_events is a list of typed late-event rows")
    late_events: list[JoinLateEvent] = []
    for item in cast("Sequence[object]", late_raw):
        parsed_late = _parse_late_event(item)
        if is_refusal(parsed_late):
            return parsed_late
        late_events.append(parsed_late.value)
    return Ok(
        JoinState(
            join_id=join_id.value,
            graph_run_id=graph_run_id.value,
            node_id=node_id.value,
            edge_id=edge_id.value,
            definition_revision=definition_revision.value,
            join_revision=join_revision.value,
            mapping=mapping,
            expected_cardinality=cardinality_raw,
            duplicate_key_policy=policy,
            first_wins_order=order.value,
            watermark=watermark.value,
            partitions=tuple(partitions),
            late_events=tuple(late_events),
        )
    )


def open_join(
    *,
    graph_run_id: str,
    node_id: str,
    edge_id: str,
    definition_revision: int,
    join_revision: int,
    mapping: EdgeMapping | str,
    expected_cardinality: int,
    duplicate_key_policy: DuplicateKeyPolicy | str,
    watermark_kind: WatermarkKind | str = WatermarkKind.ALL_EXPECTED,
    join_id: str | None = None,
) -> Result[JoinState]:
    """Mint a typed JoinState. Mapping and policy are declared, never guessed."""
    resolved_mapping = _closed_enum(
        EdgeMapping,
        mapping,
        "mapping",
        reason="join mapping is an AD-5 EdgeMapping member",
    )
    if is_refusal(resolved_mapping):
        return resolved_mapping
    resolved_policy = _closed_enum(
        DuplicateKeyPolicy,
        duplicate_key_policy,
        "duplicate_key_policy",
        reason="duplicate_key_policy is refuse|first-wins",
    )
    if is_refusal(resolved_policy):
        return resolved_policy
    resolved_kind = _closed_enum(
        WatermarkKind,
        watermark_kind,
        "watermark.kind",
        reason="watermark.kind is closed vocabulary",
    )
    if is_refusal(resolved_kind):
        return resolved_kind
    payload = {
        "join_id": join_id
        or derive_join_id(graph_run_id=graph_run_id, node_id=node_id, edge_id=edge_id),
        "graph_run_id": graph_run_id,
        "node_id": node_id,
        "edge_id": edge_id,
        "definition_revision": definition_revision,
        "join_revision": join_revision,
        "mapping": resolved_mapping.value.value,
        "expected_cardinality": expected_cardinality,
        "duplicate_key_policy": resolved_policy.value.value,
        "first_wins_order": list(FIRST_WINS_ORDER),
        "watermark": {"kind": resolved_kind.value.value, "cause": None, "closed_at": None},
        "partitions": [],
        "late_events": [],
    }
    return parse_join_state(payload)


def _maybe_close_all_expected(state: JoinState) -> Result[JoinState]:
    if state.watermark.kind is not WatermarkKind.ALL_EXPECTED or state.watermark.closed:
        return Ok(state)
    if len(state.partitions) < state.expected_cardinality:
        return Ok(state)
    latest: str | None = None
    latest_key: datetime | None = None
    for item in state.partitions:
        parsed = _parse_instant(item.receive_time, field="receive_time")
        if is_refusal(parsed):
            return parsed
        if latest_key is None or parsed.value >= latest_key:
            latest_key = parsed.value
            latest = item.receive_time
    if latest is None:
        return Ok(state)
    return Ok(
        state.with_watermark(
            JoinWatermark(kind=WatermarkKind.ALL_EXPECTED, cause=None, closed_at=latest)
        )
    )


def apply_join_arrival(
    state: JoinState,
    arrival: JoinArrival,
    *,
    detected_at: str | None = None,
) -> Result[JoinState]:
    """Apply one arrival under first-wins / refuse and the closed watermark."""
    incoming_key = first_wins_key(
        event_time=arrival.event_time,
        receive_time=arrival.receive_time,
        source_event_id=arrival.source_event_id,
    )
    if is_refusal(incoming_key):
        return incoming_key
    stamp = detected_at if detected_at is not None else arrival.receive_time
    if state.watermark.closed:
        return Ok(
            state.with_late(
                JoinLateEvent(
                    source_event_id=arrival.source_event_id,
                    partition_id=arrival.partition_id,
                    detected_at=stamp,
                    disposition=LATE_DISPOSITION,
                )
            )
        )
    existing = state.partition(arrival.partition_id)
    if existing is None:
        updated = state.with_partitions((*state.partitions, arrival.as_partition()))
        return _maybe_close_all_expected(updated)
    if existing.source_event_id == arrival.source_event_id:
        return Ok(state)
    if state.duplicate_key_policy is DuplicateKeyPolicy.REFUSE:
        return policy_rejection(
            "duplicate_key_policy",
            "keyed-join unique key already bound; duplicate_key_policy is refuse",
            join_id=state.join_id,
            partition_id=arrival.partition_id,
            bound_source_event_id=existing.source_event_id,
            given_source_event_id=arrival.source_event_id,
        )
    existing_key = existing.first_wins_key()
    if is_refusal(existing_key):
        return existing_key
    if incoming_key.value < existing_key.value:
        replaced = tuple(
            arrival.as_partition() if item.partition_id == arrival.partition_id else item
            for item in state.partitions
        )
        return Ok(state.with_partitions(replaced))
    return Ok(state)


def close_join_watermark(
    state: JoinState,
    *,
    kind: WatermarkKind | str,
    closed_at: str,
    cause: str | None = None,
) -> Result[JoinState]:
    """Persist watermark close. Further arrivals become late evidence."""
    resolved_kind = _closed_enum(
        WatermarkKind,
        kind,
        "watermark.kind",
        reason="watermark.kind is closed vocabulary",
    )
    if is_refusal(resolved_kind):
        return resolved_kind
    parsed = _parse_instant(closed_at, field="watermark.closed_at")
    if is_refusal(parsed):
        return parsed
    if state.watermark.closed:
        return Ok(state)
    return Ok(
        state.with_watermark(
            JoinWatermark(kind=resolved_kind.value, cause=cause, closed_at=closed_at)
        )
    )


def plan_partial_retry(
    state: JoinState,
    *,
    definition_revision: int,
    join_revision: int,
) -> Result[JoinRetryPlan]:
    """Re-invoke only failed partitions under the same join definition."""
    if state.definition_revision != definition_revision or state.join_revision != join_revision:
        return policy_rejection(
            "join_revision",
            "partial retry uses the same join definition "
            "(definition_revision + join_revision) (FR-WF-52; RC-08)",
            join_id=state.join_id,
            bound_definition_revision=state.definition_revision,
            bound_join_revision=state.join_revision,
            given_definition_revision=definition_revision,
            given_join_revision=join_revision,
        )
    reinvoke = tuple(
        item.partition_id for item in state.partitions if item.status is JoinPartitionStatus.FAILED
    )
    reused = {
        item.partition_id: item.result_identity
        for item in state.partitions
        if item.status is JoinPartitionStatus.DONE and item.result_identity is not None
    }
    return Ok(
        JoinRetryPlan(
            join=state,
            definition_revision=definition_revision,
            join_revision=join_revision,
            reinvoke_partition_ids=reinvoke,
            reused_result_identities=reused,
        )
    )


def apply_retry_result(
    state: JoinState,
    *,
    partition_id: str,
    result_identity: str,
    definition_revision: int,
    join_revision: int,
    source_event_id: str | None = None,
    event_time: str | None = None,
    receive_time: str | None = None,
    logical_invocation_id: str | None = None,
) -> Result[JoinState]:
    """Record a failed-partition retry without rewriting successful identities."""
    planned = plan_partial_retry(
        state,
        definition_revision=definition_revision,
        join_revision=join_revision,
    )
    if is_refusal(planned):
        return planned
    if partition_id not in planned.value.reinvoke_partition_ids:
        return _invalid(
            "partition_id",
            "retry result applies only to failed partitions of this join definition",
            partition_id=partition_id,
            reinvoke_partition_ids=list(planned.value.reinvoke_partition_ids),
        )
    if not result_identity:
        return _invalid("result_identity", "retry result requires result_identity")
    current = state.partition(partition_id)
    if current is None:
        return _invalid("partition_id", "unknown join partition", given=partition_id)
    updated = JoinPartition(
        partition_id=current.partition_id,
        source_event_id=source_event_id or current.source_event_id,
        event_time=event_time or current.event_time,
        receive_time=receive_time or current.receive_time,
        status=JoinPartitionStatus.DONE,
        logical_invocation_id=logical_invocation_id or current.logical_invocation_id,
        result_identity=result_identity,
    )
    partitions = tuple(
        updated if item.partition_id == partition_id else item for item in state.partitions
    )
    for item in partitions:
        if item.status is JoinPartitionStatus.DONE and item.partition_id != partition_id:
            prior = planned.value.reused_result_identities.get(item.partition_id)
            if prior is not None and item.result_identity != prior:
                return policy_rejection(
                    "result_identity",
                    "successful partition result_identity values are reused on retry",
                    partition_id=item.partition_id,
                )
    return Ok(state.with_partitions(partitions))


def write_join_state(conn: sqlite3.Connection, state: JoinState) -> None:
    conn.execute("DELETE FROM task_graph_join_late_event WHERE join_id = ?", (state.join_id,))
    conn.execute("DELETE FROM task_graph_join_partition WHERE join_id = ?", (state.join_id,))
    conn.execute("DELETE FROM task_graph_join_state WHERE join_id = ?", (state.join_id,))
    conn.execute(
        "INSERT INTO task_graph_join_state ("
        "join_id, graph_run_id, node_id, edge_id, definition_revision, join_revision, "
        "mapping, expected_cardinality, duplicate_key_policy, first_wins_order, "
        "watermark_kind, watermark_cause, watermark_closed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            state.join_id,
            state.graph_run_id,
            state.node_id,
            state.edge_id,
            state.definition_revision,
            state.join_revision,
            state.mapping.value,
            state.expected_cardinality,
            state.duplicate_key_policy.value,
            _dump(list(state.first_wins_order)),
            state.watermark.kind.value,
            state.watermark.cause,
            state.watermark.closed_at,
        ),
    )
    conn.executemany(
        "INSERT INTO task_graph_join_partition ("
        "join_id, partition_id, status, logical_invocation_id, source_event_id, "
        "event_time, receive_time, result_identity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(
            (
                state.join_id,
                item.partition_id,
                item.status.value,
                item.logical_invocation_id,
                item.source_event_id,
                item.event_time,
                item.receive_time,
                item.result_identity,
            )
            for item in state.partitions
        ),
    )
    conn.executemany(
        "INSERT INTO task_graph_join_late_event ("
        "join_id, source_event_id, partition_id, detected_at, disposition) "
        "VALUES (?, ?, ?, ?, ?)",
        tuple(
            (
                state.join_id,
                item.source_event_id,
                item.partition_id,
                item.detected_at,
                item.disposition,
            )
            for item in state.late_events
        ),
    )


def load_join_states(
    conn: sqlite3.Connection,
    *,
    graph_run_id: str | None = None,
) -> Result[tuple[JoinState, ...]]:
    if graph_run_id is None:
        headers = conn.execute(
            "SELECT join_id, graph_run_id, node_id, edge_id, definition_revision, "
            "join_revision, mapping, expected_cardinality, duplicate_key_policy, "
            "first_wins_order, watermark_kind, watermark_cause, watermark_closed_at "
            "FROM task_graph_join_state ORDER BY join_id"
        ).fetchall()
    else:
        headers = conn.execute(
            "SELECT join_id, graph_run_id, node_id, edge_id, definition_revision, "
            "join_revision, mapping, expected_cardinality, duplicate_key_policy, "
            "first_wins_order, watermark_kind, watermark_cause, watermark_closed_at "
            "FROM task_graph_join_state WHERE graph_run_id = ? ORDER BY join_id",
            (graph_run_id,),
        ).fetchall()
    loaded: list[JoinState] = []
    for header in headers:
        join_id = header[0]
        if not isinstance(join_id, str):
            return _invalid("join_id", "join_id is text")
        partition_rows = conn.execute(
            "SELECT partition_id, status, logical_invocation_id, source_event_id, "
            "event_time, receive_time, result_identity FROM task_graph_join_partition "
            "WHERE join_id = ? ORDER BY partition_id",
            (join_id,),
        ).fetchall()
        late_rows = conn.execute(
            "SELECT source_event_id, partition_id, detected_at, disposition "
            "FROM task_graph_join_late_event WHERE join_id = ? "
            "ORDER BY detected_at, source_event_id",
            (join_id,),
        ).fetchall()
        parsed = parse_join_state(
            {
                "join_id": header[0],
                "graph_run_id": header[1],
                "node_id": header[2],
                "edge_id": header[3],
                "definition_revision": header[4],
                "join_revision": header[5],
                "mapping": header[6],
                "expected_cardinality": header[7],
                "duplicate_key_policy": header[8],
                "first_wins_order": header[9],
                "watermark": {
                    "kind": header[10],
                    "cause": header[11],
                    "closed_at": header[12],
                },
                "partitions": [
                    {
                        "partition_id": row[0],
                        "status": row[1],
                        "logical_invocation_id": row[2],
                        "source_event_id": row[3],
                        "event_time": row[4],
                        "receive_time": row[5],
                        "result_identity": row[6],
                    }
                    for row in partition_rows
                ],
                "late_events": [
                    {
                        "source_event_id": row[0],
                        "partition_id": row[1],
                        "detected_at": row[2],
                        "disposition": row[3],
                    }
                    for row in late_rows
                ],
            }
        )
        if is_refusal(parsed):
            return parsed
        loaded.append(parsed.value)
    return Ok(tuple(loaded))
