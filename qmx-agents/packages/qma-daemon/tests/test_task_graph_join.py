"""Story 57.4 — join algebra bound to revisions and a total order."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.vocabulary.enums import EdgeMapping
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph import (
    FIRST_WINS_ORDER,
    JOIN_GUESSED_FROM_JSON_SHAPE,
    JOIN_LATE_EVENT_TABLE,
    JOIN_PARTITION_TABLE,
    JOIN_STATE_FIELDS,
    JOIN_STATE_TABLE,
    DuplicateKeyPolicy,
    JoinArrival,
    JoinPartition,
    JoinPartitionStatus,
    JoinState,
    WatermarkKind,
    parse_join_state,
    refuse_guessed_join_from_json,
)
from qmf.core import is_ok, is_refusal

_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "taskgraph"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "task_graph_join_usage.py"


def _compose(tmp_path: Path, *, boot: str) -> DaemonProcess:
    seed = tmp_path / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(result), result
    return result.value


def _open_join(
    process: DaemonProcess,
    *,
    cardinality: int = 2,
    policy: DuplicateKeyPolicy = DuplicateKeyPolicy.FIRST_WINS,
    graph_run_id: str = "tg:join-run",
) -> JoinState:
    opened = process.task_graphs.open_join(
        graph_run_id=graph_run_id,
        node_id="nJoin",
        edge_id="eA-Join",
        definition_revision=3,
        join_revision=1,
        mapping=EdgeMapping.KEYED_JOIN,
        expected_cardinality=cardinality,
        duplicate_key_policy=policy,
    )
    assert is_ok(opened), opened
    return opened.value


def _partition(state: JoinState, partition_id: str) -> JoinPartition:
    item = state.partition(partition_id)
    assert item is not None
    return item


def test_join_state_persists_bound_fields_not_json_shape(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-57-4-fields")
    try:
        names = process.sqlite_table_names()
        assert JOIN_STATE_TABLE in names
        assert JOIN_PARTITION_TABLE in names
        assert JOIN_LATE_EVENT_TABLE in names
        tables = process.snapshot()["task_graph_state_tables"]
        assert JOIN_STATE_TABLE in cast("list[str]", tables)
        state = _open_join(process, cardinality=2)
        payload = dict(state.to_payload())
        assert set(JOIN_STATE_FIELDS) <= set(payload)
        join_id = payload["join_id"]
        assert isinstance(join_id, str)
        assert join_id.startswith("join:")
        assert payload["graph_run_id"] == "tg:join-run"
        assert payload["node_id"] == "nJoin"
        assert payload["edge_id"] == "eA-Join"
        assert payload["definition_revision"] == 3
        assert payload["join_revision"] == 1
        assert payload["mapping"] == "keyed-join"
        assert payload["expected_cardinality"] == 2
        assert payload["duplicate_key_policy"] == "first-wins"
        assert payload["first_wins_order"] == list(FIRST_WINS_ORDER)
        watermark = cast("dict[str, object]", payload["watermark"])
        assert watermark["kind"] == "all-expected"
        assert "cause" in watermark
        assert "closed_at" in watermark
        assert payload["partitions"] == []
        assert payload["late_events"] == []
        assert payload["guessed_from_json_shape"] is False
        sql = process.sqlite.execute(
            "SELECT definition_revision, join_revision, mapping, duplicate_key_policy, "
            "first_wins_order FROM task_graph_join_state WHERE join_id = ?",
            (state.join_id,),
        )
        assert sql[0][0] == 3
        assert sql[0][1] == 1
        assert sql[0][2] == "keyed-join"
        assert sql[0][3] == "first-wins"
        assert "event_time" in str(sql[0][4])
    finally:
        process.close()


def test_join_is_not_guessed_from_json_shape() -> None:
    assert JOIN_GUESSED_FROM_JSON_SHAPE is False
    refused = refuse_guessed_join_from_json(given={"partitions": [{"k": 1}]})
    assert is_refusal(refused)
    assert refused.context["guessed_from_json_shape"] is False
    assert list(cast("list[str]", refused.context["required_fields"])) == list(JOIN_STATE_FIELDS)
    guessed = parse_join_state(
        {
            "partitions": [
                {
                    "partition_id": "k1",
                    "source_event_id": "sev:a",
                    "event_time": "2026-09-19T12:00:00Z",
                    "receive_time": "2026-09-19T12:00:00Z",
                }
            ]
        }
    )
    assert is_refusal(guessed)
    assert guessed.context["guessed_from_json_shape"] is False
    wrong_order = parse_join_state(
        {
            "join_id": "join:x",
            "graph_run_id": "tg:x",
            "node_id": "nJoin",
            "edge_id": "eA-Join",
            "definition_revision": 1,
            "join_revision": 1,
            "mapping": "keyed-join",
            "expected_cardinality": 1,
            "duplicate_key_policy": "first-wins",
            "first_wins_order": ["receive_time", "event_time", "source_event_id"],
            "watermark": {"kind": "all-expected", "cause": None, "closed_at": None},
            "partitions": [],
            "late_events": [],
        }
    )
    assert is_refusal(wrong_order)


def test_first_wins_total_order_is_stable_across_replay(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-57-4-order")
    try:
        state = _open_join(process, cardinality=2)
        later = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:b",
                event_time="2026-09-19T12:00:02Z",
                receive_time="2026-09-19T12:00:00.010Z",
                result_identity="fp1:sha256:b",
            ),
        )
        assert is_ok(later)
        earlier = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:a",
                event_time="2026-09-19T12:00:01Z",
                receive_time="2026-09-19T12:00:00.050Z",
                result_identity="fp1:sha256:a",
            ),
        )
        assert is_ok(earlier)
        winner = _partition(earlier.value, "k1")
        assert winner.source_event_id == "sev:a"
        assert winner.result_identity == "fp1:sha256:a"
        replay = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:b",
                event_time="2026-09-19T12:00:02Z",
                receive_time="2026-09-19T12:00:00.010Z",
                result_identity="fp1:sha256:b-replay",
            ),
        )
        assert is_ok(replay)
        assert replay.value.watermark.closed is False
        replay_winner = _partition(replay.value, "k1")
        assert replay_winner.source_event_id == "sev:a"
        assert replay_winner.result_identity == "fp1:sha256:a"
        assert replay.value.late_events == ()
        closed = process.task_graphs.close_join_watermark(
            state.join_id,
            kind=WatermarkKind.TIMEOUT,
            closed_at="2026-09-19T12:01:00Z",
            cause="join-timeout",
        )
        assert is_ok(closed)
        late_replay = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:b",
                event_time="2026-09-19T12:00:02Z",
                receive_time="2026-09-19T12:00:00.010Z",
                result_identity="fp1:sha256:b-replay",
            ),
            detected_at="2026-09-19T12:05:00Z",
        )
        assert is_ok(late_replay)
        late_winner = _partition(late_replay.value, "k1")
        assert late_winner.source_event_id == "sev:a"
        assert late_replay.value.late_events[0].disposition == "late"
        assert late_replay.value.late_events[0].source_event_id == "sev:b"
    finally:
        process.close()


def test_late_arrival_after_watermark_is_evidence_not_merged(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-57-4-late")
    try:
        state = _open_join(process, cardinality=2)
        first = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:a",
                event_time="2026-09-19T12:00:00Z",
                receive_time="2026-09-19T12:00:00.050Z",
                result_identity="fp1:sha256:a",
            ),
        )
        assert is_ok(first)
        closed = process.task_graphs.close_join_watermark(
            state.join_id,
            kind=WatermarkKind.TIMEOUT,
            closed_at="2026-09-19T12:01:00Z",
            cause="join-timeout",
        )
        assert is_ok(closed)
        assert closed.value.watermark.kind is WatermarkKind.TIMEOUT
        assert closed.value.watermark.cause == "join-timeout"
        assert closed.value.watermark.closed_at == "2026-09-19T12:01:00Z"
        late = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k2",
                source_event_id="sev:late",
                event_time="2026-09-19T11:59:00Z",
                receive_time="2026-09-19T12:05:00Z",
                result_identity="fp1:sha256:late",
            ),
            detected_at="2026-09-19T12:05:00Z",
        )
        assert is_ok(late)
        assert late.value.partition("k2") is None
        kept = _partition(late.value, "k1")
        assert kept.result_identity == "fp1:sha256:a"
        assert len(late.value.late_events) == 1
        evidence = late.value.late_events[0]
        assert evidence.disposition == "late"
        assert evidence.source_event_id == "sev:late"
        assert evidence.partition_id == "k2"
        assert evidence.detected_at == "2026-09-19T12:05:00Z"
    finally:
        process.close()


def test_partial_retry_reuses_definition_and_successful_identities(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-57-4-retry")
    try:
        state = _open_join(process, cardinality=2)
        done = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:ok",
                event_time="2026-09-19T12:00:00Z",
                receive_time="2026-09-19T12:00:00.040Z",
                status=JoinPartitionStatus.DONE,
                logical_invocation_id="inv:k1",
                result_identity="fp1:sha256:ok",
            ),
        )
        assert is_ok(done)
        failed = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k2",
                source_event_id="sev:fail",
                event_time="2026-09-19T12:00:01Z",
                receive_time="2026-09-19T12:00:01.040Z",
                status=JoinPartitionStatus.FAILED,
                logical_invocation_id="inv:k2",
            ),
        )
        assert is_ok(failed)
        closed = process.task_graphs.close_join_watermark(
            state.join_id,
            kind=WatermarkKind.FAILED_AGGREGATION,
            closed_at="2026-09-19T12:02:00Z",
            cause="partition-k2-failed",
        )
        assert is_ok(closed)
        wrong = process.task_graphs.retry_failed_join(
            state.join_id, definition_revision=3, join_revision=2
        )
        assert is_refusal(wrong)
        planned = process.task_graphs.retry_failed_join(
            state.join_id, definition_revision=3, join_revision=1
        )
        assert is_ok(planned)
        assert planned.value.definition_revision == 3
        assert planned.value.join_revision == 1
        assert planned.value.reinvoke_partition_ids == ("k2",)
        assert planned.value.reused_result_identities == {"k1": "fp1:sha256:ok"}
        retried = process.task_graphs.apply_join_retry_result(
            state.join_id,
            partition_id="k2",
            result_identity="fp1:sha256:retry",
            definition_revision=3,
            join_revision=1,
        )
        assert is_ok(retried)
        assert retried.value.definition_key == (3, 1)
        reused = _partition(retried.value, "k1")
        retried_row = _partition(retried.value, "k2")
        assert reused.result_identity == "fp1:sha256:ok"
        assert retried_row.status is JoinPartitionStatus.DONE
        assert retried_row.result_identity == "fp1:sha256:retry"
    finally:
        process.close()


def test_join_state_survives_daemon_restart(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-57-4-restart-a")
    try:
        state = _open_join(process, cardinality=1)
        applied = process.task_graphs.apply_join_arrival(
            state.join_id,
            JoinArrival(
                partition_id="k1",
                source_event_id="sev:a",
                event_time="2026-09-19T12:00:00Z",
                receive_time="2026-09-19T12:00:00.050Z",
                result_identity="fp1:sha256:a",
            ),
        )
        assert is_ok(applied)
        join_id = state.join_id
    finally:
        process.close()

    restarted = _compose(tmp_path, boot="boot-57-4-restart-b")
    try:
        restored = restarted.task_graphs.get_join(join_id)
        assert is_ok(restored)
        body = restored.value
        assert body.definition_revision == 3
        assert body.join_revision == 1
        assert body.mapping is EdgeMapping.KEYED_JOIN
        assert body.first_wins_order == FIRST_WINS_ORDER
        restored_row = _partition(body, "k1")
        assert restored_row.result_identity == "fp1:sha256:a"
        assert body.watermark.closed is True
    finally:
        restarted.close()


def test_example_and_source_bind_total_order() -> None:
    tree = ast.parse((_SRC / "join.py").read_text(encoding="utf-8"))
    assigned: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.target.id] = ast.literal_eval(node.value)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.targets[0].id] = ast.literal_eval(node.value)
    assert assigned.get("JOIN_GUESSED_FROM_JSON_SHAPE") is False
    assert assigned.get("FIRST_WINS_ORDER") == (
        "event_time",
        "receive_time",
        "source_event_id",
    )
    assert assigned.get("LATE_DISPOSITION") == "late"
    namespace = runpy.run_path(str(_EXAMPLE))
    assert callable(namespace["main"])
    namespace["main"]()
