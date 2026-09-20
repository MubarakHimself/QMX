"""Reference usage — JoinState binds revisions and a first-wins total order."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from qma.core.vocabulary.enums import EdgeMapping
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph import (
    FIRST_WINS_ORDER,
    JOIN_GUESSED_FROM_JSON_SHAPE,
    DuplicateKeyPolicy,
    JoinArrival,
    JoinPartitionStatus,
    WatermarkKind,
    parse_join_state,
    refuse_guessed_join_from_json,
)
from qmf.core import is_ok, is_refusal


def _compose(root: Path, *, boot: str) -> DaemonProcess:
    seed = root / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        root,
        machine="example-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(result)
    return result.value


def main() -> None:
    assert JOIN_GUESSED_FROM_JSON_SHAPE is False
    assert FIRST_WINS_ORDER == ("event_time", "receive_time", "source_event_id")
    assert is_refusal(refuse_guessed_join_from_json(given={"partitions": []}))
    guessed = parse_join_state({"partitions": [{"partition_id": "k1"}]})
    assert is_refusal(guessed)
    with TemporaryDirectory() as raw:
        root = Path(raw)
        process = _compose(root, boot="boot-join")
        try:
            opened = process.task_graphs.open_join(
                graph_run_id="tg:join-run",
                node_id="nJoin",
                edge_id="eA-Join",
                definition_revision=3,
                join_revision=1,
                mapping=EdgeMapping.KEYED_JOIN,
                expected_cardinality=2,
                duplicate_key_policy=DuplicateKeyPolicy.FIRST_WINS,
            )
            assert is_ok(opened)
            join_id = opened.value.join_id
            later = process.task_graphs.apply_join_arrival(
                join_id,
                JoinArrival(
                    partition_id="k1",
                    source_event_id="sev:b",
                    event_time="2026-09-19T12:00:02Z",
                    receive_time="2026-09-19T12:00:00.010Z",
                    status=JoinPartitionStatus.DONE,
                    result_identity="fp1:sha256:b",
                ),
            )
            assert is_ok(later)
            earlier = process.task_graphs.apply_join_arrival(
                join_id,
                JoinArrival(
                    partition_id="k1",
                    source_event_id="sev:a",
                    event_time="2026-09-19T12:00:01Z",
                    receive_time="2026-09-19T12:00:00.050Z",
                    status=JoinPartitionStatus.DONE,
                    result_identity="fp1:sha256:a",
                ),
            )
            assert is_ok(earlier)
            winner = earlier.value.partition("k1")
            assert winner is not None
            assert winner.source_event_id == "sev:a"
            closed = process.task_graphs.close_join_watermark(
                join_id,
                kind=WatermarkKind.TIMEOUT,
                closed_at="2026-09-19T12:01:00Z",
                cause="join-timeout",
            )
            assert is_ok(closed)
            late = process.task_graphs.apply_join_arrival(
                join_id,
                JoinArrival(
                    partition_id="k1",
                    source_event_id="sev:late",
                    event_time="2026-09-19T12:00:00Z",
                    receive_time="2026-09-19T12:05:00Z",
                    result_identity="fp1:sha256:late",
                ),
                detected_at="2026-09-19T12:05:00Z",
            )
            assert is_ok(late)
            late_winner = late.value.partition("k1")
            assert late_winner is not None
            assert late_winner.source_event_id == "sev:a"
            assert late.value.late_events[0].disposition == "late"
            print("join first-wins order bound; late arrival recorded with evidence")
        finally:
            process.close()
        restarted = _compose(root, boot="boot-join-2")
        try:
            restored = restarted.task_graphs.get_join(join_id)
            assert is_ok(restored)
            assert restored.value.definition_revision == 3
            assert restored.value.join_revision == 1
            restored_row = restored.value.partition("k1")
            assert restored_row is not None
            assert restored_row.source_event_id == "sev:a"
            print("restart restored join definition and first-wins winner")
        finally:
            restarted.close()


if __name__ == "__main__":
    main()
